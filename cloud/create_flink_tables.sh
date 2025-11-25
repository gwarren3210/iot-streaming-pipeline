#!/bin/bash
# Script to create Flink SQL tables in Confluent Cloud
# Submits CREATE TABLE statements for Source and Sink

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
CREATE_SOURCE="${SCRIPT_DIR}/flink_job_create_source.sql"
CREATE_SINK="${SCRIPT_DIR}/flink_job_create_sink.sql"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Source the .env file
export $(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | xargs)

# Check required variables
if [ -z "$FLINK_COMPUTE_POOL_ID" ] || [ -z "$FLINK_COMPUTE_POOL_ENV" ]; then
    echo "❌ Error: Missing Flink environment variables in .env file"
    echo "Required: FLINK_COMPUTE_POOL_ID, FLINK_COMPUTE_POOL_ENV"
    exit 1
fi

# Get Kafka cluster ID (database) - check .env first, then extract from bootstrap servers
if [ -n "$KAFKA_CLUSTER_ID" ]; then
    KAFKA_DATABASE="$KAFKA_CLUSTER_ID"
elif [ -n "$KAFKA_BOOTSTRAP_SERVERS" ]; then
    # Extract cluster ID from bootstrap servers (pkc-xxxxx -> lkc-xxxxx)
    # Or get it from confluent CLI
    KAFKA_DATABASE=$(confluent kafka cluster list -o json 2>/dev/null | \
        jq -r --arg endpoint "$KAFKA_BOOTSTRAP_SERVERS" '.[] | select(.endpoint | contains($endpoint) or ($endpoint | contains(.endpoint))) | .id' 2>/dev/null | head -1)
    
    if [ -z "$KAFKA_DATABASE" ]; then
        echo "⚠️  Warning: Could not determine Kafka cluster ID"
        echo "   Please add KAFKA_CLUSTER_ID to your .env file"
        echo "   Or ensure KAFKA_BOOTSTRAP_SERVERS matches your cluster endpoint"
    fi
else
    echo "❌ Error: Need KAFKA_CLUSTER_ID or KAFKA_BOOTSTRAP_SERVERS in .env"
    exit 1
fi

if [ -z "$KAFKA_DATABASE" ]; then
    echo "❌ Error: Could not determine Kafka cluster ID (database)"
    echo "   Add KAFKA_CLUSTER_ID=lkc-xxxxx to your .env file"
    exit 1
fi

echo "   Database (Kafka Cluster): $KAFKA_DATABASE"

# Check if prepared SQL files exist
if [ ! -f "$CREATE_SOURCE" ] || [ ! -f "$CREATE_SINK" ]; then
    echo "❌ Error: Prepared SQL files not found"
    echo "Run ./prepare_flink_sql.sh first to generate the separate SQL files"
    exit 1
fi

# Function to delete statement by name
delete_statement_by_name() {
    local stmt_name="$1"
    echo "   🗑️  Deleting existing statement: $stmt_name (if it exists)..."
    # Delete by name directly (with --force to skip confirmation)
    confluent flink statement delete "$stmt_name" \
        --environment "$FLINK_COMPUTE_POOL_ENV" \
        --force 2>/dev/null || true
    sleep 2
}

echo "📝 Creating Flink SQL Tables in Confluent Cloud..."
echo "   Compute Pool: $FLINK_COMPUTE_POOL_ID"
echo "   Environment: $FLINK_COMPUTE_POOL_ENV"
echo ""

# Verify SQL file doesn't have PROCTIME
if grep -qi "PROCTIME" "$CREATE_SOURCE"; then
    echo "❌ Error: flink_job_create_source.sql still contains PROCTIME()"
    echo "   Please regenerate it with: ./prepare_flink_sql.sh"
    exit 1
fi

# Submit CREATE TABLE for source
echo "📤 Submitting: create-table-iot-sensor-data-v2"
delete_statement_by_name "create-table-iot-sensor-data-v2"

# Read and verify SQL content
SQL_CONTENT=$(cat "$CREATE_SOURCE")
if echo "$SQL_CONTENT" | grep -qi "PROCTIME"; then
    echo "❌ Error: SQL content still contains PROCTIME()"
    exit 1
fi

echo "   📄 SQL preview: ${SQL_CONTENT:0:100}..."
if OUTPUT=$(confluent flink statement create create-table-iot-sensor-data-v2 \
    --sql "$SQL_CONTENT" \
    --compute-pool "$FLINK_COMPUTE_POOL_ID" \
    --environment "$FLINK_COMPUTE_POOL_ENV" \
    --database "$KAFKA_DATABASE" 2>&1); then
    if echo "$OUTPUT" | grep -q "FAILED"; then
        echo "   ❌ Error creating table:"
        echo "$OUTPUT" | grep -A 5 "Status Detail" || echo "$OUTPUT"
        exit 1
    else
        echo "   ✓ Table created successfully"
    fi
else
    echo "   ❌ Error creating table"
    exit 1
fi
echo ""

# Submit CREATE TABLE for sink
echo "📤 Submitting: create-table-temperature-averages"
delete_statement_by_name "create-table-temperature-averages"

SQL_CONTENT=$(cat "$CREATE_SINK")
if OUTPUT=$(confluent flink statement create create-table-temperature-averages \
    --sql "$SQL_CONTENT" \
    --compute-pool "$FLINK_COMPUTE_POOL_ID" \
    --environment "$FLINK_COMPUTE_POOL_ENV" \
    --database "$KAFKA_DATABASE" 2>&1); then
    if echo "$OUTPUT" | grep -q "FAILED"; then
        echo "   ❌ Error creating table:"
        echo "$OUTPUT" | grep -A 5 "Status Detail" || echo "$OUTPUT"
        exit 1
    else
        echo "   ✓ Table created successfully"
    fi
else
    echo "   ❌ Error creating table"
    exit 1
fi
echo ""

echo "✅ Tables created successfully!"
