# IoT Streaming Pipeline - Kubernetes Deployment

This directory contains the Kubernetes manifests and source code to deploy the IoT Streaming Pipeline. It is self-contained and uses OSS Kafka and Cassandra.

## Architecture

1.  **Producer**: Python script generates IoT data -> Kafka Topic `iot_sensor_data`.
2.  **Flink**: SQL Job reads `iot_sensor_data` -> Aggregates (Windowed Avg) -> Kafka Topic `iot_windowed_data`.
3.  **Kafka Connect**: Reads `iot_windowed_data` -> Writes to Cassandra Table `iot_windowed_data`.

## Prerequisites

-   **Kubernetes Cluster**: A running cluster (Minikube, Kind, Docker Desktop, GKE, EKS, etc.).
-   **kubectl**: Configured to communicate with your cluster.
-   **Docker**: To build the images.

## Structure

-   `producer/`: Source code and Dockerfile for the Python Producer.
-   `flink/`: Flink SQL job, Python runner, and Dockerfile.
-   `connect/`: Dockerfile and config for Kafka Connect.
-   `*.yaml`: Kubernetes manifests.
-   `build_and_push.sh`: Script to build Docker images.

## Deployment Instructions

1.  **Create Namespace**
    ```bash
    kubectl apply -f namespace.yaml
    ```

2.  **Build Images**
    Run the build script to create `iot-producer`, `iot-flink-job`, and `iot-connect`.
    ```bash
    ./build_and_push.sh
    ```
    > [!NOTE]
    > If using Minikube, run `eval $(minikube docker-env)` before building.

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

5.  **Run Flink Job**
    Submit the Flink SQL job:
    ```bash
    JM_POD=$(kubectl get pods -n iot-pipeline -l component=jobmanager -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -n iot-pipeline $JM_POD -- flink run -py /opt/flink/flink_job.py
    ```

6.  **Configure Kafka Connect**
    Once the `kafka-connect` pod is running, configure the Cassandra Sink:
    ```bash
    kubectl exec -n iot-pipeline deploy/kafka-connect -- curl -X POST -H "Content-Type: application/json" --data @/dev/stdin http://localhost:8083/connectors < connect/sink-config.json
    ```
    *Note: You might need to copy the config file to the pod or run curl from your local machine via port-forwarding.*
    
    **Alternative (Port Forwarding):**
    ```bash
    kubectl port-forward svc/kafka-connect 8083:8083 -n iot-pipeline
    curl -X POST -H "Content-Type: application/json" --data @connect/sink-config.json http://localhost:8083/connectors
    ```

7.  **Access Flink Web UI**
    ```bash
    kubectl port-forward svc/flink-jobmanager 8081:8081 -n iot-pipeline
    ```
    Open [http://localhost:8081](http://localhost:8081).
