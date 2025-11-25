# Kubernetes Migration - Progress Report

## ✅ Completed Components

### 1. Infrastructure Setup
**Status:** All pods running successfully
- Cassandra (v4.1) with 512M heap, 1Gi memory limit
- Kafka (KRaft mode, single broker)
- Flink JobManager & TaskManagers (custom image)
- Producer (Python, JSON serialization)
- Kafka Connect (2Gi memory limit)

### 2. Flink SQL Job
**Status:** ✅ Running (Job ID: `59ef5664fbd8f5ebf1524d8f4e5dc479`)
- Reads from `iot_sensor_data` topic
- Performs 1-minute tumbling window aggregations
- Writes to `iot_windowed_data` topic

### 3. Kafka Connect Cassandra Sink
**Status:** ✅ Connector configured and running
- Connector: `cassandra-sink`
- State: RUNNING
- Task 0: RUNNING

### 4. Cassandra Schema
**Status:** ✅ Created
- Keyspace: `iot_data` (replication_factor=1)
- Table: `iot_windowed_data` (device_id, window_start, window_end, avg_temp)

---

## 🔧 Blockers Encountered & Resolutions

### Blocker 1: PyFlink Dependency Hell
**Issue:** `ModuleNotFoundError: No module named 'typing_extensions'`
- PyFlink uses bundled Python environment that doesn't see system packages
- Installing `apache-flink` via pip downloads duplicate Flink binaries

**Attempted Fixes:**
1. ❌ Added `typing_extensions` to requirements.txt - didn't work due to Docker cache
2. ❌ Rebuilt with `--no-cache` - still failed, PyFlink uses isolated environment
3. ❌ Added `apache-flink` back - created conflicts with base image

**Final Solution:** ✅ Switched from PyFlink to **Flink SQL Client**
- Removed all Python dependencies from Flink image
- Created `job.sql` with DDL and INSERT statements
- Execute via `sql-client.sh -f /opt/flink/job.sql`
- Much simpler, no dependency conflicts

### Blocker 2: Kafka JSON Format PRIMARY KEY Constraint
**Issue:** `ValidationException: Kafka table with 'json' format doesn't support PRIMARY KEY`

**Fix:** ✅ Removed PRIMARY KEY from `iot_windowed_data` table definition in `job.sql`

### Blocker 3: Docker Image Caching
**Issue:** Kubernetes pods using old image despite rebuilds

**Attempted Fixes:**
1. ❌ `imagePullPolicy: IfNotPresent` - cached old image
2. ✅ Changed to `imagePullPolicy: Always` - forces pull of latest

### Blocker 4: Memory Issues
**Issue:** Multiple OOMKilled errors

**Cassandra:**
- ❌ Initial: `cassandra:latest` (v5.x) - too heavy
- ✅ Solution: Switched to `cassandra:4.1` + added `MAX_HEAP_SIZE=512M`

**Kafka Connect:**
- ❌ Initial: 1Gi limit - insufficient
- ✅ Solution: Increased to 2Gi memory limit

### Blocker 5: Kafka Connect Replication Factor
**Issue:** `Unable to replicate partition 3 times: only 1 broker registered`

**Fix:** ✅ Added environment variables:
```yaml
CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR: "1"
CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR: "1"
CONNECT_STATUS_STORAGE_REPLICATION_FACTOR: "1"
```

### Blocker 6: Connector Configuration Submission
**Issue:** Multiple failures submitting sink config

**Attempted Fixes:**
1. ❌ `kubectl exec ... curl ... < config.json` - stdin piping broken
2. ❌ `kubectl cp` - tar not available in container
3. ✅ `kubectl port-forward` + local curl - worked

---

## ⚠️ Current Blocker: No Data in Cassandra

### Symptoms
- Cassandra table exists but has 0 rows
- Connector status: RUNNING
- Flink job: RUNNING

### Investigation Status
**What We Know:**
1. ✅ Producer is running (pod healthy)
2. ✅ Flink job submitted successfully
3. ✅ Kafka Connect connector is RUNNING
4. ✅ Cassandra table schema created
5. ❓ Unknown: Is data in `iot_sensor_data` topic?
6. ❓ Unknown: Is data in `iot_windowed_data` topic?

**What We Tried:**
1. ❌ `kafka-console-consumer.sh` - command not in PATH initially
2. ✅ Found correct path: `/opt/kafka/bin/kafka-console-consumer.sh`
3. ⏳ Currently running consumer to check `iot_windowed_data` topic

**Possible Root Causes:**
1. Producer not actually writing to Kafka
2. Flink job not consuming/processing data
3. Kafka Connect not reading from topic
4. Schema mismatch between Kafka messages and Cassandra table
5. Connector mapping configuration incorrect

### Next Steps to Debug
1. Check if `iot_sensor_data` topic has messages
2. Check if `iot_windowed_data` topic has messages
3. Check Flink job logs for errors
4. Check Kafka Connect logs for processing errors
5. Verify field mapping in `sink-config.json` matches actual data structure

---

## Architecture Summary

```
Producer (Python)
    ↓ (JSON to Kafka)
iot_sensor_data topic
    ↓ (Flink SQL consumes)
Flink Job (1-min tumbling window)
    ↓ (Aggregated JSON to Kafka)
iot_windowed_data topic
    ↓ (Kafka Connect consumes)
Cassandra Sink Connector
    ↓ (Writes to Cassandra)
iot_data.iot_windowed_data table
```

**Current Status:** Pipeline configured end-to-end, but data not flowing to Cassandra yet.
