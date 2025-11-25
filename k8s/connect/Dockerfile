FROM confluentinc/cp-kafka-connect:latest

# Install Cassandra Sink Connector
RUN confluent-hub install --no-prompt datastax/kafka-connect-cassandra-sink:latest

# Set environment variables for Connect
ENV CONNECT_PLUGIN_PATH="/usr/share/java,/usr/share/confluent-hub-components"
