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
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "client.id": "iot-producer",
    }
    return conf

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

TOPIC = os.getenv("KAFKA_TOPIC", "iot_sensor_data")

def generate_iot_data(device_id: int):
    """Simulate a single IoT device reading."""
    now = datetime.utcnow()
    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return {
        "device_id": f"device-{device_id}",
        "timestamp": timestamp_str,
        "temperature": round(random.uniform(15.0, 30.0), 2),
        "humidity": round(random.uniform(30.0, 80.0), 2),
        "status": random.choice(["OK", "WARN", "FAIL"]),
    }

# =========================
# Main Loop
# =========================
def main():
    # Initialize producer
    try:
        config = getConfig()
        producer = Producer(config)
        
        topic = TOPIC
        
    except Exception as e:
        print(f"❌ Error initializing producer: {e}")
        return
    
    print(f"🚀 Starting IoT producer... sending data to Kafka topic '{topic}' at {config['bootstrap.servers']}")
    device_count = 10

    try:
        while True:
            for device_id in range(1, device_count + 1):
                data = generate_iot_data(device_id)
                # Serialize to JSON
                serialized_value = json.dumps(data).encode('utf-8')
                
                producer.produce(
                    topic=topic,
                    value=serialized_value,
                    callback=delivery_report
                )
                print(f"Sent: {data}")
            producer.flush()

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    finally:
        producer.flush()

if __name__ == "__main__":
    main()
