#!/usr/bin/env python3
"""
Kafka Consumer that reads IoT data from Confluent Cloud
and writes it to DataStax Astra DB (Cassandra).

This script acts as a bridge between Confluent Cloud Kafka and Astra DB,
consuming messages from both 'iot_sensor_data' and 'temperature_averages' topics
and inserting them into corresponding Cassandra tables.
"""

import os
import json
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

# Load environment variables
load_dotenv()

# Kafka Configuration
KAFKA_CONFIG = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': os.getenv('KAFKA_API_KEY'),
    'sasl.password': os.getenv('KAFKA_API_SECRET'),
    'group.id': 'cassandra-sink-consumer-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 5000,
}

# Schema Registry Configuration
SCHEMA_REGISTRY_CONFIG = {
    'url': os.getenv('SCHEMA_REGISTRY_URL'),
    'basic.auth.user.info': f"{os.getenv('SCHEMA_REGISTRY_API_KEY')}:{os.getenv('SCHEMA_REGISTRY_API_SECRET')}"
}

# Astra DB Configuration
ASTRA_DB_ID = os.getenv('ASTRA_DB_ID')
ASTRA_DB_REGION = os.getenv('ASTRA_DB_REGION', 'eu-west-1')
ASTRA_DB_TOKEN = os.getenv('ASTRA_DB_APPLICATION_TOKEN')
ASTRA_DB_KEYSPACE = os.getenv('ASTRA_DB_KEYSPACE', 'default')

# Topics to consume from
KAFKA_TOPICS = ['iot_sensor_data', 'temperature_averages']

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\n[INFO] Shutdown signal received. Closing consumer...")
    running = False


def connect_to_astra():
    """
    Connect to DataStax Astra DB using the secure connect bundle.
    
    Returns:
        cassandra.cluster.Session: Connected Cassandra session
    """
    print(f"[INFO] Connecting to Astra DB (ID: {ASTRA_DB_ID})...")
    
    # Construct the secure connect bundle path
    secure_connect_bundle = os.path.expanduser(f"~/.astra/scb/scb_{ASTRA_DB_ID}-1_{ASTRA_DB_REGION}.zip")
    
    # Check if bundle exists
    if not os.path.exists(secure_connect_bundle):
        print(f"[ERROR] Secure connect bundle not found at: {secure_connect_bundle}")
        print("[INFO] Download it from Astra Portal > Database > Connect > Driver")
        sys.exit(1)
    
    # Create authentication provider
    auth_provider = PlainTextAuthProvider('token', ASTRA_DB_TOKEN)
    
    # Create cluster connection
    cluster = Cluster(
        cloud={
            'secure_connect_bundle': secure_connect_bundle
        },
        auth_provider=auth_provider
    )
    
    # Connect to keyspace
    session = cluster.connect(ASTRA_DB_KEYSPACE)
    print(f"[INFO] Connected to Astra DB keyspace: {ASTRA_DB_KEYSPACE}")
    
    return session


def create_tables_if_not_exist(session):
    """    
    Args:
        session: Cassandra session
    """
    # Table for raw IoT sensor data
    create_iot_table_query = """
    CREATE TABLE IF NOT EXISTS iot_sensor_data (
        device_id TEXT,
        timestamp TIMESTAMP,
        temperature DOUBLE,
        humidity DOUBLE,
        status TEXT,
        PRIMARY KEY (device_id, timestamp)
    ) WITH CLUSTERING ORDER BY (timestamp DESC);
    """
    
    # Table for aggregated temperature averages
    create_avg_table_query = """
    CREATE TABLE IF NOT EXISTS temperature_averages (
        device_id TEXT,
        window_start TIMESTAMP,
        window_end TIMESTAMP,
        avg_temperature DOUBLE,
        PRIMARY KEY (device_id, window_start)
    ) WITH CLUSTERING ORDER BY (window_start DESC);
    """
    
    try:
        session.execute(create_iot_table_query)
        print("[INFO] Table 'iot_sensor_data' is ready")
        session.execute(create_avg_table_query)
        print("[INFO] Table 'temperature_averages' is ready")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        sys.exit(1)


def insert_iot_sensor_record(session, record):
    """    
    Args:
        session: Cassandra session
        record: Dictionary containing the IoT sensor data
    """
    insert_query = """
    INSERT INTO iot_sensor_data (device_id, timestamp, temperature, humidity, status)
    VALUES (?, ?, ?, ?, ?)
    """
    
    prepared = session.prepare(insert_query)
    
    try:
        # Parse timestamp - handle both SQL format and ISO 8601 format
        timestamp_str = record.get('timestamp')
        try:
            # Try SQL format first: 'yyyy-MM-dd HH:mm:ss.SSS'
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            # Fallback to ISO 8601 format for old data: '2025-11-24T18:28:25.155390'
            timestamp = datetime.fromisoformat(timestamp_str)
        
        session.execute(prepared, (
            record['device_id'],
            timestamp,
            float(record['temperature']),
            float(record['humidity']),
            record['status']
        ))
        
        print(f"[SUCCESS] IoT Data: device={record['device_id']}, "
              f"temp={record['temperature']:.2f}°C, "
              f"humidity={record['humidity']:.2f}%, "
              f"status={record['status']}")
        
    except Exception as e:
        print(f"[ERROR] Failed to insert IoT record: {e}")
        print(f"[DEBUG] Record: {record}")


def insert_temperature_average_record(session, record):
    """    
    Args:
        session: Cassandra session
        record: Dictionary containing the temperature average data
    """
    insert_query = """
    INSERT INTO temperature_averages (device_id, window_start, window_end, avg_temperature)
    VALUES (?, ?, ?, ?)
    """
    
    prepared = session.prepare(insert_query)
    
    try:
        # Parse timestamps if they're strings
        window_start = record['window_start']
        window_end = record['window_end']
        
        # Convert to datetime if needed
        if isinstance(window_start, str):
            window_start = datetime.fromisoformat(window_start.replace('Z', '+00:00'))
        if isinstance(window_end, str):
            window_end = datetime.fromisoformat(window_end.replace('Z', '+00:00'))
        
        session.execute(prepared, (
            record['device_id'],
            window_start,
            window_end,
            float(record['avg_temperature'])
        ))
        
        print(f"[SUCCESS] Avg Temp: device={record['device_id']}, "
              f"avg_temp={record['avg_temperature']:.2f}°C, "
              f"window_start={window_start}")
        
    except Exception as e:
        print(f"[ERROR] Failed to insert record: {e}")
        print(f"[DEBUG] Record: {record}")


def consume_and_sink():
    """
    Main consumer loop: read from Kafka and write to Cassandra.
    """
    session = connect_to_astra()
    create_tables_if_not_exist(session)
    
    schema_registry_client = SchemaRegistryClient(SCHEMA_REGISTRY_CONFIG)
    
    avro_deserializer = AvroDeserializer(
        schema_registry_client=schema_registry_client
    )
    
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe(KAFKA_TOPICS)
    
    print(f"[INFO] Subscribed to topics: {', '.join(KAFKA_TOPICS)}")
    print("[INFO] Waiting for messages... (Press Ctrl+C to stop)")
    
    try:
        while running:
            # Poll for messages
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    continue
                else:
                    print(f"[ERROR] Kafka error: {msg.error()}")
                    continue
            
            # Parse message value based on topic
            try:
                topic = msg.topic()
                
                if topic == 'iot_sensor_data':
                    # Deserialize Avro message
                    value = avro_deserializer(
                        msg.value(),
                        SerializationContext(topic, MessageField.VALUE)
                    )
                    if value:
                        insert_iot_sensor_record(session, value)
                
                elif topic == 'temperature_averages':
                    # Deserialize Avro message (Flink SQL output)
                    value = avro_deserializer(
                        msg.value(),
                        SerializationContext(topic, MessageField.VALUE)
                    )
                    if value:
                        insert_temperature_average_record(session, value)
                
                else:
                    print(f"[WARNING] Unknown topic: {topic}")
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to decode JSON: {e}")
                print(f"[DEBUG] Raw message: {msg.value()}")
            except Exception as e:
                print(f"[ERROR] Unexpected error processing message: {e}")
    
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    
    finally:
        # Clean up
        print("[INFO] Closing consumer...")
        consumer.close()
        session.cluster.shutdown()
        print("[INFO] Consumer closed successfully")


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Validate environment variables
    required_vars = [
        'KAFKA_BOOTSTRAP_SERVERS',
        'KAFKA_API_KEY',
        'KAFKA_API_SECRET',
        'SCHEMA_REGISTRY_URL',
        'SCHEMA_REGISTRY_API_KEY',
        'SCHEMA_REGISTRY_API_SECRET',
        'ASTRA_DB_ID',
        'ASTRA_DB_APPLICATION_TOKEN'
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Start consuming
    consume_and_sink()
