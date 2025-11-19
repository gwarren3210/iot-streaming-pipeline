#!/bin/bash
# Helper script to prepare Flink SQL file with credentials from .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
SQL_TEMPLATE="${SCRIPT_DIR}/flink_job.sql"
SQL_OUTPUT="${SCRIPT_DIR}/flink_job_prepared.sql"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "Please create it by copying .env.example and adding your credentials"
    exit 1
fi

# Source the .env file
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Check required variables
if [ -z "$KAFKA_BOOTSTRAP_SERVERS" ] || [ -z "$KAFKA_API_KEY" ] || [ -z "$KAFKA_API_SECRET" ]; then
    echo "❌ Error: Missing required variables in .env file"
    echo "Required: KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET"
    exit 1
fi

# Substitute variables in SQL template
sed -e "s|\${KAFKA_BOOTSTRAP_SERVERS}|${KAFKA_BOOTSTRAP_SERVERS}|g" \
    -e "s|\${KAFKA_API_KEY}|${KAFKA_API_KEY}|g" \
    -e "s|\${KAFKA_API_SECRET}|${KAFKA_API_SECRET}|g" \
    "$SQL_TEMPLATE" > "$SQL_OUTPUT"

echo "✅ Prepared Flink SQL file: $SQL_OUTPUT"
echo "   You can now submit it with:"
echo "   confluent flink statement create --compute-pool <pool-id> --environment <env-id> --statement-file $SQL_OUTPUT"

