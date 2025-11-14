# learnings
- docker compose stack steady after first restart; cache warms and topics stay declared
- pyflink job handles `iot_sensors` stream after fixing timestamp parsing to isoformat

# struggles
- flink python runner logged `NoClassDefFoundError: org/apache/flink/connector/kafka/source/KafkaSourceBuilder` because connector jar absent in lib path
- cassandra bootstrap kept throwing `NoHostAvailable` until service fully healthy and gossip ready
- initial Cassandra query attempts failed with `InvalidRequest: Error from server: code=2200` since keyspace and table not created yet

# solutions
- downloaded connector jar via `flink-job/download_kafka_jar.sh`, script pulls exact kafka sql connector and drops it beside job so `env.add_jars` sees it
- wrapped schema bootstrapping in compose exec wait loop (`docker/setup_cassandra.sh`) so script only pipes CQL after `DESCRIBE KEYSPACES` succeeds
- expanded README quickstart with explicit `CREATE KEYSPACE` + `CREATE TABLE` CQL and sample select so manual `cqlsh` sessions no longer error out