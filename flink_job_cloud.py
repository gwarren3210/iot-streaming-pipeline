import os
import json
from datetime import datetime
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.typeinfo import Types
from pyflink.common import Time
from pyflink.datastream.window import TumblingEventTimeWindows
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =========================
# Configuration from Environment Variables
# =========================
def getKafkaConfig():
    """Get Kafka configuration for Confluent Cloud with SASL_SSL."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    api_key = os.getenv("KAFKA_API_KEY")
    api_secret = os.getenv("KAFKA_API_SECRET")
    
    if not bootstrap_servers or not api_key or not api_secret:
        raise ValueError(
            "Missing required environment variables: "
            "KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET"
        )
    
    # Flink Kafka connector properties for Confluent Cloud
    return {
        "bootstrap.servers": bootstrap_servers,
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{api_key}" password="{api_secret}";',
        "group.id": os.getenv("KAFKA_GROUP_ID", "flink-iot-consumer"),
    }

# =========================
# Helper Functions
# =========================
def parseJson(line):
    """Parse JSON line from Kafka and extract relevant fields."""
    try:
        data = json.loads(line)
        ts = int(datetime.fromisoformat(data['timestamp']).timestamp() * 1000)
        return data['device_id'], ts, data['temperature']
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

# =========================
# Main Function
# =========================
def main():
    # Get configuration
    try:
        kafka_config = getKafkaConfig()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please create a .env file with KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, and KAFKA_API_SECRET")
        return
    
    # Initialize Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add Kafka connector JAR
    import os as os_module
    jar_path = os_module.path.abspath(
        os_module.path.join(os_module.path.dirname(__file__), "..", "flink-job", "flink-sql-connector-kafka.jar")
    )
    if os_module.path.exists(jar_path):
        env.add_jars(f"file://{jar_path}")
    else:
        raise FileNotFoundError(
            f"Kafka connector JAR not found at {jar_path}. "
            "Run: cd flink-job && ./download_kafka_jar.sh"
        )
    
    # Get topic from environment variable
    topic = os.getenv("KAFKA_TOPIC", "iot_sensor_data")
    
    # Create Kafka source with Confluent Cloud configuration
    # Build the source with all required properties
    kafka_source_builder = (
        KafkaSource.builder()
        .set_bootstrap_servers(kafka_config["bootstrap.servers"])
        .set_topics(topic)
        .set_group_id(kafka_config["group.id"])
        .set_value_only_deserializer(SimpleStringSchema())
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
    )
    
    # Set SASL_SSL properties for Confluent Cloud authentication
    # These properties are required for Confluent Cloud
    kafka_source_builder.set_property("security.protocol", kafka_config["security.protocol"])
    kafka_source_builder.set_property("sasl.mechanism", kafka_config["sasl.mechanism"])
    kafka_source_builder.set_property("sasl.jaas.config", kafka_config["sasl.jaas.config"])
    
    kafka_source = kafka_source_builder.build()
    
    # Create stream from Kafka source
    stream = env.from_source(
        source=kafka_source,
        watermark_strategy=WatermarkStrategy.no_watermarks(),
        source_name="Kafka Source (Confluent Cloud)"
    )
    
    # Parse incoming JSON
    parsed = stream.map(
        parseJson,
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE()])
    ).filter(lambda x: x is not None)
    
    # Add count field for windowed aggregation
    with_count = parsed.map(
        lambda x: (x[0], x[1], x[2], 1),  # (device_id, ts, temp, count=1)
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE(), Types.INT()])
    )
    
    # Windowed aggregation: compute average temperature per device per 5-minute window
    windowed_acc = (
        with_count
        .assign_timestamps_and_watermarks(WatermarkStrategy.for_monotonous_timestamps())
        .key_by(lambda x: x[0])  # Key by device_id
        .window(TumblingEventTimeWindows.of(Time.minutes(5)))
        .reduce(lambda a, b: (a[0], max(a[1], b[1]), a[2] + b[2], a[3] + b[3]))
    )
    
    # Convert accumulated (sum, count) to average
    windowed = windowed_acc.map(
        lambda x: (x[0], x[1], x[2] / x[3] if x[3] > 0 else 0.0),
        output_type=Types.TUPLE([Types.STRING(), Types.LONG(), Types.DOUBLE()])
    )
    
    # Print results (you can replace this with a sink to your database)
    windowed.print()
    
    print(f"🚀 Starting Flink job to consume from topic '{topic}' on Confluent Cloud...")
    env.execute("PyFlink IoT Job (Confluent Cloud)")

if __name__ == "__main__":
    main()

