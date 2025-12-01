CREATE TABLE IF NOT EXISTS temperature_averages (
    device_id TEXT,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    avg_temperature DOUBLE,
    PRIMARY KEY (device_id, window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);