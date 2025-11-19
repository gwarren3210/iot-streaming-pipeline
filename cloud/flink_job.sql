-- Flink SQL job for IoT temperature aggregation
-- This reads from Kafka topic 'devices' and computes 5-minute windowed averages

-- Create Kafka source table
CREATE TABLE iot_sensor_data (
    device_id STRING,
    `timestamp` STRING,
    temperature DOUBLE,
    humidity DOUBLE,
    `status` STRING,
    proc_time AS PROCTIME(),
    event_time AS TO_TIMESTAMP(`timestamp`)
) WITH (
    'connector' = 'kafka',
    'topic' = 'devices',
    'properties.bootstrap.servers' = '${KAFKA_BOOTSTRAP_SERVERS}',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
    'properties.group.id' = 'flink-iot-consumer',
    'format' = 'json',
    'scan.startup.mode' = 'latest-offset'
);

-- Create sink table for windowed averages (printing to console for now)
-- You can change this to write to a database, another Kafka topic, etc.
CREATE TABLE temperature_averages (
    device_id STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    avg_temperature DOUBLE,
    PRIMARY KEY (device_id, window_start) NOT ENFORCED
) WITH (
    'connector' = 'print'
);

-- Compute 5-minute tumbling window averages per device
INSERT INTO temperature_averages
SELECT
    device_id,
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) AS window_start,
    TUMBLE_END(event_time, INTERVAL '5' MINUTE) AS window_end,
    AVG(temperature) AS avg_temperature
FROM iot_sensor_data
GROUP BY
    device_id,
    TUMBLE(event_time, INTERVAL '5' MINUTE);

