#!/bin/bash

DEVICE_FILE="/home/morpheus/test/devices.txt"
LOG_DIR="/var/log/netflow"

mkdir -p "$LOG_DIR"

while IFS=',' read -r IP PORT; do
    # Створюємо підкаталог для кожного IP, якщо його немає
    IP_DIR="$LOG_DIR/$IP"
    if [ ! -d "$IP_DIR" ]; then
        mkdir -p "$IP_DIR"
        echo "Created directory: $IP_DIR"
    fi

    echo "Starting nfcapd for $IP:$PORT..."
    sudo nfcapd -D -p "$PORT" -w "$IP_DIR" -I "$IP_DIR"
done < "$DEVICE_FILE"