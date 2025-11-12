from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors import StreamingFileSink
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.typeinfo import Types
from pyflink.common import Time
from pyflink.datastream.window import TumblingEventTimeWindows
import json
from datetime import datetime
from cassandra.cluster import Cluster


# Global Cassandra connection (initialized once)
_cassandra_cluster = None
_cassandra_session = None

def get_cassandra_session():
    """Get or create Cassandra session"""
    global _cassandra_cluster, _cassandra_session
    if _cassandra_session is None:
        try:
            _cassandra_cluster = Cluster(['localhost'])
            _cassandra_session = _cassandra_cluster.connect('iot_data')
        except Exception as e:
            print(f"Error connecting to Cassandra: {e}")
    return _cassandra_session

def write_to_cassandra(record):
    """Write record to Cassandra and return it"""
    device_id, ts, avg = record
    window_start = datetime.fromtimestamp(ts / 1000).isoformat()
    window_end = window_start  # placeholder
    try:
        session = get_cassandra_session()
        if session:
            session.execute(
                """
                INSERT INTO iot_avg_temperature_windowed (device_id, window_start, window_end, avg_temp)
                VALUES (%s, %s, %s, %s)
                """,
                (device_id, window_start, window_end, avg)
            )
            print(f"Written to Cassandra: device_id={device_id}, avg_temp={avg}")
    except Exception as e:
        print(f"Error writing to Cassandra: {e}")
    return record


def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add Kafka connector JAR
    import os
    jar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "flink-sql-connector-kafka.jar"))
    if os.path.exists(jar_path):
        env.add_jars(f"file://{jar_path}")
    else:
        raise FileNotFoundError(
            f"Kafka connector JAR not found at {jar_path}. "
            "Run: cd flink-job && ./download_kafka_jar.sh"
        )

    # --- kafka source ---
    kafka_source = (
        KafkaSource.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_topics("iot_sensors")
        .set_group_id("pyflink-iot")
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    stream = env.from_source(
        source=kafka_source,
        watermark_strategy=WatermarkStrategy.no_watermarks(),
        source_name="Kafka Source"
    )

    # --- parsing incoming json ---
    def parse(line):
        try:
            data = json.loads(line)
            ts = int(datetime.fromisoformat(data['timestamp']).timestamp() * 1000)
            return data['device_id'], ts, data['temperature']
        except Exception:
            return None

    parsed = stream.map(
        parse,
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE()])
    ).filter(lambda x: x is not None)

    # --- keyed + windowed aggregation ---
    # Properly compute windowed average by accumulating sum and count
    # Map to add count field: (device_id, ts, temp) -> (device_id, ts, temp, count=1)
    with_count = parsed.map(
        lambda x: (x[0], x[1], x[2], 1),  # (device_id, ts, temp, count=1)
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE(), Types.INT()])
    )
    
    # Reduce to accumulate: (sum, count) across window
    windowed_acc = (
        with_count
        .assign_timestamps_and_watermarks(WatermarkStrategy.for_monotonous_timestamps())
        .key_by(lambda x: x[0])
        .window(TumblingEventTimeWindows.of(Time.minutes(5)))
        .reduce(lambda a, b: (a[0], max(a[1], b[1]), a[2] + b[2], a[3] + b[3]))
    )
    
    # Convert accumulated (sum, count) to average: (device_id, ts, avg_temp)
    windowed = windowed_acc.map(
        lambda x: (x[0], x[1], x[2] / x[3] if x[3] > 0 else 0.0),
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE()])
    )

    # --- cassandra sink (via map + print) ---
    windowed.map(write_to_cassandra).print()

    env.execute("PyFlink IoT Job")


if __name__ == "__main__":
    main()
