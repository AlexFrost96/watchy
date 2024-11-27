from flask import Flask, request, render_template_string
import subprocess

app = Flask(__name__)

@app.route('/')
def home():
    return '''
        <h1>Analyse Traffic</h1>
        <form action="/run" method="post">
            <label>Time:</label>
            <input type="text" name="time" value="2024/11/27.00:00:00"><br>
            <label>Top:</label>
            <input type="number" name="top" placeholder="e.g., 100"><br>
            <label>Filter:</label>
            <input type="text" name="filter" placeholder="e.g., srcip, dstip"><br>
            <label>Format:</label>
            <input type="text" name="format" placeholder="e.g., csv"><br>
            <button type="submit">Run</button>
        </form>
    '''

@app.route('/run', methods=['POST'])
def run_script():
    # Retrieve input values
    time = request.form.get('time', '')
    top = request.form.get('top', '')
    filter_param = request.form.get('filter', '')
    output_format = request.form.get('format', '')

    # Construct the command
    command = f'./analyse_traffic.py'
    if time:
        command += f' --time {time}'
    if top:
        command += f' --top {top}'
    if filter_param:
        command += f" --filter '{filter_param}'"
    if output_format:
        command += f' --format {output_format}'

    # Execute the command
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = f"Error executing command: {e.stderr}"

    # Render the result
    return render_template_string(f'''
        <a href="/">Return to Home</a>
        <h1>Command Output</h1>
        <pre>{output}</pre>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
