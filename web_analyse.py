from flask import Flask, request, render_template, session
import subprocess
import os
import pandas as pd
from datetime import datetime, timedelta
from flask import send_file
import plotly.graph_objects as go

app = Flask(__name__)
app.secret_key = "HTi!-7c5CPr2P>(D#>£j'EW<YWyICX"

BASE_DIR = "/var/log/netflow/"
OUTPUT_DIR = "./output_csv"

def generate_combined_graph(router_ips, start_time=None, end_time=None):
    combined_df = pd.DataFrame()

    for router_name in router_ips:
        csv_file = os.path.join(OUTPUT_DIR, f"{router_name}_netflow.csv")
        if not os.path.exists(csv_file):
            print(f"CSV file for router {router_name} not found.")
            continue

        df = pd.read_csv(csv_file)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        # Фільтруємо дані за часовим діапазоном
        if start_time:
            start_time_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        else:
            raise print("Error, start_time is required for analysis!")
        if end_time:
            end_time_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        else:
            end_time_dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        df = df[(df["Timestamp"] >= start_time_dt) & (df["Timestamp"] <= end_time_dt)]

        if df.empty:
            print(f"No data for router {router_name} in the selected range.")
            continue

        df["Router"] = router_name
        combined_df = pd.concat([combined_df, df])

    if combined_df.empty:
        return None

    # Створюємо комбінований стовпчастий графік
    fig = go.Figure()

    for router_name, router_data in combined_df.groupby("Router"):
        fig.add_trace(go.Bar(
            x=router_data["Timestamp"],
            y=router_data["Bytes"],
            name=router_name
        ))

    fig.update_layout(
        title="Combined Traffic Analysis",
        xaxis_title="Time",
        yaxis_title="Bytes",
        barmode="stack",
        height=600,
        legend_title="Routers",
        margin=dict(l=20, r=20, t=30, b=20)
    )

    return fig.to_html(full_html=False)


@app.route('/')
def home():
    #today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y/%m/%d.%H:%M:%S')
    twelve_hours_ago = (datetime.now() - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    devices = []

    # Завантажуємо пристрої з devices.txt
    with open("devices.txt", "r") as f:
        for line in f:
            ip, _ = line.strip().split(",")
            devices.append(ip)

            # Генеруємо графік для кожного пристрою
    graph = generate_combined_graph(devices,twelve_hours_ago,now)


    return render_template('index.html', start_time=twelve_hours_ago, end_time=now, devices=devices, graph=graph)

@app.route('/update', methods=['POST'])
def update_graph():
    start_time = request.form.get('start_time', request.form.get('hidden_start_time', ''))
    end_time = request.form.get('end_time', request.form.get('hidden_end_time', ''))
    router_ips = request.form.getlist('router_ip')

    if not router_ips:
        with open("devices.txt", "r") as f:
            router_ips = [line.strip().split(",")[0] for line in f]

    graph = generate_combined_graph(router_ips, start_time, end_time)
    return render_template('index.html', start_time=start_time, end_time=end_time, devices=router_ips, graph=graph)

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
    filter_param = request.form.get('filter', '')
    output_format = request.form.get('format', '')
    router_ips = ','.join(request.form.getlist('router_ip'))

    command = f'./analyse_traffic.py'
    if start_time and end_time:
        command += f' --time {start_time}-{end_time}'
    elif start_time:
        command += f' --time {start_time}'
    if top:
        command += f' --top {top}'
    if router_ips:
        command += f" --routers '{router_ips}'"
    if filter_param:
        command += f" --filter '{filter_param}'"
    if output_format:
        command += f' --format {output_format}'

    try:
        print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout

        if output_format == "csv":
            csv_path = 'updated_data.csv'
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                html_table = df.to_html(classes="table table-striped", index=False)
            else:
                html_table = "<p>Error: CSV file not found.</p>"
        else:
            html_table = f"<pre>{output}</pre>"

    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.stderr}")
        html_table = f"<pre>Error executing command: {e.stderr}</pre>"

    return render_template('output.html', table=html_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)