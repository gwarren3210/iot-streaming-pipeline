#!/bin/bash

# Build the producer image
echo "Building Producer Image..."
docker build -t iot-producer:latest -f producer/Dockerfile producer/

# Build the Flink image
echo "Building Flink Image..."
docker build -t iot-flink-job:latest -f flink/Dockerfile flink/

# Build the Kafka Connect image
echo "Building Kafka Connect Image..."
docker build -t iot-connect:latest -f connect/Dockerfile connect/

# Instructions for loading into Minikube (if applicable)
echo "If you are using Minikube, run:"
echo "  minikube image load iot-producer:latest"
echo "  minikube image load iot-flink-job:latest"
echo "  minikube image load iot-connect:latest"
echo "If you are using Kind, run:"
echo "  kind load docker-image iot-producer:latest"
echo "  kind load docker-image iot-flink-job:latest"
echo "  kind load docker-image iot-connect:latest"
