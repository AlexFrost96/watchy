from flask import Flask, request, render_template
import subprocess
import os
import pandas as pd
from datetime import datetime
from flask import send_file

app = Flask(__name__)

@app.route('/')
def home():
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y/%m/%d.%H:%M:%S')
    now = datetime.now().strftime('%Y/%m/%d.%H:%M:%S')
    devices = []
    with open("devices.txt", "r") as f:
        for line in f:
            ip, _ = line.strip().split(",")
            devices.append(ip)  # Extract only the IP address
    return render_template('index.html', start_date=today_midnight, end_time=now, devices=devices)

@app.route('/download')
def download_file():
    file_path = 'updated_data.csv'
    return send_file(file_path, as_attachment=True)

@app.route('/run', methods=['POST'])
def run_script():
    start_time = request.form.get('start_time', '')
    end_time = request.form.get('end_time', '')
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