import json
import os
import time
import random
from datetime import datetime
from confluent_kafka import Producer as CKProducer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from dotenv import load_dotenv

load_dotenv()

# =========================
# Configuration from Environment Variables
# =========================
def getConfig():
    """Get Kafka configuration from environment variables."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    api_key = os.getenv("KAFKA_API_KEY")
    api_secret = os.getenv("KAFKA_API_SECRET")
    schema_registry_url = os.getenv("SCHEMA_REGISTRY_URL")
    sr_secret = os.getenv("SCHEMA_REGISTRY_SECRET")
    sr_api_key = os.getenv("SCHEMA_REGISTRY_API_KEY")
    
    if not bootstrap_servers or not api_key or not api_secret:
        raise ValueError(
            "Missing required environment variables: "
            "KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET"
        )
    
    # Extract schema registry URL from bootstrap servers if not provided
    if not schema_registry_url and bootstrap_servers:
        # Confluent Cloud Schema Registry URL pattern
        cluster_id = bootstrap_servers.split('.')[0].replace('pkc-', '')
        schema_registry_url = f"https://psrc-{cluster_id}.us-east-2.aws.confluent.cloud"
    
    return {
        "bootstrap.servers": bootstrap_servers,
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": api_key,
        "sasl.password": api_secret,
        "schema.registry.url": schema_registry_url,
        "schema.registry.basic.auth.user.info": f"{sr_api_key}:{sr_secret}",
    }

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

TOPIC = os.getenv("KAFKA_TOPIC", "iot_sensor_data")  # Default to "iot_sensor_data" if not set


def generate_iot_data(device_id: int):
    """Simulate a single IoT device reading."""
    # Use epoch milliseconds (BIGINT) for better Flink compatibility
    now = datetime.utcnow()
    return {
        "device_id": f"device-{device_id}",
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # Format: yyyy-MM-dd HH:mm:ss.SSS
        "temperature": round(random.uniform(15.0, 30.0), 2),
        "humidity": round(random.uniform(30.0, 80.0), 2),
        "status": random.choice(["OK", "WARN", "FAIL"]),
    }

# =========================
# Main Loop
# =========================
def main():
    # Initialize producer with config from environment variables
    try:
        config = getConfig()
        producer = CKProducer({
            "bootstrap.servers": config["bootstrap.servers"],
            "security.protocol": config["security.protocol"],
            "sasl.mechanisms": config["sasl.mechanisms"],
            "sasl.username": config["sasl.username"],
            "sasl.password": config["sasl.password"],
        })
        
        # Initialize Schema Registry client
        schema_registry_client = SchemaRegistryClient({
            "url": config["schema.registry.url"],
            "basic.auth.user.info": config["schema.registry.basic.auth.user.info"],
        })
        
        # Define Avro schema for IoT device data
        # Using BIGINT (long) for timestamp as epoch milliseconds for better Flink compatibility
        avro_schema = """
        {
            "type": "record",
            "name": "iot_sensor_data_v2_value",
            "namespace": "org.apache.flink.avro.generated.record",
            "fields": [
                {"name": "device_id", "type": ["null", "string"], "default": null},
                {"name": "timestamp", "type": ["null", "string"], "default": null},
                {"name": "temperature", "type": ["null", "double"], "default": null},
                {"name": "humidity", "type": ["null", "double"], "default": null},
                {"name": "status", "type": ["null", "string"], "default": null}
            ]
        }
        """
        
        topic = os.getenv("KAFKA_TOPIC", "iot_sensor_data")
        subject = f"{topic}-value"
        avro_serializer = AvroSerializer(schema_registry_client, avro_schema)
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please create a .env file with KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, and KAFKA_API_SECRET")
        return
    except Exception as e:
        print(f"❌ Error initializing producer: {e}")
        return
    
    print(f"🚀 Starting IoT producer... sending data to Kafka topic '{topic}'")
    device_count = 10  # simulate 10 IoT devices

    try:
        while True:
            for device_id in range(1, device_count + 1):
                data = generate_iot_data(device_id)
                # Serialize using Avro serializer
                serialized_value = avro_serializer(data, SerializationContext(topic, MessageField.VALUE))
                producer.produce(
                    topic=topic,
                    value=serialized_value,
                    callback=delivery_report
                )
                print(f"Sent: {data}")
            producer.flush()

            # Wait before next batch
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    finally:
        producer.flush()

if __name__ == "__main__":
    main()
