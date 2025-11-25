#!/bin/bash
# Helper script to prepare Flink SQL files with credentials from .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "Please create it by copying .env.example and adding your credentials"
    exit 1
fi

# Source the .env file (ignore empty lines and comments)
export $(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | xargs)

# Check required variables
if [ -z "$KAFKA_BOOTSTRAP_SERVERS" ] || [ -z "$KAFKA_API_KEY" ] || [ -z "$KAFKA_API_SECRET" ]; then
    echo "❌ Error: Missing required variables in .env file"
    echo "Required: KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET"
    exit 1
fi


if [ -n "$FLINK_COMPUTE_POOL_ID" ] && [ -n "$FLINK_COMPUTE_POOL_ENV" ]; then
    echo "📤 Submit commands:"
    echo ""
    echo "   # Create source table"
    echo "   confluent flink statement create create-table-iot-sensor-data \\"
    echo "     --sql \"\$(cat flink_job_create_source.sql)\" \\"
    echo "     --compute-pool \"$FLINK_COMPUTE_POOL_ID\" \\"
    echo "     --environment \"$FLINK_COMPUTE_POOL_ENV\""
    echo ""
    echo "   # Create sink table"
    echo "   confluent flink statement create create-table-temperature-averages \\"
    echo "     --sql \"\$(cat flink_job_create_sink.sql)\" \\"
    echo "     --compute-pool \"$FLINK_COMPUTE_POOL_ID\" \\"
    echo "     --environment \"$FLINK_COMPUTE_POOL_ENV\""
    echo ""
    echo "   # Submit INSERT statement"
    echo "   confluent flink statement create iot-temperature-aggregation \\"
    echo "     --sql \"\$(cat flink_job_insert.sql)\" \\"
    echo "     --compute-pool \"$FLINK_COMPUTE_POOL_ID\" \\"
    echo "     --environment \"$FLINK_COMPUTE_POOL_ENV\""
    echo ""
    echo "   Or use: ./submit_flink_job.sh"
else
    echo "📤 Submit commands (replace <pool-id> and <env-id>):"
    echo ""
    echo "   confluent flink statement create create-table-iot-sensor-data \\"
    echo "     --sql \"\$(cat flink_job_create_source.sql)\" \\"
    echo "     --compute-pool <pool-id> \\"
    echo "     --environment <env-id>"
    echo ""
    echo "   confluent flink statement create create-table-temperature-averages \\"
    echo "     --sql \"\$(cat flink_job_create_sink.sql)\" \\"
    echo "     --compute-pool <pool-id> \\"
    echo "     --environment <env-id>"
    echo ""
    echo "   confluent flink statement create iot-temperature-aggregation \\"
    echo "     --sql \"\$(cat flink_job_insert.sql)\" \\"
    echo "     --compute-pool <pool-id> \\"
    echo "     --environment <env-id>"
fi
