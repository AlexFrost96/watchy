# watchy-tool

## Overview
The WATCHY tool is a web-based application designed to replace the functionality of NFSen for analyzing NetFlow data. This tool provides a user-friendly interface for visualizing network traffic and managing NetFlow data files.

## Features
- **Dynamic Data Visualization**: Utilizes JavaScript for interactive graphs and charts.
- **NetFlow Data Management**: Scripts to process and organize NetFlow data files.
- **Web Interface**: Built with Flask, allowing users to submit queries and view results in a browser.
- **Data Download**: Options to download processed data in CSV format.

## Project Structure
```
watchy-tool
├── static
│   └── assets
│       └── script.js          # JavaScript for frontend interactions
├── templates
│   ├── index.html             # Main HTML template for user input
│   └── output.html            # Template for displaying command output
├── move_nfcapd.sh             # Script to process and move NetFlow files
├── delete_empty_flows.sh      # Script to delete empty NetFlow files
├── run_nfcapd.sh              # Script to start nfcapd for devices
├── watchy_modules.py          # Python module for data processing and graph generation
├── web_analyse.py             # Main Flask application file
└── README.md                  # Project documentation
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd watchy-tool
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Ensure you have the necessary permissions to run the shell scripts.

## Usage
1. Start the Flask application:
   ```
   python web_analyse.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`.

3. Use the form on the main page to input your desired parameters for analyzing NetFlow data.

4. View the results on the output page, where you can also download the processed data.

## Scripts
- **move_nfcapd.sh**: Organizes NetFlow files into directories based on their creation date and generates database entries.
- **delete_empty_flows.sh**: Cleans up empty NetFlow files to maintain a tidy log directory.
- **run_nfcapd.sh**: Initializes the nfcapd process for each device listed in `devices.txt`.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.