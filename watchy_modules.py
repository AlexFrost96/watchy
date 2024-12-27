#!/usr/bin/env python3
import geoip2.database
import ipaddress
import csv
import subprocess
import argparse
import mysql.connector
import pandas as pd

# Location of MaxMind DB
GEO_DB_PATH_COUNTRY = "GeoLite2-Country.mmdb"
GEO_DB_PATH_ASN = "GeoLite2-ASN.mmdb"
NETFLOW_BASE_DIR = "/var/log/netflow/"
# Home Network
HOME_NETWORK = ipaddress.IPv4Network("192.168.50.0/24")
# Parsing arguments
parser = argparse.ArgumentParser(description="Parsing arguments for nfdump")
parser.add_argument("--top", type=int, default=100,
                    help="Show top N conversation (default: 10)")
parser.add_argument("--filter", type=str, default=None,
                    help="Filter nfdump (default: all packets)")
parser.add_argument("--time", type=str, default=None,
                    help="Time interval for nfdump (Default: traffic for ALL time)")
parser.add_argument("--routers", type=str, default=None,
                    help="Routers - where we should parsing traffic (Default: all routers)")
parser.add_argument("--format", type=str, default=None,
                    help="Format for output (Default: csv)")
args = parser.parse_args()


DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "watchy",
    "password": "zudzar-xacvav-cyshyp-0azvyl-luqcyf-wimFol",
    "database": "watchy_db"
}


def fetch_data_from_db(router_ips, start_time, end_time):
    """
    Fetch data from the database for the given router IPs and time range.
    """
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    placeholders = ', '.join(['%s'] * len(router_ips))
    query = f"""
        SELECT Timestamp, Ident, Bytes
        FROM netflow
        WHERE Ident IN ({placeholders})
          AND Timestamp BETWEEN %s AND %s
        ORDER BY Timestamp ASC
    """
    print("Query:", query)
    params = router_ips + [start_time, end_time]
    cursor.execute(query, params)
    data = cursor.fetchall()

    cursor.close()
    connection.close()
    return data


def determine_scale(df, start_time, end_time, value_column="Bytes", timestamp_column="Timestamp"):
    """
    Determines the scale and unit for the given data based on the maximum value in the selected time range.

    Parameters:
        df (pd.DataFrame): Input DataFrame.
        start_time (str): Start time (format 'YYYY-MM-DD HH:MM:SS').
        end_time (str): End time (format 'YYYY-MM-DD HH:MM:SS').
        value_column (str): Name of the column containing the values.
        timestamp_column (str): Name of the column containing the timestamps.

    Returns:
        scale (int): Scale.
        unit (str): (B, KB, MB, GB, TB).
    """
    # Convert start and end times to datetime objects
    start_time_dt = pd.to_datetime(start_time)
    end_time_dt = pd.to_datetime(end_time)

    #
    filtered_df = df[(df[timestamp_column] >= start_time_dt)
                     & (df[timestamp_column] <= end_time_dt)]

    if filtered_df.empty:
        raise ValueError("No data available for the selected time range.")

    # Find the maximum value in the selected range
    max_value = filtered_df[value_column].max()
    print("Max value in the selected range:", max_value)

    # Determine the appropriate scale and unit
    if max_value < 1000:
        scale = 1  # Bytes
        unit = "B"
    elif max_value < 1000000:
        scale = 1000  # KiloBytes
        unit = "KB"
    elif max_value < 1000000000:
        scale = 1000000  # MegaBytes
        unit = "MB"
    elif max_value < 1000000000000:
        scale = 1000000000  # GigaBytes
        unit = "GB"
    else:
        scale = 1000000000000  # TeraBytes
        unit = "TB"

    return scale, unit


def determine_aggregation_interval(start_time, end_time):
    """
    Determine the aggregation interval based on the total duration between start_time and end_time.

    Args:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'.
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'.

    Returns:
        str: Aggregation interval for resampling (e.g., '5T', '30T', '1H').
    """
    start_time_dt = pd.to_datetime(start_time)
    end_time_dt = pd.to_datetime(end_time)
    total_duration = (end_time_dt - start_time_dt).total_seconds()

    if total_duration <= 3600:  # Up to 1 hour
        return '5T'  # 5 minutes
    elif total_duration <= 86400:  # Up to 24 hours
        return '15T'  # 15 minutes
    elif total_duration <= 172800:  # Up to 48 hours
        return '30T'  # 30 min
    else:  # Greater than 24 hours
        return '1H'  # 1 hours

def generate_combined_graph(router_ips, start_time=None, end_time=None):
    """
    Generate combined graph data for the selected routers and time range.

    Args:
        router_ips (list): List of router identifiers (e.g., IPs).
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'.
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'.

    Returns:
        list: Combined graph data for frontend.
        str: Unit for Y-axis (e.g., B, KB, MB).
    """
    if not start_time or not end_time:
        raise ValueError("start_time and end_time are required for analysis!")

    data = fetch_data_from_db(router_ips, start_time, end_time)  # Fetch data
    if not data:
        print("No data available for the selected range and routers.")
        return [], "B"

    df = pd.DataFrame(data)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    interval = determine_aggregation_interval(
        start_time, end_time)  # Get aggregation interval
    df.set_index("Timestamp", inplace=True)
    aggregated_data = []

    for router_name in router_ips:
        router_data = df[df["Ident"] == router_name]
        if router_data.empty:
            continue

        aggregated_router_data = router_data["Bytes"].resample(
            interval).sum().reset_index()
        aggregated_router_data["Bytes"] = aggregated_router_data["Bytes"].fillna(
            0)

        graph_data = {
            "name": router_name,
            "data": [{"x": ts.isoformat(), "y": bytes_val} for ts, bytes_val in zip(aggregated_router_data["Timestamp"], aggregated_router_data["Bytes"])]
        }
        aggregated_data.append(graph_data)

    scale, unit = determine_scale(
        df.reset_index(), start_time, end_time)  # Determine scale
    for entry in aggregated_data:
        for point in entry["data"]:
            point["y"] = round(point["y"] / scale, 2)

    return aggregated_data, unit


def format_duration(raw_duration):
    """
    Converts a raw duration (in seconds) into a human-readable D HH:MM:SS format.

    Args:
        raw_duration (float): Duration in seconds.

    Returns:
        str: Formatted duration as D HH:MM:SS if it includes days, or HH:MM:SS otherwise.
    """
    # Convert raw_duration (float) to total seconds
    total_seconds = int(raw_duration)  # Round to nearest second
    # Get days (86400 seconds in a day)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)  # Get hours
    minutes, seconds = divmod(remainder, 60)  # Get minutes and seconds

    # Include days only if there are any
    if days > 0:
        return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{hours:02}:{minutes:02}:{seconds:02}"


def process_traffic(csv_file_path="data.csv", output_csv_path="updated_data.csv"):
    # Step 1: Parse the data
    ip_pairs_traffic, time_data, duration_data = parse_ips_and_traffic(
        csv_file_path)

    if not ip_pairs_traffic:
        print("No traffic found or no matches in the data.")
        return False  # Return False if no data found

    # Step 2: Get GEO and ASN
    geo_and_asn = get_geo_and_asn(ip_pairs_traffic)

    # Step 3: Sort traffic
    # sorted_geo_and_asn = sorted(geo_and_asn.items(), key=lambda x: x[1]['bytes'], reverse=True)

    # # Step 4: Prepare the table for output
    headers = ["First time seen", "Duration", "Src IP", "src_ASN", "src_ASN Desc", "src_Country",
               "Dst IP", "dst_ASN", "dst_ASN Desc", "dst_Country",
               "MBytes", "Packets"]

    # Step 6: Save updated data to a new CSV
    with open(output_csv_path, "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows([
            [
                time_data[idx],
                duration_data[idx],
                src_ip,
                locations['src_asn'],
                locations['src_asn_desc'],
                locations['src_country'],
                dst_ip,
                locations['dst_asn'],
                locations['dst_asn_desc'],
                locations['dst_country'],
                f"{locations['bytes'] / 1000000:.2f} MB",
                locations['packets']
            ]
            for idx, ((src_ip, dst_ip), locations) in enumerate(geo_and_asn.items())
        ])

    print(f"Updated CSV saved to: {output_csv_path}")
    return True  # Indicate success


def execute_nfdump(top=None, time=None, routers=None, filter_param=None, output_format=None):
    # Construct the nfdump command
    cmd = "nfdump {} -s record/bytes -n {}"
    routers_dir = ""
    if routers:
        if len(routers.split(',')) > 1:
            last_ip = routers.split(',')[-1]
            for ip in routers.split(','):
                if not routers_dir:
                    routers_dir = routers_dir + f"-M {NETFLOW_BASE_DIR}{ip}"
                elif ip == last_ip:
                    routers_dir = routers_dir + f":{NETFLOW_BASE_DIR}{ip} -R ."
                else:
                    routers_dir = routers_dir + f":{NETFLOW_BASE_DIR}{ip}"
        else:
            routers_dir = f"-R {NETFLOW_BASE_DIR}{routers}"
        cmd = cmd.format(routers_dir, top)
    else:
        cmd = cmd.format(f"-R {NETFLOW_BASE_DIR}", top)
    if time:
        cmd += f" -t {time}"
    if filter_param:
        cmd += f" '{filter_param}'"
    if output_format == "e":  # Extended format
        cmd += " -o extended"
    else:  # Default to CSV format with aggregation
        cmd += " -A srcip,dstip -o csv"
        if output_format != "e":  # Output to CSV file only if not 'extended'
            cmd += " > data.csv"

    print(f"Executing command: {cmd}")
    try:
        # Execute the command and capture output
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout if output_format == "e" else "Output saved to data.csv"
        print(output)
        return output, cmd
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr}")
        return f"Error: {e.stderr}", cmd

# Function for parsing IP addresses and traffic flow from CSV


def parse_ips_and_traffic(csv_file):
    ips_traffic = []
    time_data = []
    duration_data = []
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                first_seen = row["firstSeen"]
                duration = float(row["duration"])
                src_ip = row["srcAddr"]
                dst_ip = row["dstAddr"]
                packets = int(row["packets"])
                bytes = int(row["bytes"])
                ips_traffic.append((src_ip, dst_ip, packets, bytes))
                time_data.append(first_seen)
                duration_data.append(format_duration(
                    duration))  # Append raw duration
            except KeyError as e:
                print(f"Missing column in CSV: {e}")
            except ValueError as e:
                print(f"Invalid data format: {e}")
    return ips_traffic, time_data, duration_data

# Function for identification of IP geolocation and ASN


def get_geo_and_asn(ips_traffic):
    geo_dict = {}
    with geoip2.database.Reader(GEO_DB_PATH_COUNTRY) as country_reader, \
            geoip2.database.Reader(GEO_DB_PATH_ASN) as asn_reader:

        for src_ip, dst_ip, packets, bytes in ips_traffic:
            src_country = "Unknown"
            dst_country = "Unknown"
            src_asn = "Unknown"
            dst_asn = "Unknown"
            src_asn_desc = "Unknown"
            dst_asn_desc = "Unknown"

            # Checking we are not in local networks
            if ipaddress.IPv4Address(src_ip) in HOME_NETWORK:
                src_country = "Home"
            if ipaddress.IPv4Address(dst_ip) in HOME_NETWORK:
                dst_country = "Home"

            # Parsing geo and ASN for src_ip
            try:
                src_response = country_reader.country(src_ip)
                src_country = f"{src_response.country.iso_code}, {src_response.country.name or 'Unknown'}"
                src_asn_response = asn_reader.asn(src_ip)
                src_asn = src_asn_response.autonomous_system_number
                src_asn_desc = src_asn_response.autonomous_system_organization or "Unknown"
            except geoip2.errors.AddressNotFoundError:
                pass
            except Exception as e:
                print(f"Error processing {src_ip}: {e}")

           # Parsing geo and ASN for dst_ip
            try:
                dst_response = country_reader.country(dst_ip)
                dst_country = f"{dst_response.country.iso_code}, {dst_response.country.name or 'Unknown'}"
                dst_asn_response = asn_reader.asn(dst_ip)
                dst_asn = dst_asn_response.autonomous_system_number
                dst_asn_desc = dst_asn_response.autonomous_system_organization or "Unknown"
            except geoip2.errors.AddressNotFoundError:
                pass
            except Exception as e:
                print(f"Error processing {dst_ip}: {e}")

            geo_dict[(src_ip, dst_ip)] = {
                "src_country": src_country,
                "dst_country": dst_country,
                "src_asn": src_asn,
                "src_asn_desc": src_asn_desc,
                "dst_asn": dst_asn,
                "dst_asn_desc": dst_asn_desc,
                "packets": packets,
                "bytes": bytes
            }

    return geo_dict


if __name__ == "__main__":
    # Call the nfdump function with parsed arguments
    execute_nfdump(args.top, args.time, args.routers, args.filter, args.format)
    # Main CSV location
    process_traffic()
