-- Create keyspace for IoT data
CREATE KEYSPACE IF NOT EXISTS iot_data
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE iot_data;

-- Drop and recreate table for windowed temperature averages with timestamp columns
DROP TABLE IF EXISTS iot_avg_temperature_windowed;

CREATE TABLE IF NOT EXISTS iot_avg_temperature_windowed (
    device_id TEXT,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    avg_temp DOUBLE,
    PRIMARY KEY (device_id, window_start)
)
WITH CLUSTERING ORDER BY (window_start ASC);

