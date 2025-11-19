## Requirements
Docker

## 1 Image setup

### a. Build and run locally (without Docker)

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
Sent: {'device_id': 'device-8', 'timestamp': '2025-11-17T15:35:48.012624', 'temperature': 18.5, 'humidity': 58.19, 'status': 'OK'}
Sent: {'device_id': 'device-9', 'timestamp': '2025-11-17T15:35:48.012729', 'temperature': 29.76, 'humidity': 40.46, 'status': 'OK'}
Sent: {'device_id': 'device-10', 'timestamp': '2025-11-17T15:35:48.012816', 'temperature': 20.36, 'humidity': 70.76, 'status': 'FAIL'}
```

## Confluent Cloud setup (kafka and flink)

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
confluent kafka topic create devices --cluster lkc-000000
confluent api-key create --resource <your-cluster-id> --description "iot-producer"
```

should give you 
```bash
+------------+------------------------------------------------------------------+
| API Key    | <key>                                                            |
| API Secret | <secret>                                                         |
+------------+------------------------------------------------------------------+
```

### 4. Update .env file with your credentials

#### Create .env file

Copy the example file and add your credentials:
```bash
cp .env.example .env
```

After creating your API key, update the `cloud/.env` file with your credentials:
```
KAFKA_BOOTSTRAP_SERVERS=<endpoint>.us-east-2.aws.confluent.cloud:9092
KAFKA_API_KEY=<your-api-key>
KAFKA_API_SECRET=<your-api-secret>
KAFKA_TOPIC=devices
```

Then rebuild the Docker image:
```bash
docker build -f cloud/DOCKERFILE -t iot-producer:latest cloud/
```




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


## 2. Flink Consumer Setup

### a. Install Flink Dependencies

The Flink job requires additional dependencies. Install them:

```bash
cd cloud
pip install apache-flink>=1.20.0
```

### b. Download Kafka Connector JAR

The Flink job needs the Kafka connector JAR. Download it:

```bash
cd ../flink-job
./download_kafka_jar.sh
```

This will download `flink-sql-connector-kafka.jar` to the `flink-job` directory.

### c. Update .env file (if needed)

Add an optional consumer group ID to your `.env` file:

```
KAFKA_GROUP_ID=flink-iot-consumer
```

If not set, it defaults to `flink-iot-consumer`.

### d. Run Flink Job

From the `cloud` directory:

```bash
cd cloud
python flink_job_cloud.py
```

The Flink job will:
- Connect to Confluent Cloud Kafka using credentials from `.env`
- Consume messages from the `devices` topic (or `KAFKA_TOPIC` if set)
- Compute 5-minute windowed averages of temperature per device
- Print results to console

### e. Verify Data Flow

1. **Start the producer** (in one terminal):
   ```bash
   cd cloud
   python iot_producer_cloud.py
   ```

2. **Start the Flink consumer** (in another terminal):
   ```bash
   cd cloud
   python flink_job_cloud.py
   ```

You should see:
- Producer sending messages to Kafka
- Flink consuming and processing messages
- Windowed averages printed every 5 minutes

## 3. Confluent Cloud Flink (Managed Service) - **RECOMMENDED**

Use Confluent Cloud's managed Flink service with **Flink SQL** - requires minimal local code!

### a. Set up Flink Compute Pool and Environment

```bash
# Create a Flink compute pool (choose size based on your needs)
confluent flink compute-pool create iot-flink-pool \
  --cloud aws \
  --region us-east-2 \
  --max-cfu 1

# Create a Flink environment
confluent flink environment create iot-flink-env

# List your resources to get IDs
confluent flink compute-pool list
confluent flink environment list
```

You'll see output like:
```
+-------------+------------------+
| ID          | Name              |
+-------------+------------------+
| lfcp-xxxxx  | iot-flink-pool   |
+-------------+------------------+
```

### b. Prepare Flink SQL File

The SQL file (`cloud/flink_job.sql`) uses placeholders for credentials. Use the helper script to prepare it:

```bash
cd cloud
./prepare_flink_sql.sh
```

This script reads your `.env` file and creates `flink_job_prepared.sql` with your actual credentials.

**Alternative: Edit manually**

If you prefer, you can edit `cloud/flink_job.sql` directly and replace:
- `${KAFKA_BOOTSTRAP_SERVERS}` with your bootstrap server
- `${KAFKA_API_KEY}` with your API key  
- `${KAFKA_API_SECRET}` with your API secret

### c. Submit Flink SQL Job

```bash
# First, prepare the SQL file with your credentials
cd cloud
./prepare_flink_sql.sh

# Then submit the prepared SQL statement
confluent flink statement create \
  --compute-pool <your-compute-pool-id> \
  --environment <your-environment-id> \
  --statement-file cloud/flink_job_prepared.sql \
  --name "iot-temperature-aggregation"
```

### d. Monitor Your Flink Job

```bash
# List all statements
confluent flink statement list --environment <your-environment-id>

# Get statement details
confluent flink statement describe <statement-id> --environment <your-environment-id>

# View logs
confluent flink statement logs <statement-id> --environment <your-environment-id>
```

### e. Stop/Delete Flink Job

```bash
# Stop a running statement
confluent flink statement stop <statement-id> --environment <your-environment-id>

# Delete a statement
confluent flink statement delete <statement-id> --environment <your-environment-id>
```

### Benefits of Managed Flink:

✅ **No local dependencies** - No need to install PyFlink or JARs  
✅ **Scalable** - Automatically scales based on workload  
✅ **Managed** - Confluent handles infrastructure  
✅ **SQL-based** - Simple SQL syntax, easier to maintain  
✅ **Integrated** - Seamlessly connects to your Confluent Cloud Kafka cluster  

For more details, see: https://docs.confluent.io/cloud/current/flink/index.html

## Confluent cloud setup
