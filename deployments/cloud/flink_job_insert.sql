INSERT INTO temperature_averages
SELECT
    device_id,
    window_start,
    window_end,
    AVG(temperature) AS avg_temperature
FROM TABLE(
    TUMBLE(TABLE iot_sensor_data_v2, DESCRIPTOR(event_time), INTERVAL '1' MINUTE)
)
GROUP BY
    device_id,
    window_start,
    window_end;
