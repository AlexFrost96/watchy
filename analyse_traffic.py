#!/usr/bin/env python3
import geoip2.database
import ipaddress
import csv
from tabulate import tabulate
import textwrap
import subprocess
import argparse

# Location of MaxMind DB
GEO_DB_PATH_COUNTRY = "GeoLite2-Country.mmdb"
GEO_DB_PATH_ASN = "GeoLite2-ASN.mmdb"
NETFLOW_BASE_DIR = "/var/log/netflow/"
# Home Network
HOME_NETWORK = ipaddress.IPv4Network("192.168.50.0/24")
# Parsing arguments
parser = argparse.ArgumentParser(description="Parsing arguments for nfdump")
parser.add_argument("--top", type=int, default=100, help="Show top N conversation (default: 10)")
parser.add_argument("--filter", type=str, default=None, help="Filter nfdump (default: all packets)")
parser.add_argument("--time", type=str, default=None, help="Time interval for nfdump (Default: traffic for ALL time)")
parser.add_argument("--routers", type=str, default=None, help="Routers - where we should parsing traffic (Default: all routers)")
parser.add_argument("--format", type=str, default=None, help="Format for output (Default: csv)")
args = parser.parse_args()


def process_traffic(csv_file_path="data.csv", output_csv_path="updated_data.csv"):
    # Step 1: Parse the data
    ip_pairs_traffic, time_data = parse_ips_and_traffic(csv_file_path)

    if not ip_pairs_traffic:
        print("No traffic found or no matches in the data.")
        return False  # Return False if no data found

    # Step 2: Get GEO and ASN
    geo_and_asn = get_geo_and_asn(ip_pairs_traffic)

    # Step 3: Sort traffic
    sorted_geo_and_asn = sorted(geo_and_asn.items(), key=lambda x: x[1]['bytes'], reverse=True)

    # # Step 4: Prepare the table for output
    headers = ["Src IP", "src_ASN", "src_ASN Desc", "src_Country", 
               "Dst IP", "dst_ASN", "dst_ASN Desc", "dst_Country", 
               "MBytes", "Packets", "Time"]
    # table_data = []
    # for idx, ((src_ip, dst_ip), locations) in enumerate(sorted_geo_and_asn):
    #     mb_bytes = locations['bytes'] / 1_000_000  # Convert bytes to MB
    #     table_data.append([
    #         wrap_text(src_ip, width=15),
    #         wrap_text(str(locations['src_asn']), width=7),
    #         wrap_text(locations['src_asn_desc'], width=12),
    #         wrap_text(locations['src_country'], width=12),
    #         wrap_text(dst_ip, width=15),
    #         wrap_text(str(locations['dst_asn']), width=7),
    #         wrap_text(locations['dst_asn_desc'], width=12),
    #         wrap_text(locations['dst_country'], width=12),
    #         f"{mb_bytes:.2f} MB",
    #         locations['packets'],
    #         time_data[idx]
    #     ])

    # # Step 5: Print the table
    # print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Step 6: Save updated data to a new CSV
    with open(output_csv_path, "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows([
            [
                src_ip,
                locations['src_asn'],
                locations['src_asn_desc'],
                locations['src_country'],
                dst_ip,
                locations['dst_asn'],
                locations['dst_asn_desc'],
                locations['dst_country'],
                f"{locations['bytes'] / 1000000:.2f} MB",
                locations['packets'],
                time_data[idx]
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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
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
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                first_seen = row["firstSeen"]
                src_ip = row["srcAddr"]
                dst_ip = row["dstAddr"]
                packets = int(row["packets"])
                bytes = int(row["bytes"]) 
                ips_traffic.append((src_ip, dst_ip, packets, bytes))
                time_data.append(first_seen)
            except KeyError as e:
                print(f"Missing column in CSV: {e}")
            except ValueError as e:
                print(f"Invalid data format: {e}")
    return ips_traffic, time_data

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

# Функція для обмеження ширини тексту з переносом на новий рядок
def wrap_text(text, width=12):
    return textwrap.fill(text, width=width)


if __name__ == "__main__":
    # Call the nfdump function with parsed arguments
    execute_nfdump(args.top, args.time, args.routers, args.filter, args.format)
    # Main CSV location
    process_traffic()