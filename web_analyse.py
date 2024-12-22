from flask import Flask, request, render_template, session
import os
import pandas as pd
from datetime import datetime, timedelta
from analyse_traffic import execute_nfdump, process_traffic
from flask import send_file

app = Flask(__name__)
app.secret_key = "HTi!-7c5CPr2P>(D#>£j'EW<YWyICX"

BASE_DIR = "/var/log/netflow/"
OUTPUT_DIR = "./output_csv"


def determine_scale(df, start_time, end_time, value_column="Bytes", timestamp_column="Timestamp"):
    """
    Визначає масштаб для всіх значень у колонці за певний часовий проміжок.
    
    Parameters:
        df (pd.DataFrame): Вхідний DataFrame.
        start_time (str): Початковий час (формат 'YYYY-MM-DD HH:MM:SS').
        end_time (str): Кінцевий час (формат 'YYYY-MM-DD HH:MM:SS').
        value_column (str): Назва колонки з байтами.
        timestamp_column (str): Назва колонки з часовими мітками.

    Returns:
        scale (int): Масштаб.
        unit (str): Одиниця виміру (B, KB, MB, GB, TB).
    """
    # Конвертуємо часові мітки у формат datetime
    start_time_dt = pd.to_datetime(start_time)
    end_time_dt = pd.to_datetime(end_time)
    
    # Фільтруємо дані за часовим проміжком
    filtered_df = df[(df[timestamp_column] >= start_time_dt) & (df[timestamp_column] <= end_time_dt)]

    if filtered_df.empty:
        raise ValueError("No data available for the selected time range.")

    # Знаходимо максимальне значення у вибраному діапазоні
    max_value = filtered_df[value_column].max()
    print("Max value in the selected range:", max_value)

    # Визначаємо масштаб і одиницю
    if max_value < 1000:
        scale = 1  # Байти
        unit = "B"
    elif max_value < 1000000:
        scale = 1000  # Кілобайти
        unit = "KB"
    elif max_value < 1000000000:
        scale = 1000000  # Мегабайти
        unit = "MB"
    elif max_value < 1000000000000:
        scale = 1000000000  # Гігабайти
        unit = "GB"
    else:
        scale = 1000000000000  # Терабайти
        unit = "TB"

    return scale, unit
    
def generate_combined_graph(router_ips, start_time=None, end_time=None):
    combined_data = []

    for router_name in router_ips:
        csv_file = os.path.join(OUTPUT_DIR, f"{router_name}_netflow.csv")
        if not os.path.exists(csv_file):
            print(f"CSV file for router {router_name} not found.")
            continue

        df = pd.read_csv(csv_file)
        # Перевірка на наявність необхідних колонок
        if "Timestamp" not in df.columns or "Bytes" not in df.columns:
            print(f"Missing required columns in {csv_file}")
            continue

        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce') 


        # Видаляємо рядки з NaN
        df.dropna(subset=["Timestamp", "Bytes"], inplace=True)

        # Фільтруємо дані за часовим діапазоном
        if start_time:
            start_time_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        else:
            raise ValueError("start_time is required for analysis!")
        if end_time:
            end_time_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        else:
            end_time_dt = datetime.now()

        df = df[(df["Timestamp"] >= start_time_dt) & (df["Timestamp"] <= end_time_dt)]

        if df.empty:
            print(f"No data for router {router_name} in the selected range.")
            continue
        
        scale, _ = determine_scale(df, start_time, end_time)
        print(scale)
        df["Bytes"] = (df["Bytes"] / scale).round(2)
        router_data = {
            "name": router_name,
            "data": [{"x": timestamp.isoformat(), "y": bytes_val} for timestamp, bytes_val in zip(df["Timestamp"], df["Bytes"])]
        }
        combined_data.append(router_data)

    return combined_data


@app.route('/')
def home():
    twelve_hours_ago = (datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    devices = []

    # Завантажуємо пристрої з devices.txt
    with open("devices.txt", "r") as f:
        for line in f:
            ip, _ = line.strip().split(",")
            devices.append(ip)

    # Генеруємо дані для графіку
    graph_data = generate_combined_graph(devices, twelve_hours_ago, now)

    return render_template('index.html', start_time=twelve_hours_ago, end_time=now, devices=devices, graph_data=graph_data)
    
@app.route('/update', methods=['POST'])
def update_graph():
    start_time = request.form.get('start_time', request.form.get('hidden_start_time', ''))
    end_time = request.form.get('end_time', request.form.get('hidden_end_time', ''))
    router_ips = request.form.getlist('router_ip')

    if not router_ips:
        with open("devices.txt", "r") as f:
            router_ips = [line.strip().split(",")[0] for line in f]

    graph_data = generate_combined_graph(router_ips, start_time, end_time)

    # Логування даних
    print("Graph data:", graph_data)

    return render_template(
        'index.html',
        start_time=start_time,
        end_time=end_time,
        devices=router_ips,
        graph_data=graph_data
    )


@app.route('/download')
def download_file():
    file_path = 'updated_data.csv'
    return send_file(file_path, as_attachment=True)


@app.route('/run', methods=['POST'])
def run_script():
    start_time = request.form.get('start_time', request.form.get('hidden_start_time', ''))
    end_time = request.form.get('end_time', request.form.get('hidden_end_time', ''))
    if start_time:
        start_time_obj = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        start_time = start_time_obj.strftime('%Y/%m/%d.%H:%M:%S')
    if end_time:
        end_time_obj = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        end_time = end_time_obj.strftime('%Y/%m/%d.%H:%M:%S')
    top = request.form.get('top', '')
    if not top.strip():
        top = 100
    else:
        top = int(top)
    filter_param = request.form.get('filter', '')
    output_format = request.form.get('format', '')
    router_ips = ','.join(request.form.getlist('router_ip'))

    if start_time and end_time:
        time = f'{start_time}-{end_time}'
    elif start_time:
        time = start_time
    try:
        output_csv_path = "updated_data.csv"
        output, cmd = execute_nfdump(top, time, router_ips, filter_param, output_format)
        if process_traffic():
            if output_format == "csv" and os.path.exists(output_csv_path):
                df = pd.read_csv(output_csv_path)
                html_table = df.to_html(classes="table table-hover", border=0, index=False)
            else:
                html_table = f"<pre>{output}</pre>"
        else:
            html_table = "<p>No traffic data found for the specified range.</p>"

    except Exception as e:
        print(f"Command failed: {e}")
        html_table = f"<pre>Error executing command: {e}</pre>"

    return render_template('output.html', table=html_table, command=cmd)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)