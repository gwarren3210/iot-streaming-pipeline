# Docker Compose Deployment

This directory contains the Docker Compose setup for local development and learning.

## Overview

This deployment uses Docker Compose to run a complete IoT streaming pipeline locally:
- **Kafka**: Apache Kafka in KRaft mode (single broker)
- **Flink**: JobManager + TaskManager for stream processing
- **Cassandra**: Apache Cassandra for time-series storage

## Structure

```
docker-compose/
├── docker-compose.yml     # Infrastructure (Kafka, Flink, Cassandra)
├── setup/                 # Cassandra schema setup scripts
│   ├── setup_cassandra.cql
│   └── setup_cassandra.sh
├── producer/              # IoT data simulator scripts
│   ├── iot_producer.py
│   └── requirements.txt
└── flink-job/            # Flink streaming job
    ├── flink_job.py
    ├── requirements.txt
    └── download_kafka_jar.sh
```

---

## Prerequisites

* Docker & Docker Compose
* [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv?tab=readme-ov-file) (optional but recommended)
* Python 3.10+
* Java 11+ (openjdk) - Required for Flink

---

## Setup & Run

### 1. Clone the Repository

```bash
git clone https://github.com/gwarren3210/iot-streaming-pipeline.git
cd iot-streaming-pipeline
```

### 2. Start the Streaming Stack

Navigate to the docker-compose directory and start all services:

```bash
cd deployments/docker-compose
docker compose up -d
```

Verify all containers are running:

```bash
docker compose ps
```

You should see three services: `kafka`, `jobmanager`, `taskmanager`, and `cassandra`.

Wait for Cassandra to be fully ready (may take 30-60 seconds on first start).

### 3. Prepare Cassandra Schema

Initialize the keyspace and table that the Flink job writes to.

**Option A: Scripted setup (recommended)**

```bash
bash setup/setup_cassandra.sh
```

This script waits for Cassandra to be ready, then creates:
- Keyspace: `iot_data`
- Table: `iot_avg_temperature_windowed`

**Option B: Manual setup via `cqlsh`**

```bash
docker compose exec cassandra cqlsh
```

Then run:

```sql
CREATE KEYSPACE IF NOT EXISTS iot_data
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE iot_data;

CREATE TABLE IF NOT EXISTS iot_avg_temperature_windowed (
    device_id TEXT,
    window_start TEXT,
    window_end TEXT,
    avg_temp DOUBLE,
    PRIMARY KEY (device_id, window_start)
);
```

Exit `cqlsh` with `EXIT;`.

### 4. Run IoT Sensor Producer

In a new terminal, start the producer to generate simulated sensor data:

```bash
cd deployments/docker-compose/producer

# Create virtual environment (recommended)
pyenv virtualenv 3.11.14 producer_venv
pyenv activate producer_venv

# Install dependencies
pip install -r requirements.txt

# Start producer
python iot_producer.py
```

The producer will:
- Generate simulated sensor readings (temperature, humidity, status)
- Send messages to Kafka topic `iot_sensors`
- Print confirmation for each message sent

### 5. Start Flink Processing Job

In another terminal, start the Flink job to process the data:

```bash
cd deployments/docker-compose/flink-job

# Create virtual environment (recommended)
pyenv virtualenv 3.11.14 flink_venv
pyenv activate flink_venv

# Install dependencies
pip install -r requirements.txt

# Start Flink job
python flink_job.py
```

The Flink job will:
- Consume messages from `iot_sensors` topic
- Perform 5-minute tumbling window aggregations
- Calculate average temperature per device per window
- Write results to Cassandra table `iot_avg_temperature_windowed`

### 6. Verify Data Flow

**Check Kafka topics:**

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

You should see `iot_sensors` topic.

**Inspect data in Cassandra:**

```bash
docker compose exec cassandra cqlsh
```

Then query:

```sql
USE iot_data;

-- View windowed aggregates
SELECT device_id, window_start, window_end, avg_temp
FROM iot_avg_temperature_windowed
LIMIT 10;

-- Count records
SELECT COUNT(*) FROM iot_avg_temperature_windowed;
```

Exit `cqlsh` with `EXIT;`.

**Check Flink Web UI:**

```bash
# Port-forward Flink Web UI
docker compose port jobmanager 8081
```

Open [http://localhost:8081](http://localhost:8081) in your browser to monitor:
- Job status and metrics
- Task manager health
- Throughput and latency

---

## Services Details

### Kafka

- **Port:** `9092` (exposed on host)
- **Mode:** KRaft (no Zookeeper)
- **Topics:** Created automatically by producers
- **Access:** `localhost:9092`

### Flink

- **JobManager UI:** [http://localhost:8081](http://localhost:8081)
- **Mode:** Local cluster (1 JobManager + 1 TaskManager)
- **Parallelism:** Default (1)

### Cassandra

- **Port:** `9042` (CQL native protocol)
- **Keyspace:** `iot_data`
- **Access:** `docker compose exec cassandra cqlsh`

---

## Troubleshooting

### Containers not starting

**Check logs:**
```bash
docker compose logs kafka
docker compose logs cassandra
docker compose logs jobmanager
```

**Common issues:**
- Port conflicts: Ensure ports 9092, 8081, 9042 are available
- Memory: Ensure Docker has enough memory allocated (4GB+ recommended)
- Disk space: Check available disk space for volumes

### Cassandra connection issues

**Wait for Cassandra to be ready:**
```bash
docker compose logs cassandra | grep "Starting listening for CQL clients"
```

Cassandra can take 30-60 seconds to start on first launch.

**Check if Cassandra is responding:**
```bash
docker compose exec cassandra cqlsh -e "DESCRIBE KEYSPACES;"
```

### Flink job not processing data

**Check Flink job status:**
- Visit [http://localhost:8081](http://localhost:8081)
- Check if job is in "RUNNING" state
- Review job logs in the Web UI

**Verify Kafka topic has data:**
```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic iot_sensors \
  --from-beginning \
  --max-messages 5
```

### No data in Cassandra

1. Verify producer is running and sending messages
2. Check Flink job is running (Web UI)
3. Verify Cassandra table exists: `DESCRIBE TABLE iot_data.iot_avg_temperature_windowed;`
4. Check Flink job logs for errors

---

## Stopping the Pipeline

**Stop all services:**
```bash
docker compose down
```

**Stop and remove volumes (clean slate):**
```bash
docker compose down -v
```

This will delete all data including:
- Kafka topics and messages
- Cassandra keyspaces and tables
- Flink job state

---

## Next Steps

- Try the [Cloud Deployment](../cloud/README.md) for managed services
- Explore the [Kubernetes Deployment](../kubernetes/README.md) for production setup
- Review [project documentation](../../docs/) for architecture details

---

## Additional Resources

- [Flink Documentation](https://flink.apache.org/docs/)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Cassandra Documentation](https://cassandra.apache.org/doc/latest/)
