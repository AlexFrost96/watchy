import os
import mysql.connector
from datetime import datetime, timedelta
import logging
import sys

BASE_DIR = "/var/log/netflow/"
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "watchy",
    "password": "zudzar-xacvav-cyshyp-0azvyl-luqcyf-wimFol",
    "database": "watchy_db"
}

TABLE_NAME = "netflow"

# Configure logging
logging.basicConfig(
    filename="db_operations.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def log_to_file(message):
    """
    Writing log messages to a file.
    """
    logging.info(message)


def parse_file_name_to_time_range(file_name):
    """
    Converts nfcapd file name to a specific time range.

    Args:
        file_name (str): File name in the format 'nfcapd.YYYYMMDDHHMM'.

    Returns:
        str: Time range in the format 'YYYY/MM/DD.HH:MM:SS-YYYY/MM/DD.HH:MM:SS'.
    """
    # Extract timestamp from file name
    timestamp_str = file_name.split(".")[1]
    timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M")

    # Calculate the end time (5 minutes later)
    end_time = timestamp + timedelta(minutes=5)

    # Format the start and end time
    start_time_formatted = timestamp.strftime("%Y/%m/%d.%H:%M:%S")
    end_time_formatted = end_time.strftime("%Y/%m/%d.%H:%M:%S")

    # Combine into the time range format
    time_range = f"{start_time_formatted}-{end_time_formatted}"

    return time_range


def create_table_if_not_exists(connection):
    """
    Creates the MariaDB table if it does not exist.
    """
    query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        Timestamp DATETIME NOT NULL,
        Ident VARCHAR(255) NOT NULL,
        Flows INT,
        Flows_tcp INT,
        Flows_udp INT,
        Flows_icmp INT,
        Flows_other INT,
        Packets INT,
        Packets_tcp INT,
        Packets_udp INT,
        Packets_icmp INT,
        Packets_other INT,
        Bytes BIGINT,
        Bytes_tcp BIGINT,
        Bytes_udp BIGINT,
        Bytes_icmp BIGINT,
        Bytes_other BIGINT,
        First DATETIME,
        Last DATETIME,
        msec_first BIGINT,
        msec_last BIGINT,
        Sequence_failures INT
    );
    """
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        log_to_file("Table created successfully or already exists.")
    except Exception as e:
        log_to_file(f"Error creating table: {e}")
        raise


def insert_data_to_db(connection, data):
    """
    Inserts data into the MariaDB table.
    """
    query = f"""
        INSERT INTO {TABLE_NAME} (
            Timestamp, Ident, Flows, Flows_tcp, Flows_udp, Flows_icmp, Flows_other,
            Packets, Packets_tcp, Packets_udp, Packets_icmp, Packets_other,
            Bytes, Bytes_tcp, Bytes_udp, Bytes_icmp, Bytes_other,
            First, Last, msec_first, msec_last, Sequence_failures
        )
        VALUES (
            %(Timestamp)s, %(Ident)s, %(Flows)s, %(Flows_tcp)s, %(Flows_udp)s, %(Flows_icmp)s, %(Flows_other)s,
            %(Packets)s, %(Packets_tcp)s, %(Packets_udp)s, %(Packets_icmp)s, %(Packets_other)s,
            %(Bytes)s, %(Bytes_tcp)s, %(Bytes_udp)s, %(Bytes_icmp)s, %(Bytes_other)s,
            %(First)s, %(Last)s, %(msec_first)s, %(msec_last)s, %(Sequence_failures)s
        )
    """
    try:
        cursor = connection.cursor()
        log_to_file(f"Preparing to insert data: {data}")
        cursor.execute(query, data)
        connection.commit()
        log_to_file("Data inserted successfully.")
    except Exception as e:
        log_to_file(f"Error inserting data: {e}")
        raise


def process_file(file_path, connection):
    """
    Processes a single file and inserts data into the database.
    """
    try:
        file_name = file_path.split(BASE_DIR)[1].split("/")[-1]
        timestamp_str = file_name.split(".")[1]
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M")
        # time_range = parse_file_name_to_time_range(file_name)
        #file_path = BASE_DIR + file_path.split(BASE_DIR)[1].split("/")[0] + "/"
        cmd = f"nfdump -r {file_path} -I"
        result = os.popen(cmd).read()
        data = {
            "Timestamp": timestamp,
            "Ident": None,
            "Flows": None,
            "Flows_tcp": None,
            "Flows_udp": None,
            "Flows_icmp": None,
            "Flows_other": None,
            "Packets": None,
            "Packets_tcp": None,
            "Packets_udp": None,
            "Packets_icmp": None,
            "Packets_other": None,
            "Bytes": None,
            "Bytes_tcp": None,
            "Bytes_udp": None,
            "Bytes_icmp": None,
            "Bytes_other": None,
            "First": None,
            "Last": None,
            "msec_first": None,
            "msec_last": None,
            "Sequence_failures": None,
        }

        for line in result.split("\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip().replace(" ", "_")
                value = value.strip()
                try:
                    # Convert numeric fields
                    if key in {"First", "Last"}:
                        # Convert Unix timestamp to datetime
                        data[key] = datetime.fromtimestamp(int(value))
                    elif key in {"Ident"}:
                        data[key] = value.replace("/var/log/netflow/", "")
                    elif value.isdigit():
                        data[key] = int(value)
                    else:
                        data[key] = value
                except ValueError:
                    data[key] = value

        log_to_file(f"Processing file: {file_path}")
        insert_data_to_db(connection, data)

    except Exception as e:
        log_to_file(f"Error processing file {file_path}: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        log_to_file("No files provided for processing.")
        sys.exit(1)

    connection = mysql.connector.connect(**DB_CONFIG)
    try:
        create_table_if_not_exists(connection)

        for file_path in sys.argv[1:]:
            if os.path.exists(file_path):
                process_file(file_path, connection)
            else:
                pass
    finally:
        connection.close()
        log_to_file("Database connection closed.")
