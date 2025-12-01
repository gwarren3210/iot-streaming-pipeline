import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

# =========================
# Configuration
# =========================
KAFKA_BROKER = "localhost:9092"   # or your broker hostname
TOPIC = "iot_sensors"

# =========================
# Initialize Kafka Producer
# =========================
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# =========================
# Helper Functions
# =========================
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
    print(f"🚀 Starting IoT producer... sending data to Kafka topic '{TOPIC}'")
    device_count = 10  # simulate 10 IoT devices

    try:
        while True:
            for device_id in range(1, device_count + 1):
                data = generate_iot_data(device_id)
                producer.send(TOPIC, value=data)
                print(f"Sent: {data}")
            producer.flush()

            # Wait before next batch
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
