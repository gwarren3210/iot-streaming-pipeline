#!/bin/bash
# Setup Cassandra keyspace and table

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
SERVICE_NAME="cassandra"

compose_exec() {
  docker compose -f "${COMPOSE_FILE}" exec -T "${SERVICE_NAME}" "$@"
}

echo "📦 Setting up Cassandra schema..."

# Wait for Cassandra to be ready
echo "⏳ Waiting for Cassandra to be ready..."
until compose_exec cqlsh -e "DESCRIBE KEYSPACES" > /dev/null 2>&1; do
  echo "   Cassandra not ready yet, waiting..."
  sleep 2
done

echo "✅ Cassandra is ready"

# Create keyspace and table
cat "${SCRIPT_DIR}/setup_cassandra.cql" | compose_exec cqlsh

echo "✅ Cassandra keyspace 'iot_data' and table 'iot_avg_temperature_windowed' created"

# Verify
echo "📋 Verifying table structure:"
compose_exec cqlsh -e "USE iot_data; DESCRIBE TABLE iot_avg_temperature_windowed;"

