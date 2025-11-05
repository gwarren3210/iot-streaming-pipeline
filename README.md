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
├── /producers/            # IoT data simulator scripts (Python or Go)
│   └── iot_producer.py
├── /flink-job/            # Flink streaming job source
│   └── flink_job.py
├── /docker/               # Docker Compose setup for Kafka + Flink + Cassandra
│   └── docker-compose.yml
├── /schemas/              # Event schemas (JSON/Avro)
│   └── sensor_event.json
├── /notebooks/            # Optional analysis or visualization notebooks
└── README.md
```

---

## Setup & Run

### Prerequisites

* Docker & Docker Compose
* Python 3.10+ (if using Python producers)
* Optional: Grafana for visualization

### 1. Clone and Start Infrastructure

```bash
git clone https://github.com/gwarren3210/iot-streaming-pipeline.git
cd iot-streaming-pipeline
docker compose up -d
```

This spins up:

* Kafka broker (with Zookeeper or KRaft)
* Flink JobManager + TaskManager
* Cassandra database

### 2. Run IoT Sensor Producer

```bash
cd producers
python iot_producer.py
```

Simulates sensors emitting messages to Kafka topic `sensor.raw`.

### 3. Start Flink Processing Job

Submit your Flink job to the running Flink cluster:

```bash
cd flink-job
./deploy_flink_job.sh
```

Flink consumes `sensor.raw`, computes windowed averages, and writes results to Cassandra.

### 4. Verify in Cassandra

Connect to Cassandra and query results:

```sql
SELECT * FROM sensor_aggregates LIMIT 10;
```

### 5. (Optional) Add Grafana Dashboard

Use Grafana’s Cassandra or REST connector to visualize:

* Average temperature over time
* Alerts for abnormal readings

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
* [ ] Add **Grafana dashboard** for live monitoring
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
