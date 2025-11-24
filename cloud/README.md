## Requirements
Docker

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
Sent: {'device_id': 'device-8', 'timestamp': '2025-11-17T15:35:48.012624', 'temperature': 18.5, 'humidity': 58.19, 'status': 'OK'}
Sent: {'device_id': 'device-9', 'timestamp': '2025-11-17T15:35:48.012729', 'temperature': 29.76, 'humidity': 40.46, 'status': 'OK'}
Sent: {'device_id': 'device-10', 'timestamp': '2025-11-17T15:35:48.012816', 'temperature': 20.36, 'humidity': 70.76, 'status': 'FAIL'}
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
confluent kafka topic create iot_sensor_data --cluster lkc-omx10j
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

### 4. Update .env file with your credentials


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

## 3. Confluent Cloud Flink (Managed Service) - **RECOMMENDED**

Use Confluent Cloud's managed Flink service with **Flink SQL** - requires minimal local code!

### a. Set up Flink Compute Pool and Environment

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

### b. Prepare Flink SQL File

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
