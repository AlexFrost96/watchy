#!/usr/bin/env python3
import geoip2.database
import ipaddress
import csv
from tabulate import tabulate
import textwrap
import os
import argparse

# Шляхи до MaxMind баз даних
GEO_DB_PATH_COUNTRY = "GeoLite2-Country.mmdb"
GEO_DB_PATH_ASN = "GeoLite2-ASN.mmdb"
# Мережа для "Home"
HOME_NETWORK = ipaddress.IPv4Network("192.168.50.0/24")
# Додаємо аргументи
parser = argparse.ArgumentParser(description="Parsing arguments for nfdump")
parser.add_argument("--top", type=int, default=100, help="Show top N conversation (default: 10)")
parser.add_argument("--filter", type=str, default=None, help="Filter nfdump (default: all packets)")
parser.add_argument("--time", type=str, default=None, help="Time interval for nfdump (Default: traffic for ALL time)")
parser.add_argument("--format", type=str, default=None, help="Format for output (Default: csv)")
args = parser.parse_args()
nfdump_top_N = args.top
nfdump_filter = args.filter
nfdump_time = args.time
nfdump_format = args.format
cmd = f"./get_nfdump.sh {nfdump_top_N}"
if nfdump_time:
    cmd += f" '{nfdump_time}'"
else:
    cmd += " false"
if nfdump_filter:
    cmd += f" '{nfdump_filter}'"
else:
    cmd += " false"
if nfdump_format:
    cmd += f" {nfdump_format}" 
else:
    cmd += " false"
print(f"Executing command: {cmd}")
os.system(cmd)

# Функція для парсингу IP-адрес та трафіку із CSV
def parse_ips_and_traffic(csv_file):
    ips_traffic = []
    time_data = []  # Для зберігання часу
    with open(csv_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                first_seen = row["firstSeen"]
                src_ip = row["srcAddr"]
                dst_ip = row["dstAddr"]
                packets = int(row["packets"])
                bytes_ = int(row["bytes"]) 
                ips_traffic.append((src_ip, dst_ip, packets, bytes_))
                time_data.append(first_seen)
            except KeyError as e:
                print(f"Missing column in CSV: {e}")
            except ValueError as e:
                print(f"Invalid data format: {e}")
    return ips_traffic, time_data

# Функція для визначення геолокації та ASN IP-адрес
def get_geo_and_asn(ips_traffic):
    geo_dict = {}
    with geoip2.database.Reader(GEO_DB_PATH_COUNTRY) as country_reader, \
         geoip2.database.Reader(GEO_DB_PATH_ASN) as asn_reader:

        for src_ip, dst_ip, packets, bytes_ in ips_traffic:
            src_country = "Unknown"
            dst_country = "Unknown"
            src_asn = "Unknown"
            dst_asn = "Unknown"
            src_asn_desc = "Unknown"
            dst_asn_desc = "Unknown"

            # Перевірка, чи IP в мережі 192.168.50.0/24
            if ipaddress.IPv4Address(src_ip) in HOME_NETWORK:
                src_country = "Home"
            if ipaddress.IPv4Address(dst_ip) in HOME_NETWORK:
                dst_country = "Home"

            # Геолокація та ASN для src_ip
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

            # Геолокація та ASN для dst_ip
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
                "bytes": bytes_  # Зберігаємо байти
            }

    return geo_dict

# Функція для обмеження ширини тексту з переносом на новий рядок
def wrap_text(text, width=12):
    return textwrap.fill(text, width=width)

# Основний блок
if __name__ == "__main__":
    # Шлях до CSV файлу
    CSV_FILE_PATH = "data.csv"

    # Парсимо IP-адреси та трафік, а також час
    ip_pairs_traffic, time_data = parse_ips_and_traffic(CSV_FILE_PATH)

    if not ip_pairs_traffic:
        print("No traffic found or no matches in the data.")

    # Визначаємо геолокації, ASN, пакети та байти
    geo_and_asn = get_geo_and_asn(ip_pairs_traffic)

    # Сортуємо по байтах у порядку спадання
    sorted_geo_and_asn = sorted(geo_and_asn.items(), key=lambda x: x[1]['bytes'], reverse=True)

    # Формуємо таблицю для виводу
    table_data = []
    for idx, ((src_ip, dst_ip), locations) in enumerate(sorted_geo_and_asn):
        # Перетворюємо біти в мегабіти для виведення
        mb_bytes = locations['bytes'] / 1_000_000  # Конвертація байтів в мегабайти
        table_data.append([
            wrap_text(src_ip, width=15),
            wrap_text(str(locations['src_asn']), width=7),
            wrap_text(locations['src_asn_desc'], width=12),
            wrap_text(locations['src_country'], width=12),
            wrap_text(dst_ip, width=15),
            wrap_text(str(locations['dst_asn']), width=7),
            wrap_text(locations['dst_asn_desc'], width=12),
            wrap_text(locations['dst_country'], width=12),
            f"{mb_bytes:.2f} MB",  # Виводимо мегабайти
            locations['packets'],
            time_data[idx]  # Додаємо час з time_data
        ])

    # Виведення таблиці
    headers = ["Src IP", "src_ASN", "src_ASN Desc", "src_Country", "Dst IP", "dst_ASN", "dst_ASN Desc", "dst_Country", "Mbits", "Packets", "Time"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Збереження в оновлений CSV файл
    with open("updated_data.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for idx, ((src_ip, dst_ip), locations) in enumerate(geo_and_asn.items()):
            writer.writerow([
                src_ip,
                locations['src_asn'],
                locations['src_asn_desc'],
                locations['src_country'],
                dst_ip,
                locations['dst_asn'],
                locations['dst_asn_desc'],
                locations['dst_country'],
                locations['bytes'],  # Зберігаємо байти
                locations['packets'],
                time_data[idx]  # Додаємо час
            ])

    print("Updated CSV saved to: updated_data.csv")