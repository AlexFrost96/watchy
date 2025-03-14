#!/usr/bin/env python3
from flask import Flask, request, render_template, session
import os
import pandas as pd
from datetime import datetime, timedelta
from watchy_modules import execute_nfdump, process_traffic, fetch_data_from_db, determine_aggregation_interval, determine_scale, generate_combined_graph
from flask import send_file


app = Flask(__name__)
app.secret_key = "HTi!-7c5CPr2P>(D#>£j'EW<YWyICX"


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0


def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


@app.route('/')
def home():
    twelve_hours_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    devices = []
    with open("config.txt", "r") as f:
       devices = [line.strip().split(",")[0] for line in f if '=' not in line and line.strip()]
    graph_data, scale_unit = generate_combined_graph(
        devices, twelve_hours_ago, now)
    return render_template('index.html', start_time=twelve_hours_ago, end_time=now, devices=devices, graph_data=graph_data, yaxis_unit=scale_unit, current_page='home')


@app.route('/devices')
def devices():
    devices = []
    base_dir = "/var/log/netflow/"
    with open("config.txt", "r") as f:
        for line in f:
            if '=' in line or not line:
                continue
            ip, port = line.strip().split(",")
            device_dir = os.path.join(base_dir, ip)
            if os.path.exists(device_dir):
                memory_usage = get_directory_size(device_dir)
                memory_usage = human_readable_size(memory_usage)
            else:
                memory_usage = "0 B"
            devices.append({"ip": ip, "port": port, "memory_usage": memory_usage})
    return render_template('devices.html', devices=devices, current_page='devices')


@app.route('/config')
def config():
    list_config = []
    with open("config.txt", "r") as f:
        #list_config = [line.strip().replace('=', ': ') for line in f if '=' in line and line.strip()]
        for line in f:
            if '=' in line:
                config_name, value = line.strip().split("=")
                list_config.append({"config_name": config_name, "value": value})
    return render_template('config.html', list_config=list_config, current_page='config')


@app.route('/update', methods=['POST'])
def update_graph():
    start_time = request.form.get(
        'start_time', request.form.get('hidden_start_time', ''))
    end_time = request.form.get(
        'end_time', request.form.get('hidden_end_time', ''))
    router_ips = request.form.getlist('router_ip')

    if not router_ips:
        with open("config.txt", "r") as f:
            router_ips = [line.strip().split(",")[0] for line in f if '=' not in line and line.strip()]

    data = fetch_data_from_db(router_ips, start_time, end_time)  # Fetch data

    if not data:
        print("No data available for the selected range and routers.")
        return render_template('index.html', start_time=start_time, end_time=end_time, devices=router_ips, graph_data=[], yaxis_unit="B")

    df = pd.DataFrame(data)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    interval = determine_aggregation_interval(
        start_time, end_time)  # Get aggregation interval
    df.set_index("Timestamp", inplace=True)

    graph_data = []
    for router in router_ips:
        router_data = df[df["Ident"] == router]
        aggregated_router_data = router_data["Bytes"].resample(
            interval).sum().reset_index()
        aggregated_router_data["Bytes"] = (
            aggregated_router_data["Bytes"] / determine_scale(df.reset_index(), start_time, end_time)[0]).round(2)

        router_graph_data = {
            "name": router,
            "data": [{"x": ts.isoformat(), "y": bytes_val} for ts, bytes_val in zip(aggregated_router_data["Timestamp"], aggregated_router_data["Bytes"])]
        }
        graph_data.append(router_graph_data)

    return render_template('index.html', start_time=start_time, end_time=end_time, devices=router_ips, graph_data=graph_data, yaxis_unit=determine_scale(df.reset_index(), start_time, end_time)[1])


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
        start_time_nf = start_time_obj.strftime('%Y/%m/%d.%H:%M:%S')
    if end_time:
        end_time_obj = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        end_time_nf = end_time_obj.strftime('%Y/%m/%d.%H:%M:%S')
    top = request.form.get('top', '')
    if not top.strip():
        top = 100
    else:
        top = int(top)
    filter_param = request.form.get('filter', '')
    output_format = request.form.get('format', '')
    router_ips = ','.join(request.form.getlist('router_ip'))
    cmd = ""  # Initialize cmd to ensure it always exists
    try:
        output_csv_path = "updated_data.csv"
        output, cmd = execute_nfdump(top, start_time_nf, end_time_nf, router_ips, filter_param, output_format)
        print(output)
        if process_traffic():
            if output_format == "csv" and os.path.exists(output_csv_path):
                df = pd.read_csv(output_csv_path)
                html_table = df.to_html(
                    classes="table table-hover", border=0, index=False)
            else:
                html_table = f"<pre>{output}</pre>"
        else:
            html_table = "<p>No traffic data found for the specified range.</p>"

    except Exception as e:
        print(f"Command failed: {e}")
        html_table = f"<pre>Error executing command: {e}</pre>"

    return render_template('output.html', table=html_table, command=cmd, start_time=start_time, end_time=end_time, current_page='output')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
