# IoT Streaming Pipeline - Cloud Deployment

This directory contains the cloud-based implementation of the IoT streaming pipeline using Confluent Cloud (Kafka + Flink) and DataStax Astra DB (Cassandra).

## Quick Start

1. **Set up environment**: Copy `.env.example` to `.env` and fill in your credentials
2. **Run the producer**: `python iot_producer_cloud.py` (sends IoT data to Kafka)
3. **Create Flink tables**: `./create_flink_tables.sh` (sets up source and sink tables)
4. **Submit Flink job**: `./submit_flink_insert.sh` (starts temperature aggregation)
5. **Run Cassandra consumer**: `python cassandra_sink_consumer.py` (sinks data to Astra DB)

For detailed setup instructions, see the sections below.

---

## Requirements
Python
Java
Astra DB
Confluent Cloud

## 1 Image setup

### a. Build and run producer locally (without Docker)

```bash
cd cloud
pip install -r requirements.txt
python iot_producer_cloud.py
```

### b. Build and run with Docker

```bash
# From project root
docker build -f cloud/DOCKERFILE -t iot-producer:latest cloud/
docker run --rm --env-file cloud/.env iot-producer:latest
```
there should be logs similar to the following
```
Sent: {'device_id': 'device-8', 'timestamp': '2025-11-24 19:35:48.012', 'temperature': 18.5, 'humidity': 58.19, 'status': 'OK'}
Sent: {'device_id': 'device-9', 'timestamp': '2025-11-24 19:35:48.012', 'temperature': 29.76, 'humidity': 40.46, 'status': 'OK'}
Sent: {'device_id': 'device-10', 'timestamp': '2025-11-24 19:35:48.012', 'temperature': 20.36, 'humidity': 70.76, 'status': 'FAIL'}
```

## Confluent Cloud setup (kafka and flink)

#### Create .env file

Copy the example file and add your credentials:
```bash
cp .env.example .env
```

```bash
brew install confluentinc/tap/cli
confluent login
confluent kafka cluster create iot_kafka_cluster --cloud "aws" --region "us-east-2"
```

you should see something like
```
+----------------------+---------------------------------------------------------+
| Current              | false                                                   |
| ID                   | lkc-000000                                              |
| Name                 | iot_kafka_cluster                                       |
| Type                 | BASIC                                                   |
| Ingress Limit (MB/s) | 250                                                     |
| Egress Limit (MB/s)  | 750                                                     |
| Storage              | 5000 GB                                                 |
| Cloud                | aws                                                     |
| Region               | us-east-2                                               |
| Availability         | single-zone                                             |
| Status               | PROVISIONING                                            |
| Endpoint             | SASL_SSL://<endpoint>.us-east-2.aws.confluent.cloud:9092|
| REST Endpoint        | https://<endpoint>.us-east-2.aws.confluent.cloud:443    |
+----------------------+---------------------------------------------------------+
```

```bash
confluent kafka topic create iot_sensor_data_v2 --cluster lkc-omx10j
confluent api-key create --resource <your-cluster-id> --description "iot-producer"
```

should give you 
```bash
+------------+------------------------------------------------------------------+
| API Key    | <key>                                                            |
| API Secret | <secret>                                                         |
+------------+------------------------------------------------------------------+
```

Also create a schema regitry key
```bash
confluent schema-registry cluster describe
confluent api-key create --resource lsrc-89xo85
```

confluent api-key create --resource lsrc-89xo85
It may take a couple of minutes for the API key to be ready.
Save the API key and secret. The secret is not retrievable later.
+------------+------------------------------------------------------------------+
| API Key    | TQDNR4434RN52O72                                                 |
| API Secret | cfltlw+/cNhSDTij8/s+6ONcUtdLWBJgH2I2hc6YZogDsw6Lp7JcyXn651o4mg+Q |

### Update .env file with your credentials


After creating your API key, update the `cloud/.env` file with your credentials:
```
KAFKA_BOOTSTRAP_SERVERS=<endpoint>.us-east-2.aws.confluent.cloud:9092
KAFKA_API_KEY=<your-api-key>
KAFKA_API_SECRET=<your-api-secret>
KAFKA_TOPIC=iot_sensor_data_v2
```

Then rebuild the Docker image:
```bash
docker build -f cloud/DOCKERFILE -t iot-producer:latest cloud/
```


Use Confluent Cloud's managed Flink service with **Flink SQL** - requires minimal local code!

### Set up Flink Compute Pool and Environment

```bash
confluent flink region use --cloud aws --region us-east-2
# Create a Flink compute pool (choose size based on your needs)
confluent flink compute-pool create iot-flink-pool \
  --cloud aws \
  --region us-east-2 \

# List your resources to get IDs
confluent flink compute-pool list
```

You'll see output like:
```

  Current |     ID      |      Name      | Environment | Current CFU | Max CFU | Cloud |  Region   |   Status     
----------+-------------+----------------+-------------+-------------+---------+-------+-----------+--------------
          | lfcp-zxnn7d | iot-flink-pool | env-x56xqq  |           0 |       5 | AWS   | us-east-2 | PROVISIONED  
```

Add ID and Environemt to .env and shell shortcuts for ease of use
```bash
vars="$(
  confluent flink compute-pool list \
    | grep -v '^-' \
    | grep -v 'ID' \
    | awk '{print "FLINK_COMPUTE_POOL_ID="$2 "\nFLINK_COMPUTE_POOL_ENV="$6}'
)"
printf "%s\n" "$vars" >> .env && \
eval "$(printf "export %s\n" "$vars")"
```

### Prepare Flink SQL File

The SQL file (`cloud/flink_job.sql`) uses placeholders for credentials. Use the helper script to prepare it:

```bash
cd cloud
./prepare_flink_sql.sh
```

This script reads your `.env` file and prints the `confluent flink statement create` commands to the console.

**Alternative: Edit manually**

If you prefer, you can edit `cloud/flink_job.sql` directly and replace:
- `${KAFKA_BOOTSTRAP_SERVERS}` with your bootstrap server
- `${KAFKA_API_KEY}` with your API key  
- `${KAFKA_API_SECRET}` with your API secret

### c. Submit Flink SQL Job

**Important:** Confluent Cloud Flink only accepts **one statement at a time**. You need to submit the CREATE TABLE statements first, then the INSERT statement.

**Option 1: Use the automated submission scripts (Recommended)**

```bash
cd cloud
./prepare_flink_sql.sh   # Prepare the SQL with your credentials
./create_flink_tables.sh # Creates the Source and Sink tables
./submit_flink_insert.sh # Submits the INSERT statement
```

**Note:** The `prepare_flink_sql.sh` script will print a ready-to-use command, but you'll need to extract individual statements if you want to submit them manually.

### Monitor Your Flink Job

```bash
# List all statements
confluent flink statement list --environment <your-environment-id>

# Get statement details
confluent flink statement describe <statement-id> --environment <your-environment-id>

# View logs
confluent flink statement logs <statement-id> --environment <your-environment-id>
```

### Stop/Delete Flink Job

```bash
# Stop a running statement
confluent flink statement stop <statement-id> --environment <your-environment-id>

# Delete a statement
confluent flink statement delete <statement-id> --environment <your-environment-id>
```

### Important Configuration Notes

**Timestamp Format:**
- The Python producer sends timestamps in SQL format: `yyyy-MM-dd HH:mm:ss.SSS`
- This format is required for Flink's `TO_TIMESTAMP()` function to work correctly
- The source table uses a computed column: `event_time AS TO_TIMESTAMP(\`timestamp\`)`

**Schema Alignment:**
- When Flink creates a table with the Confluent connector, it automatically registers an Avro schema in the Schema Registry
- The schema name follows the pattern: `<table_name>_value` in namespace `org.apache.flink.avro.generated.record`
- The Python producer's Avro schema must match this exact name (currently `iot_sensor_data_v2_value`)
- All fields are nullable to match Flink's schema expectations


## Cassandra Consumer Setup (Astra DB)

The `cassandra_sink_consumer.py` script bridges Confluent Cloud Kafka and DataStax Astra DB by:
- Consuming **raw IoT sensor data** from the `iot_sensor_data_v2` topic (Avro format)
- Consuming **aggregated temperature data** from the `temperature_averages` topic (Avro format, created by Flink)
- Writing both data streams to separate Cassandra tables in Astra DB

### Initial Astra DB Setup

#### Install Astra CLI

```bash
brew install datastax/astra-cli/astra
```

#### Create Database

1. Go to the [Astra Portal](https://astra.datastax.com)
2. Create a new Serverless database
3. Choose your cloud provider and region (e.g., AWS `eu-west-1`)
4. Note your database name and ID (e.g., `cassandra_db_sink` with `default` keyspace)

#### Generate Application Token

You need an application token to connect your application to Astra DB.

**Create token via the Astra Portal:**

1. In the [Astra Portal](https://astra.datastax.com), click the name of your database
2. On the **Overview** tab, in the **Database Details** section, click **Generate Token**
3. (Optional) Enter a description for the token
4. Set the expiration (default is "Never expire")
5. **Important:** Select **Admin User** role
6. Click **Generate Token** and copy the token (starts with `AstraCS:...`)
7. **Important:** Store the token securely - it's only shown once!

**Optional: Set up Astra CLI for future token management**

Once you have your first token, you can configure the CLI:

```bash
# Setup Astra CLI (requires your initial token)
astra setup
```

> **Note:** You must create your first token via the Astra Portal UI. After running `astra setup` with that token, you can create additional tokens using the CLI.

For more details, see: https://docs.datastax.com/en/astra-db-serverless/administration/manage-application-tokens.html

---

### Consumer Setup

#### Prerequisites

1. **Astra DB Database**: Created (e.g., `cassandra_db_sink`)
2. **Kafka Topics**: Both `iot_sensor_data_v2` and `temperature_averages` exist
3. **Secure Connect Bundle**: Downloaded from Astra Portal
4. **Application Token**: Generated with Admin User role

### Step 1: Download Secure Connect Bundle

The consumer needs the Astra DB secure connect bundle to authenticate.

**Using Astra Portal:**
1. Go to [Astra Portal](https://astra.datastax.com)
2. Select your database
3. Click **Connect** tab → **Driver** → **Download Bundle**
4. If using the Astra Portal's "Download Bundle" option, copy the provided `curl` command. This command will automatically save the bundle to the correct `~/.astra/scb/` directory.

**Using Astra CLI:**
```bash
# Find your database ID
astra db list

# Download the bundle, also downloads to the correct file location
astra db download-scb <DB_ID>
```

### Step 2: Update .env File

Add Astra DB credentials to `cloud/.env`:
```bash
# DataStax Astra DB Configuration
ASTRA_DB_ID=your-database-id
ASTRA_DB_REGION=your-region  # e.g., eu-west-1
ASTRA_DB_APPLICATION_TOKEN=AstraCS:your-token-here
ASTRA_DB_KEYSPACE=default
```

### Step 3: Run the Consumer

```bash
cd cloud
python cassandra_sink_consumer.py
```

**Expected Output:**
```
[INFO] Connecting to Astra DB (ID: 658fd008-...)...
[INFO] Connected to Astra DB keyspace: default
[INFO] Table 'iot_sensor_data' is ready
[INFO] Table 'temperature_averages' is ready
[INFO] Subscribed to topics: iot_sensor_data_v2, temperature_averages
[INFO] Waiting for messages...
[SUCCESS] IoT Data: device=device-1, temp=22.45°C, humidity=65.30%, status=OK
[SUCCESS] Avg Temp: device=device-1, avg_temp=22.45°C, window_start=2025-11-24 19:00:00
```

The consumer automatically creates the required tables on startup:
- `iot_sensor_data`: Stores raw IoT sensor readings
- `temperature_averages`: Stores Flink-aggregated temperature data

#### Optional: Manual Table Creation

If you prefer to create the tables manually before running the consumer, you can use the Astra Portal CQL Console or the Astra CLI.

**Using Astra Portal CQL Console:**

1. Go to [Astra Portal](https://astra.datastax.com)
2. Select your database
3. Click **CQL Console** tab
4. Run the following commands:

```sql
-- Table for raw IoT sensor data
CREATE TABLE IF NOT EXISTS iot_sensor_data (
    device_id TEXT,
    timestamp TIMESTAMP,
    temperature DOUBLE,
    humidity DOUBLE,
    status TEXT,
    PRIMARY KEY (device_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- Table for aggregated temperature averages
CREATE TABLE IF NOT EXISTS temperature_averages (
    device_id TEXT,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    avg_temperature DOUBLE,
    PRIMARY KEY (device_id, window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
```

**Using Astra CLI:**

```bash
# Create a SQL file (e.g., avg_temp_csql.sql) with the CREATE TABLE statements above
# Then execute it:
astra db cqlsh exec cassandra_db_sink -k default -f avg_temp_csql.sql
```


### Step 4: Verify Data in Astra DB

Using the CQL Console in Astra Portal:

```sql
-- View raw IoT sensor data
SELECT * FROM iot_sensor_data LIMIT 10;

-- View data for a specific device
SELECT * FROM iot_sensor_data 
WHERE device_id = 'device-1' 
LIMIT 5;

-- View aggregated temperature averages
SELECT * FROM temperature_averages LIMIT 10;

-- Count total records
SELECT COUNT(*) FROM iot_sensor_data;
SELECT COUNT(*) FROM temperature_averages;
```

### Complete Pipeline Architecture

```
IoT Producer → Kafka (iot_sensor_data_v2) → Flink (aggregation) → Kafka (temperature_averages) → Python Consumer → Astra DB
```

You should have three processes running:
1. **Producer**: `python iot_producer_cloud.py` → Sends raw IoT data to Kafka
2. **Flink Job**: `iot-temperature-aggregation` → Aggregates data in 1-minute windows
3. **Consumer**: `python cassandra_sink_consumer.py` → Writes both streams to Astra DB

### Cassandra Consumer Troubleshooting

#### Authentication Error

```
AuthenticationFailed: Bad credentials
```

**Solution**: Regenerate token with **Admin User** role, not just Database Administrator.

#### Bundle Not Found

```
Secure connect bundle not found
```

**Solution**: Download the bundle to the path: `~/.astra/scb/scb_{ASTRA_DB_ID}-1_{ASTRA_DB_REGION}.zip`

#### No Messages Received

**Check**:
1. Is the Flink job running? `confluent flink statement list`
2. Is the producer sending data? Check producer logs
3. Do both topics exist? `confluent kafka topic list`
4. Are Schema Registry credentials correct in `.env`?

#### Connection Timeout

**Solution**: Check your network/firewall settings. Astra DB requires outbound HTTPS access.

### Complete Data Flow Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │                                     │
IoT Producer → Kafka (iot_sensor_data_v2) → Flink (aggregation) → Kafka (temperature_averages)
                    │                                                     │
                    │                                                     │
                    └──────────────────┐                    ┌─────────────┘
                                       │                    │
                                       ▼                    ▼
                                Python Consumer → Astra DB (both tables)
```

**Data Streams:**
- **Raw IoT Data**: `iot_sensor_data_v2` topic → Consumer → `iot_sensor_data` table
- **Aggregated Data**: Flink processes raw data → `temperature_averages` topic → Consumer → `temperature_averages` table

---

## Google Cloud Setup (Optional)


```bash
brew install --cask gcloud-cli
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:"$PATH"
```

To use gcloud-cli, you may need to add the /opt/homebrew/share/google-cloud-sdk/bin directory
to your PATH environment variable, e.g. (for Bash shell):

continue the setup with
```bash
gcloud init
```
create a new cloud project, I named it iot_producer

---

## Troubleshooting

### Flink Job Issues

**"Unknown identifier 'event_time'" error:**
- The source table definition is outdated in Confluent Cloud
- Solution: Drop and recreate the table using `./create_flink_tables.sh`

**"RowTime field should not be null" or "SourceInvalidValue" errors:**
- Old data in Kafka topic has incompatible timestamp format
- Solution: The source table is configured with `'scan.startup.mode' = 'latest-offset'` to skip old data
- Restart the producer to send fresh data with the correct format

**Flink job stuck in PENDING:**
- Check that the Flink compute pool has available resources
- Verify the Kafka topic exists and has data
- Check statement logs: `confluent flink statement logs <statement-id> --environment <env-id>`

### Producer Issues

**SchemaRegistryError (HTTP 409):**
- Schema mismatch between producer and Flink-created schema
- Solution: Ensure producer schema matches the table name (e.g., `iot_sensor_data_v2_value`)
- All fields must be nullable to match Flink's expectations

### Cassandra Consumer Issues

**No data appearing in Astra DB:**
- Verify the consumer is subscribed to the correct topics
- Check that the Flink job is in RUNNING state
- Ensure the secure connect bundle is downloaded and in the correct location

**Connection refused:**
- Download the secure connect bundle from Astra Portal > Database > Connect > Driver
- Verify `ASTRA_DB_ID` and `ASTRA_DB_REGION` match your database configuration

## Next Steps

- Cloud deployment of the producer and consumer
- Visualization of the data in a dashboard