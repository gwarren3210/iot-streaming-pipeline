CREATE TABLE temperature_averages (
    device_id STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    avg_temperature DOUBLE
) WITH (
    'connector' = 'confluent'
);
