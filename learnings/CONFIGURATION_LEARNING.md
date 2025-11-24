# Configuration Learnings for IoT Streaming Pipeline

## 1. Timestamp Formatting
- Flink’s `TO_TIMESTAMP` expects **SQL‑compatible** format `yyyy‑MM‑dd HH:mm:ss.SSS`.
- The original Python producer used `datetime.isoformat()` (e.g., `2025-11-24T18:38:35.870039`) which includes a `T` and caused `event_time` to be `NULL`.
- Updated producer to `now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]` to emit the correct format.

## 2. Event‑time Column & Watermarks
- Source table must define a computed column `event_time AS TO_TIMESTAMP(`timestamp`)` and a watermark:
  ```sql
  WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
  ```
- Missing `event_time` leads to **SourceInvalidValue** errors (`RowTime field should not be null`).

## 3. Schema Registry Naming
- When Flink creates a table with the Confluent connector, it registers an Avro schema named `<table_name>_value` in the namespace `org.apache.flink.avro.generated.record`.
- Original table `iot_sensor_data` → schema `iot_sensor_data_value`.
- After renaming to `iot_sensor_data_v2`, Flink generated `iot_sensor_data_v2_value`.
- The Python producer must use the exact schema name; otherwise a `SchemaRegistryError` (`NAME_MISMATCH`) occurs.

## 4. Skipping Stale Bad Data
- Old records with the ISO‑8601 timestamp remained in the topic, causing repeated failures.
- Added `'scan.startup.mode' = 'latest-offset'` to the source table DDL to start consuming only new data after the fix.

## 5. Table Renaming Strategy
- Renaming the source table (`iot_sensor_data` → `iot_sensor_data_v2`) forces Flink to drop the old table definition and create a fresh one, clearing any hidden state.
- Updated all scripts (`create_flink_tables.sh`, `flink_job_insert.sql`) to reference the new table name.

## 6. Producer‑Flink Alignment Steps
1. **Fix timestamp format** in `iot_producer_cloud.py`.
2. **Update Avro schema name** to match the new table (`iot_sensor_data_v2_value`).
3. **Add `scan.startup.mode = 'latest-offset'`** to the source DDL.
4. **Rename the source table** to `iot_sensor_data_v2` and adjust scripts.
5. **Re‑run** `create_flink_tables.sh` and `submit_flink_insert.sh`.
6. **Restart** the Python producer.

## 7. Debugging Checklist Used
- Checked Flink job status (`confluent flink statement describe`).
- Verified table DDL with `SHOW CREATE TABLE`.
- Tested `TO_TIMESTAMP` with a literal query.
- Inspected Schema Registry compatibility errors.
- Queried sink table (`SELECT * FROM temperature_averages LIMIT 10`).

---
These configurations and the associated learnings ensure a stable end‑to‑end pipeline: correct timestamp handling, proper schema alignment, and clean state management.
