#!/bin/bash

# Define the base directory
BASE_DIR=$(pwd)

# Install required Python packages
pip3 install -r requirements.txt

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/watchy.service"

echo "[Unit]
Description=Flask Web Application
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$BASE_DIR
ExecStart=$(which python3) $BASE_DIR/web_analyse.py

[Install]
WantedBy=multi-user.target" | sudo tee $SERVICE_FILE

# Reload systemd to apply the new service
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable watchy.service
sudo systemctl start watchy.service

# Create cron file
CRON_FILE="/etc/cron.d/watchy"

echo "*/1 * * * * $(whoami) BASE_DIR=$BASE_DIR $BASE_DIR/move_nfcapd.sh >> $BASE_DIR/moving_nfcapd.log 2>&1" | sudo tee $CRON_FILE

# Set the correct permissions for the cron file
sudo chmod 644 $CRON_FILE

echo "Installation complete. The WATCHY service has been started and the cron job has been set up."