# IoT Streaming Data Pipeline (Kafka + Flink + Cassandra)

This project is a **real-time IoT data pipeline** that ingests, processes, and stores simulated sensor readings using modern streaming technologies.  
It’s designed as a hands-on learning project to master **Apache Kafka**, **Apache Flink**, and **Apache Cassandra** — with room to expand into **Spark**, **Grafana**, or **Kafka Connect** later.

---

## Overview

### Architecture

```text
IoT Devices → Kafka → Flink → Cassandra → (optional) Grafana Dashboard
````

| Layer                | Tool                  | Purpose                                              |
| -------------------- | --------------------- | ---------------------------------------------------- |
| **Data Producers**   | Simulated IoT sensors | Emit JSON readings (temperature, humidity, etc.)     |
| **Messaging Layer**  | Apache Kafka          | Durable, scalable event streaming backbone           |
| **Stream Processor** | Apache Flink          | Real-time windowed aggregation and anomaly detection |
| **Data Sink**        | Apache Cassandra      | Time-series storage for sensor aggregates            |
| **(Optional)**       | Grafana               | Dashboard to visualize sensor trends                 |

---

## Project Goals

* Learn Kafka fundamentals (topics, producers, consumers, offsets)
* Build a Flink job to process streaming data with windowing & state
* Persist processed data in Cassandra for long-term analytics
* Design a scalable, event-driven architecture with clear data flow
* Provide a base for future extensions (e.g. Spark ML, Kafka Connect)

---

## 🧱 Repository Structure

```
.
├── /producers/            # IoT data simulator scripts
│   └── iot_producer.py
├── /flink-job/            # Flink streaming job source
│   └── flink_job.py
├── /docker/               # Docker Compose setup for Kafka + Flink + Cassandra
│   └── docker-compose.yml
└── README.md
```

---

## Setup & Run

### Prerequisites

* Docker & Docker Compose
* [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv?tab=readme-ov-file) 
* Python 3.10+
* Java 11+ (openjdk)
* [Grafana](https://grafana.com/docs/grafana/latest/setup-grafana/installation/) for visualization  [[docker](https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/)]

### 1. Clone the Repo

```bash
git clone https://github.com/gwarren3210/iot-streaming-pipeline.git
cd iot-streaming-pipeline
```

### 1.5 Setup env variables

./docker/.env
```bash
# .env
GRAFANA_USER=admin
GRAFANA_PASSWORD=supersecret123
```

### 2. Start the Streaming Stack

Spin up Kafka, Flink, Cassandra, and Grafana.

```bash
cd docker
docker compose up -d
```

Check that the containers are healthy before moving on:

```bash
docker compose ps
```

### 3. Prepare Cassandra Schema

Initialize the keyspace and table that the Flink job writes to. Choose one of the following:

* **Scripted setup (recommended):**
  ```bash
  bash docker/setup_cassandra.sh
  ```
  > This script recreates the `iot_avg_temperature_windowed` table so that Grafana can read native `timestamp` columns. Re-run it whenever you need to reset the schema for dashboards.
* **Manual setup via `cqlsh`:**
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

```bash
cd producers
pyenv virtualenv 3.11.14 producer_venv
pyenv activate producer_venv
pip install -r requirements.txt
python iot_producer.py
```

Simulates sensors emitting messages to Kafka topic `iot_sensors`.

### 5. Start Flink Processing Job

Submit your Flink job to the running Flink cluster:

```bash
cd flink-job
pyenv virtualenv 3.11.14 flink_venv
pyenv activate flink_venv
pip install -r requirements.txt
python flink_job.py
```

Flink consumes `iot_sensors`, computes windowed averages, and writes results to Cassandra.

### 6. Inspect Data in Cassandra

Once producer and Flink job are running, verify that results land in Cassandra:

```bash
cd docker && docker compose exec cassandra cqlsh
```

Connect to Cassandra and query results:

```sql
USE iot_data;
SELECT device_id, window_start, window_end, avg_temp
FROM iot_avg_temperature_windowed
LIMIT 10;
```

You should see windowed aggregates for each device. Exit `cqlsh` with `EXIT;`.

### 7. Access Grafana Dashboard

Once data is flowing into Cassandra, access the Grafana dashboard:

1. **Open Grafana:** Navigate to `http://localhost:3000` in your browser
2. **Login:** Use the credentials from your `.env` file (default: `admin`/`admin`)
3. **View Dashboard:** The "IoT Sensor Dashboard" should be automatically available
4. **Configure Datasource (if needed):** The Cassandra datasource should be pre-configured, but you can verify it in `Configuration > Data Sources`

The dashboard displays:
- **Average Temperature by Device:** Time series graph showing temperature trends
- **Recent Readings:** Table showing the latest windowed averages

**Note:** Make sure you have data in Cassandra before expecting visualizations. Run the producer and Flink job first (steps 4-5). Grafana queries rely on timestamp columns, so if you created the table manually ensure `window_start`/`window_end` are of type `TIMESTAMP`.

---

## 📊 Example Data Flow

Example raw event:

```json
{
  "sensor_id": "sensor-01",
  "timestamp": "2025-11-05T12:00:00Z",
  "temperature": 27.5,
  "humidity": 40.2
}
```

Example processed record (Flink output):

```json
{
  "sensor_id": "sensor-01",
  "window_start": "2025-11-05T12:00:00Z",
  "avg_temp": 26.8,
  "avg_humidity": 41.1
}
```

---

## Future Improvements

* [ ] Add **Kafka Connect** → auto-ingest into Cassandra or Elasticsearch
* [ ] Add **Spark Structured Streaming** for batch analytics
* [x] Add **Grafana dashboard** for live monitoring
* [ ] Introduce **Schema Registry** for Avro/JSON consistency
* [ ] Add **Anomaly detection model** via Flink ML

---

## Learning Outcomes

By the end of this project, you’ll understand how to:

* Build a scalable, decoupled streaming architecture
* Handle real-time data with exactly-once semantics in Flink
* Integrate Kafka and Cassandra for low-latency analytics
* Extend your system for real-world use cases (IoT, monitoring, fintech, etc.)

---

## 🧾 License

Apache 2.0 License © 2025 Gavriel Warren

---

## 🌐 Diagram

![Architecture Diagram](docs/architecture.png)

Lucidchart version available in `/docs/architecture.lucid`.

```
   cd docker
   docker compose down cassandra
   docker compose up -d cassandra
   # Wait for Cassandra to be healthy
   docker compose restart cassandra-jmx-exporter
```