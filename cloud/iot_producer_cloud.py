import json
import os
import time
import random
from datetime import datetime
from confluent_kafka import Producer
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
    
    if not bootstrap_servers or not api_key or not api_secret:
        raise ValueError(
            "Missing required environment variables: "
            "KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET"
        )
    
    return {
        "bootstrap.servers": bootstrap_servers,
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": api_key,
        "sasl.password": api_secret,
    }

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

TOPIC = os.getenv("KAFKA_TOPIC", "devices")  # Default to "devices" if not set


def generate_iot_data(device_id: int):
    """Simulate a single IoT device reading."""
    return {
        "device_id": f"device-{device_id}",
        "timestamp": datetime.utcnow().isoformat(),
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
        producer = Producer(config)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please create a .env file with KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, and KAFKA_API_SECRET")
        return
    
    topic = os.getenv("KAFKA_TOPIC", "devices")
    print(f"🚀 Starting IoT producer... sending data to Kafka topic '{topic}'")
    device_count = 10  # simulate 10 IoT devices

    try:
        while True:
            for device_id in range(1, device_count + 1):
                data = generate_iot_data(device_id)
                producer.produce(
                    topic=topic,
                    value=json.dumps(data).encode('utf-8'),
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
