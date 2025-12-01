# IoT Streaming Pipeline - Kubernetes Deployment

This directory contains the Kubernetes manifests and source code to deploy the IoT Streaming Pipeline. It is self-contained and uses OSS Kafka and Cassandra.

## Architecture

1.  **Producer**: Python script generates IoT data -> Kafka Topic `iot_sensor_data`.
2.  **Flink**: SQL Job reads `iot_sensor_data` -> Aggregates (Windowed Avg) -> Kafka Topic `iot_windowed_data`.
3.  **Kafka Connect**: 
    - Reads `iot_sensor_data` -> Writes to Cassandra Table `iot_sensor_data` (raw data)
    - Reads `iot_windowed_data` -> Writes to Cassandra Table `iot_windowed_data` (aggregated data)
4.  **Grafana**: Visualization and monitoring dashboard for pipeline metrics and data.

## Prerequisites

-   **Minikube**
-   **kubectl**
-   **Docker**

## Structure

-   `producer/`: Source code and Dockerfile for the Python Producer.
-   `flink/`: Flink SQL job (`job.sql`) and Dockerfile.
-   `connect/`: Dockerfile and config for Kafka Connect.
-   `*.yaml`: Kubernetes manifests.
-   `prometheus-rbac.yaml`: RBAC permissions for Prometheus to scrape Kubernetes metrics.
-   `build_and_push.sh`: Script to build Docker images.

## Deployment Instructions
0. **Start Minikube (ensure proper memory allocation)**
    ```bash
    minikube start --memory=15972 --cpus=4
    ```
    note you may need to adjust docker's memory limit
    ```
    Settings → Resources → Memory slider
    ```
1.  **Create Namespace**
    ```bash
    kubectl apply -f namespace.yaml
    ```

2.  **Build Images**
    Run the build script to create `iot-producer`, `iot-flink-job`, and `iot-connect`.
    
    **For Minikube (choose one method):**
    
    **Method 1: Use Minikube's Docker daemon (Recommended)**
    ```bash
    eval $(minikube docker-env)
    ./build_and_push.sh
    ```
    **Why this is better** than loading with minikube image load
    - **Faster**: Images are built directly in Minikube's Docker daemon, no transfer needed
    - **Less disk usage**: Images only exist in Minikube, not duplicated locally
    
 
3.  **Deploy Services**
    Apply all manifests in this directory:
    ```bash
    kubectl apply -f .
    ```

4.  **Verify Deployment**
    Check if all pods are running:
    ```bash
    kubectl get pods -n iot-pipeline
    ```

5.  **Create Cassandra Schema**
    Create the keyspace and tables in Cassandra:
    ```bash
    CASSANDRA_POD=$(kubectl get pods -n iot-pipeline -l app=cassandra -o jsonpath='{.items[0].metadata.name}')
    # Create keyspace
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "CREATE KEYSPACE IF NOT EXISTS iot_data WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1};"
    # Create table for raw sensor data
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "CREATE TABLE IF NOT EXISTS iot_data.iot_sensor_data (device_id TEXT, timestamp TEXT, temperature DOUBLE, humidity DOUBLE, status TEXT, PRIMARY KEY (device_id, timestamp));"
    # Create table for aggregated windowed data
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "CREATE TABLE IF NOT EXISTS iot_data.iot_windowed_data (device_id TEXT, window_start TIMESTAMP, window_end TIMESTAMP, avg_temp DOUBLE, PRIMARY KEY (device_id, window_start, window_end));"
    ```

6.  **Run Flink Job**
    Submit the Flink SQL job using the SQL client:
    ```bash
    JM_POD=$(kubectl get pods -n iot-pipeline -l component=jobmanager -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/sql-client.sh -f /opt/flink/job.sql
    ```
    
    Verify the job is running:
    ```bash
    kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/flink list
    ```

7.  **Configure Kafka Connect**
    Once the `kafka-connect` pod is running, configure both Cassandra Sink connectors using port-forwarding (recommended):
    ```bash
    # In one terminal, start port-forwarding
    kubectl port-forward svc/kafka-connect 8083:8083 -n iot-pipeline
    
    # In another terminal, submit both connector configs
    # 1. Connector for raw sensor data (iot_sensor_data topic)
    curl -X POST -H "Content-Type: application/json" --data @connect/sink-config-raw.json http://localhost:8083/connectors
    
    # 2. Connector for aggregated windowed data (iot_windowed_data topic)
    curl -X POST -H "Content-Type: application/json" --data @connect/sink-config.json http://localhost:8083/connectors
    ```
    
    Verify both connectors are running:
    ```bash
    curl http://localhost:8083/connectors/cassandra-sink-raw/status
    curl http://localhost:8083/connectors/cassandra-sink/status
    ```

8.  **Access Flink Web UI**
    ```bash
    kubectl port-forward svc/flink-jobmanager 8081:8081 -n iot-pipeline
    ```
    Open [http://localhost:8081](http://localhost:8081) to monitor job status and metrics.

9.  **Deploy Prometheus (Optional but Recommended)**
    For metrics collection and visualization in Grafana:
    ```bash
    # First, create RBAC permissions for Prometheus to scrape Kubernetes metrics
    kubectl apply -f prometheus-rbac.yaml
    
    # Then deploy Prometheus
    kubectl apply -f prometheus.yaml -n iot-pipeline
    ```
    Wait for Prometheus to be ready:
    ```bash
    kubectl wait --for=condition=ready pod -l app=prometheus -n iot-pipeline --timeout=60s
    ```
    Access Prometheus UI:
    ```bash
    kubectl port-forward svc/prometheus 9090:9090 -n iot-pipeline
    ```
    Open [http://localhost:9090](http://localhost:9090) to query metrics directly.
    
    **Note**: Prometheus is configured to scrape:
    - Container metrics via cAdvisor (CPU, memory, network, disk I/O)
    - Kubernetes pod metrics (if pods have `prometheus.io/scrape=true` annotation)
    - Self-monitoring metrics

10. **Access Grafana Dashboard**
    ```bash
    kubectl port-forward svc/grafana 3000:3000 -n iot-pipeline
    ```
    Open [http://localhost:3000](http://localhost:3000) and login with:
    - Username: `admin`
    - Password: `admin`
    
    **Note**: Grafana is pre-configured with Prometheus as a datasource. Once Prometheus is deployed, you can immediately start creating dashboards.

## Verification

After deployment, verify the pipeline is working:

1.  **Check Producer Logs**
    ```bash
    kubectl logs -n iot-pipeline -l app=producer --tail=50
    ```
    Should show messages being sent to Kafka.

2.  **Check Kafka Topics**
    ```bash
    KAFKA_POD=$(kubectl get pods -n iot-pipeline -l app=kafka -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic iot_sensor_data --from-beginning --max-messages 5
    kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic iot_windowed_data --from-beginning --max-messages 5
    ```

3.  **Check Cassandra Data**
    ```bash
    CASSANDRA_POD=$(kubectl get pods -n iot-pipeline -l app=cassandra -o jsonpath='{.items[0].metadata.name}')
    # Check raw sensor data
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT COUNT(*) FROM iot_data.iot_sensor_data;"
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT * FROM iot_data.iot_sensor_data LIMIT 10;"
    # Check aggregated windowed data
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT COUNT(*) FROM iot_data.iot_windowed_data;"
    kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT * FROM iot_data.iot_windowed_data LIMIT 10;"
    ```

## Troubleshooting

### Image Pull Issues (Minikube)
If pods show `ImagePullBackOff` or `ErrImagePull`:
- Ensure you've loaded images into Minikube: `minikube image load <image-name>:latest`
- Or use `eval $(minikube docker-env)` before building

### Flink Job Not Starting
- Check Flink JobManager logs: `kubectl logs -n iot-pipeline -l component=jobmanager`
- Verify SQL syntax: `kubectl exec -n iot-pipeline <jm-pod> -- cat /opt/flink/job.sql`

### Kafka Connect Connector Issues
- Check connector status: 
  - `curl http://localhost:8083/connectors/cassandra-sink-raw/status` (raw data)
  - `curl http://localhost:8083/connectors/cassandra-sink/status` (aggregated data)
- View connector logs: `kubectl logs -n iot-pipeline -l app=kafka-connect`
- Ensure replication factors are set to `1` for single-broker setup (already configured in deployment)

### No Data in Cassandra
1. Verify producer is sending data to `iot_sensor_data` topic
2. Check Flink job is running and processing data
3. Verify data exists in `iot_windowed_data` topic
4. Check Kafka Connect connector is consuming from the topic
5. Verify field mapping in `connect/sink-config.json` matches the data structure

### Prometheus Not Collecting Data
1. **Check Prometheus targets**:
   ```bash
   # Port-forward Prometheus
   kubectl port-forward svc/prometheus 9090:9090 -n iot-pipeline
   # Then visit http://localhost:9090/targets
   ```

2. **Verify Flink metrics are enabled**:
   - Flink Prometheus reporter is configured but may not initialize properly in some versions
   - Check Flink logs for metrics reporter initialization:
     ```bash
     JM_POD=$(kubectl get pods -n iot-pipeline -l component=jobmanager -o jsonpath='{.items[0].metadata.name}')
     kubectl logs -n iot-pipeline $JM_POD | grep -i "metrics reporter\|prometheus"
     ```

3. **Check if metrics endpoint is accessible**:
   ```bash
   JM_POD=$(kubectl get pods -n iot-pipeline -l component=jobmanager -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n iot-pipeline $JM_POD -- curl -s http://localhost:9249/metrics | head -20
   ```

4. **Reload Prometheus config** (if you updated it):
   ```bash
   PROMETHEUS_POD=$(kubectl get pods -n iot-pipeline -l app=prometheus -o jsonpath='{.items[0].metadata.name}')
   # Restart Prometheus pod to reload config
   kubectl delete pod -n iot-pipeline $PROMETHEUS_POD
   ```

5. **Check Prometheus logs**:
   ```bash
   kubectl logs -n iot-pipeline -l app=prometheus --tail=50
   ```

7. **Known Issue**: Flink 2.1 may have issues with Prometheus reporter initialization. If metrics don't appear:
   - Check Flink Web UI at `http://localhost:8081` for job metrics
   - Use Flink's REST API for metrics collection
   - Consider using a Flink metrics exporter sidecar container

## Helpful Commands

### Resource Monitoring
```bash
# View pod resource usage (CPU/Memory)
kubectl top pods -n iot-pipeline

# View node resource usage
kubectl top nodes

# Get detailed pod information with resource requests/limits
kubectl get pods -n iot-pipeline -o wide
```

### Pod Management
```bash
# Get all pods with status
kubectl get pods -n iot-pipeline

# Describe a specific pod (replace <pod-name>)
kubectl describe pod <pod-name> -n iot-pipeline

# View pod logs
kubectl logs <pod-name> -n iot-pipeline

# Follow pod logs in real-time
kubectl logs -f <pod-name> -n iot-pipeline

# View logs for all pods with a label
kubectl logs -n iot-pipeline -l app=producer --tail=50
```

### Flink Job Management
```bash
# Get Flink JobManager pod name
JM_POD=$(kubectl get pods -n iot-pipeline -l component=jobmanager -o jsonpath='{.items[0].metadata.name}')

# List running Flink jobs
kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/flink list

# Cancel a Flink job (replace <job-id>)
kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/flink cancel <job-id>

# View Flink job details
kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/flink info <job-id>

# Resubmit Flink SQL job
kubectl exec -n iot-pipeline $JM_POD -- /opt/flink/bin/sql-client.sh -f /opt/flink/job.sql
```

### Kafka Management
```bash
# Get Kafka pod name
KAFKA_POD=$(kubectl get pods -n iot-pipeline -l app=kafka -o jsonpath='{.items[0].metadata.name}')

# List all Kafka topics
kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# Describe a topic
kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic iot_sensor_data

# Consume messages from a topic
kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic iot_sensor_data --from-beginning --max-messages 10

# Produce a test message
kubectl exec -n iot-pipeline $KAFKA_POD -- /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic iot_sensor_data
```

### Kafka Connect Management
```bash
# List all connectors (requires port-forward)
curl http://localhost:8083/connectors

# Get connector status
curl http://localhost:8083/connectors/cassandra-sink-raw/status
curl http://localhost:8083/connectors/cassandra-sink/status

# Get connector configuration
curl http://localhost:8083/connectors/cassandra-sink-raw/config
curl http://localhost:8083/connectors/cassandra-sink/config

# Restart a connector
curl -X POST http://localhost:8083/connectors/cassandra-sink-raw/restart
curl -X POST http://localhost:8083/connectors/cassandra-sink/restart

# Delete a connector
curl -X DELETE http://localhost:8083/connectors/cassandra-sink-raw
curl -X DELETE http://localhost:8083/connectors/cassandra-sink
```

### Cassandra Management
```bash
# Get Cassandra pod name
CASSANDRA_POD=$(kubectl get pods -n iot-pipeline -l app=cassandra -o jsonpath='{.items[0].metadata.name}')

# Open CQL shell interactively
kubectl exec -it -n iot-pipeline $CASSANDRA_POD -- cqlsh

# List all keyspaces
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "DESCRIBE KEYSPACES;"

# List tables in a keyspace
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "DESCRIBE TABLES;"

# Query raw sensor data
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT * FROM iot_data.iot_sensor_data LIMIT 10;"
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT COUNT(*) FROM iot_data.iot_sensor_data;"

# Query aggregated windowed data
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT * FROM iot_data.iot_windowed_data LIMIT 10;"
kubectl exec -n iot-pipeline $CASSANDRA_POD -- cqlsh -e "SELECT COUNT(*) FROM iot_data.iot_windowed_data;"
```

### Prometheus Management
```bash
# Get Prometheus pod name
PROMETHEUS_POD=$(kubectl get pods -n iot-pipeline -l app=prometheus -o jsonpath='{.items[0].metadata.name}')

# View Prometheus logs
kubectl logs -n iot-pipeline $PROMETHEUS_POD

# Reload Prometheus configuration (if config changed)
kubectl exec -n iot-pipeline $PROMETHEUS_POD -- wget --post-data="" http://localhost:9090/-/reload

# Check Prometheus targets (what it's scraping)
# Access Prometheus UI and go to Status > Targets

# Query Prometheus via API
kubectl exec -n iot-pipeline $PROMETHEUS_POD -- wget -qO- 'http://localhost:9090/api/v1/query?query=up'
```

### Service Management
```bash
# List all services
kubectl get svc -n iot-pipeline

# Port forward to access services locally
kubectl port-forward svc/flink-jobmanager 8081:8081 -n iot-pipeline
kubectl port-forward svc/kafka-connect 8083:8083 -n iot-pipeline
kubectl port-forward svc/prometheus 9090:9090 -n iot-pipeline
kubectl port-forward svc/grafana 3000:3000 -n iot-pipeline

# Get service endpoints
kubectl get endpoints -n iot-pipeline
```

### Debugging Commands
```bash
# Check pod events
kubectl get events -n iot-pipeline --sort-by='.lastTimestamp'

# View pod resource usage over time
kubectl top pod <pod-name> -n iot-pipeline --containers

# Execute a command in a running pod
kubectl exec -it <pod-name> -n iot-pipeline -- /bin/bash

# Check if minikube is running
minikube status

# View minikube logs
minikube logs
```

### Cleanup Commands
```bash
# Delete all resources in the namespace
kubectl delete all --all -n iot-pipeline

# Delete specific deployment
kubectl delete deployment <deployment-name> -n iot-pipeline

# Delete namespace (removes everything)
kubectl delete namespace iot-pipeline
```

## Monitoring with Grafana

Grafana is included in the deployment for visualization and monitoring. Here's how to set it up:

### Basic Setup

Grafana is deployed automatically when you run `kubectl apply -f .`. Access it via:

```bash
kubectl port-forward svc/grafana 3000:3000 -n iot-pipeline
```

Then open [http://localhost:3000](http://localhost:3000) and login with:
- **Username**: `admin`
- **Password**: `admin`

### Adding Prometheus (Recommended)

Prometheus is included in the deployment. To deploy it:

```bash
kubectl apply -f prometheus.yaml
```

**What Prometheus Scrapes:**
- **cAdvisor Metrics**: ✅ Container-level metrics (CPU, memory, network, disk) for all pods via Kubernetes API
- **Kubernetes Pods**: Any pod with `prometheus.io/scrape=true` annotation
- **Self-monitoring**: Prometheus metrics
- **Note**: Flink-specific metrics require the Prometheus reporter to be working (see troubleshooting). cAdvisor provides container-level metrics for all pods including Flink.

**Configuration:**
- Scrape interval: 15 seconds
- Retention: 15 days
- Storage: 5Gi persistent volume

**Access Prometheus:**
```bash
kubectl port-forward svc/prometheus 9090:9090 -n iot-pipeline
```
Open [http://localhost:9090](http://localhost:9090) to query metrics using PromQL.

**Grafana Integration:**
Grafana is pre-configured to connect to Prometheus at `http://prometheus:9090`. Once both are running, you can immediately create dashboards.

### Data Sources

Grafana is pre-configured with:
- **Prometheus**: For metrics from Flink, Kafka, and system metrics (default datasource)
- **Cassandra**: For querying IoT sensor data directly from Cassandra

**Using Cassandra Datasource:**

The Cassandra datasource is automatically configured. To query your IoT data:

1. **Create a new panel** in Grafana
2. **Select "Cassandra"** as the datasource
3. **Write CQL queries** to fetch data:

**Example Queries:**

```sql
-- Get latest sensor readings
SELECT device_id, timestamp, temperature, humidity, status 
FROM iot_sensor_data 
WHERE device_id = 'device-001' 
ORDER BY timestamp DESC 
LIMIT 100;

-- Get aggregated windowed data
SELECT device_id, window_start, window_end, avg_temp 
FROM iot_windowed_data 
WHERE device_id = 'device-001' 
ORDER BY window_start DESC 
LIMIT 50;

-- Count records per device
SELECT device_id, COUNT(*) as record_count 
FROM iot_sensor_data 
GROUP BY device_id;
```

**Note**: The Cassandra datasource uses the `hadesarchitect-cassandra-datasource` plugin. If you encounter connection issues, verify:
- Cassandra pod is running: `kubectl get pods -n iot-pipeline -l app=cassandra`
- Keyspace exists: `kubectl exec -n iot-pipeline <cassandra-pod> -- cqlsh -e "DESCRIBE KEYSPACE iot_data;"`

### Creating Dashboards

1. **Container Metrics Dashboard** (cAdvisor - Recommended):
   - **CPU Usage**: `rate(container_cpu_usage_seconds_total{namespace="iot-pipeline"}[5m])`
   - **Memory Usage**: `container_memory_usage_bytes{namespace="iot-pipeline"}`
   - **Network I/O**: `rate(container_network_receive_bytes_total{namespace="iot-pipeline"}[5m])`
   - **Disk I/O**: `rate(container_fs_reads_bytes_total{namespace="iot-pipeline"}[5m])`
   - **Pod-specific metrics**: Filter by `pod="<pod-name>"` label

2. **Pipeline Health Dashboard**:
   - All pod CPU/memory usage
   - Network traffic between components
   - Container restart counts
   - Resource limits vs usage

3. **Flink Metrics Dashboard** (if Prometheus reporter works):
   - Job throughput, latency, checkpoint duration
   - Task manager metrics
   - Kafka consumer/producer metrics

4. **IoT Data Dashboard** (requires custom data source):
   - Temperature/humidity trends over time
   - Device status distribution
   - Windowed aggregation trends
   - Query Cassandra directly or use a custom exporter

### Example Prometheus Queries (cAdvisor Metrics)

**Pod CPU Usage** (all containers):
```promql
rate(container_cpu_usage_seconds_total{namespace="iot-pipeline"}[5m])
```

**Pod Memory Usage**:
```promql
container_memory_usage_bytes{namespace="iot-pipeline"}
```

**Pod Memory Usage by Container**:
```promql
container_memory_usage_bytes{namespace="iot-pipeline", container!="POD", container!=""}
```

**Network I/O**:
```promql
rate(container_network_receive_bytes_total{namespace="iot-pipeline"}[5m])
rate(container_network_transmit_bytes_total{namespace="iot-pipeline"}[5m])
```

**Disk I/O**:
```promql
rate(container_fs_reads_bytes_total{namespace="iot-pipeline"}[5m])
rate(container_fs_writes_bytes_total{namespace="iot-pipeline"}[5m])
```

**CPU Usage by Pod Name**:
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="iot-pipeline"}[5m])) by (pod)
```

**Memory Usage by Pod Name**:
```promql
sum(container_memory_usage_bytes{namespace="iot-pipeline"}) by (pod)
```

**Flink-specific metrics** (if Prometheus reporter is working):
```promql
# These will only work if Flink Prometheus reporter initializes correctly
rate(flink_taskmanager_job_task_operator_numRecordsInPerSecond[5m])
flink_jobmanager_job_lastCheckpointDuration
```

### Alternative: Direct Cassandra Queries

You can also create dashboards that query Cassandra directly using:
- **Grafana Simple JSON Datasource**: Create a REST API endpoint that queries Cassandra
- **Cassandra Datasource Plugin**: Install the Grafana Cassandra plugin

### Persistence

Grafana data (dashboards, users, etc.) is persisted in a PersistentVolumeClaim. If you delete the Grafana pod, your dashboards will be preserved.
