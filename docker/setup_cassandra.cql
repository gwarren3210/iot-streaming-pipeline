-- Create keyspace for IoT data
CREATE KEYSPACE IF NOT EXISTS iot_data
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE iot_data;

-- Create table for windowed temperature averages
CREATE TABLE IF NOT EXISTS iot_avg_temperature_windowed (
    device_id TEXT,
    window_start TEXT,
    window_end TEXT,
    avg_temp DOUBLE,
    PRIMARY KEY (device_id, window_start)
);

