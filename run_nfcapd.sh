#!/bin/bash

DEVICE_FILE="/home/morpheus/test/config.txt"
LOG_DIR="/var/log/netflow"

mkdir -p "$LOG_DIR"

# Get the list of currently running nfcapd processes
running_devices=$(ps aux | grep '[n]fcapd' | awk '{for(i=1;i<=NF;i++) if ($i ~ /-I/) print $(i+1)}')

# Read the devices from the DEVICE_FILE
declare -A devices
while IFS=',' read -r IP PORT; do
    # Skip commented lines
    [[ "$IP" =~ ^#.*$ ]] && continue
    devices["$IP"]=$PORT
done < "$DEVICE_FILE"

# Stop nfcapd for devices that are no longer listed in the DEVICE_FILE
for device in $running_devices; do
    device_ip=$(basename "$device")
    if [[ -z "${devices[$device_ip]}" ]]; then
        echo "Stopping nfcapd for $device_ip..."
        sudo pkill -f "nfcapd.*$device_ip"
    fi
done

# Start nfcapd for devices listed in the DEVICE_FILE
for IP in "${!devices[@]}"; do
    PORT=${devices[$IP]}
    IP_DIR="$LOG_DIR/$IP"
    if [ ! -d "$IP_DIR" ]; then
        mkdir -p "$IP_DIR"
        echo "Created directory: $IP_DIR"
    fi

    echo "Starting nfcapd for $IP:$PORT..."
    sudo nfcapd -D -p "$PORT" -w "$IP_DIR" -I "$IP_DIR"
done