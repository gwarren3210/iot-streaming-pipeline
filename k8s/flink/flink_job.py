from pyflink.table import EnvironmentSettings, TableEnvironment
import os

def main():
    # Create Table Environment
    env_settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(env_settings)

    # Add Kafka Connector JAR
    # The JAR is expected to be in the /opt/flink/lib directory in the image
    # or we can add it explicitly if needed.
    # In the Dockerfile we copied it to lib/, so it should be picked up automatically.
    # However, for safety in some environments, we can add it.
    jar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "flink-sql-connector-kafka.jar"))
    if os.path.exists(jar_path):
        t_env.get_config().get_configuration().set_string("pipeline.jars", f"file://{jar_path}")

    # Read SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), "job.sql")
    with open(sql_file_path, "r") as f:
        sql_statements = f.read().split(";")

    # Execute SQL statements
    for statement in sql_statements:
        statement = statement.strip()
        if statement:
            print(f"Executing SQL: {statement}")
            t_env.execute_sql(statement)

if __name__ == "__main__":
    main()
