#!/bin/sh
set -e

echo "Installing wget and curl..."
apt-get update -qq
apt-get install -y -qq wget curl > /dev/null 2>&1

echo "Downloading JMX Exporter HTTP Server..."
if wget -O /tmp/jmx_prometheus_httpserver.jar https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_httpserver/0.20.0/jmx_prometheus_httpserver-0.20.0.jar; then
    echo "Download successful via wget"
elif curl -L -o /tmp/jmx_prometheus_httpserver.jar https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_httpserver/0.20.0/jmx_prometheus_httpserver-0.20.0.jar; then
    echo "Download successful via curl"
else
    echo "ERROR: Failed to download JMX Exporter"
    exit 1
fi

if [ ! -s /tmp/jmx_prometheus_httpserver.jar ]; then
    echo "ERROR: Downloaded file is empty or doesn't exist"
    exit 1
fi

echo "JMX Exporter JAR file size: $(ls -lh /tmp/jmx_prometheus_httpserver.jar | awk '{print $5}')"
echo "Waiting for Cassandra JMX to be ready..."
sleep 10

echo "Starting JMX Exporter HTTP Server on port 9000..."
java -jar /tmp/jmx_prometheus_httpserver.jar 9000 /etc/jmx-exporter-config.yml

