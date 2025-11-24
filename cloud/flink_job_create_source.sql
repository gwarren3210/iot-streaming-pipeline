CREATE TABLE iot_sensor_data_v2 (
    device_id STRING,
    `timestamp` STRING,
    temperature DOUBLE,
    humidity DOUBLE,
    `status` STRING,
    event_time AS TO_TIMESTAMP(`timestamp`),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'confluent',
    'scan.startup.mode' = 'latest-offset'
);