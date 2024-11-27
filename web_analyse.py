from flask import Flask, request, render_template
import subprocess
import os
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run_script():
    time = request.form.get('time', '')
    top = request.form.get('top', '')
    filter_param = request.form.get('filter', '')
    output_format = request.form.get('format', '')
    router_ip = request.form.get('router_ip', '')

    command = f'./analyse_traffic.py'
    if time:
        command += f' --time {time}'
    if top:
        command += f' --top {top}'
    if router_ip:
        command += f' --router {router_ip}'
    if filter_param:
        command += f" --filter '{filter_param}'"
    if output_format:
        command += f' --format {output_format}'


    try:
        print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout

        if output_format == "csv":
            csv_path = 'data.csv'
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