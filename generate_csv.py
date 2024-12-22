import os
import csv
import pandas as pd
from datetime import datetime

BASE_DIR = "/var/log/netflow/"
OUTPUT_DIR = "./output_csv"  # Директорія для збереження CSV


def process_router_files(router_dir, router_name) -> None:
    """
    Processes NetFlow data files in a specified directory and generates a CSV file with summarized data.
    """
    csv_file = os.path.join(OUTPUT_DIR, f"{router_name}_netflow.csv")
    
    # Перебираємо файли nfcapd.*
    for root, _, files in os.walk(router_dir):
        for file in files:
            if file.startswith("nfcapd.") and not file.endswith(".current"):
                try:
                    file_path = os.path.join(root, file)
                    # Отримуємо timestamp із назви файлу
                    file_name = os.path.basename(file_path)
                    timestamp_str = file_name.split(".")[1]
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M")
                    
                    # Аналізуємо файл за допомогою nfdump
                    cmd = f"nfdump -r {file_path} -I"
                    result = os.popen(cmd).read()
                    data = {"Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")}
                    
                    for line in result.split("\n"):
                        if ": " in line:
                            parts = line.split(": ", 1)
                            if len(parts) == 2:
                                key, value = parts
                                if key == "Ident":
                                    value = value.replace('/var/log/netflow/', '')
                                else:
                                    pass
                                try:
                                    data[key.strip()] = int(value.strip())
                                except ValueError:
                                    data[key.strip()] = value.strip()
                    
                    # Якщо CSV не існує, створюємо файл із заголовками
                    if not os.path.exists(csv_file):
                        with open(csv_file, mode="w", newline="") as file:
                            writer = csv.writer(file)
                            writer.writerow(data.keys())
                    
                    # Додаємо рядок у CSV
                    with open(csv_file, mode="a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(data.values())
                
                except ValueError as ve:
                    print(f"Skipping invalid file: {file}. Reason: {ve}")
                except Exception as e:
                    print(f"Error processing file: {file}. Reason: {e}")


# Основний блок
if __name__ == "__main__":
    # Перевіряємо, чи існує вихідна директорія для CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Перебираємо всі піддиректорії (роутери)
    for router_name in os.listdir(BASE_DIR):
        router_dir = os.path.join(BASE_DIR, router_name)
        if os.path.isdir(router_dir):
            print(f"Processing router: {router_name}")
            process_router_files(router_dir, router_name)