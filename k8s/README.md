# IoT Streaming Pipeline - Kubernetes Deployment

This directory contains the Kubernetes manifests and source code to deploy the IoT Streaming Pipeline. It is self-contained and uses OSS Kafka and Cassandra.

## Architecture

1.  **Producer**: Python script generates IoT data -> Kafka Topic `iot_sensor_data`.
2.  **Flink**: SQL Job reads `iot_sensor_data` -> Aggregates (Windowed Avg) -> Kafka Topic `iot_windowed_data`.
3.  **Kafka Connect**: 
    - Reads `iot_sensor_data` -> Writes to Cassandra Table `iot_sensor_data` (raw data)
    - Reads `iot_windowed_data` -> Writes to Cassandra Table `iot_windowed_data` (aggregated data)

## Prerequisites

-   **Minikube**
-   **kubectl**
-   **Docker**

## Structure

-   `producer/`: Source code and Dockerfile for the Python Producer.
-   `flink/`: Flink SQL job (`job.sql`) and Dockerfile.
-   `connect/`: Dockerfile and config for Kafka Connect.
-   `*.yaml`: Kubernetes manifests.
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

### Service Management
```bash
# List all services
kubectl get svc -n iot-pipeline

# Port forward to access services locally
kubectl port-forward svc/flink-jobmanager 8081:8081 -n iot-pipeline
kubectl port-forward svc/kafka-connect 8083:8083 -n iot-pipeline

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
