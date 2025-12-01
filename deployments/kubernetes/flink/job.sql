CREATE TABLE iot_sensor_data (
    device_id STRING,
    `timestamp` STRING,
    temperature DOUBLE,
    humidity DOUBLE,
    status STRING,
    ts AS TO_TIMESTAMP(`timestamp`, 'yyyy-MM-dd HH:mm:ss.SSS'),
    WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'iot_sensor_data',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-sql-group',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

CREATE TABLE iot_windowed_data (
    device_id STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    avg_temp DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'iot_windowed_data',
    'properties.bootstrap.servers' = 'kafka:9092',
    'format' = 'json'
);

INSERT INTO iot_windowed_data
SELECT
    device_id,
    window_start,
    window_end,
    AVG(temperature) as avg_temp
FROM TABLE(
    TUMBLE(TABLE iot_sensor_data, DESCRIPTOR(ts), INTERVAL '1' MINUTE)
)
GROUP BY device_id, window_start, window_end;
