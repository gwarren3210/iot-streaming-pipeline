#!/bin/bash
# Download Flink Kafka connector JAR
# Compatible with Flink 2.0+ (PyFlink 2.1.1 uses Flink 2.1.1)

# Using Flink 2.0 compatible connector (works with Flink 2.1.1)
KAFKA_VERSION="4.0.1-2.0"
JAR_NAME="flink-sql-connector-kafka-${KAFKA_VERSION}.jar"
JAR_URL="https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/${KAFKA_VERSION}/${JAR_NAME}"

echo "Downloading Kafka connector JAR..."
curl -L -o "flink-sql-connector-kafka.jar" "${JAR_URL}"

if [ $? -eq 0 ]; then
    echo "Downloaded: flink-sql-connector-kafka.jar"
else
    echo "Download failed. Try manually from: ${JAR_URL}"
    exit 1
fi

