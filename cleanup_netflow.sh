#!/bin/bash

CONFIG_FILE="config.txt"
LOG_DIR="/var/log/netflow"
RESERVED_MEMORY=0
LOG_FILE="cleanup.log"

# Function to convert memory size (e.g., 24G) to bytes
convert_to_bytes() {
    local size=$(echo "$1" | tr -d '[:space:]')  # Remove spaces
    local unit=${size: -1}
    local value=${size%?}
    case $unit in
        K|k) echo $((value * 1024)) ;;
        M|m) echo $((value * 1024 * 1024)) ;;
        G|g) echo $((value * 1024 * 1024 * 1024)) ;;
        T|t) echo $((value * 1024 * 1024 * 1024 * 1024)) ;;
        *) echo $value ;;  # Default case (assume bytes)
    esac
}

# Read configuration file
while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(echo "$line" | tr -d '[:space:]')  # Remove spaces
    if [[ "$line" =~ ^reserved_memory= ]]; then
        RESERVED_MEMORY=$(convert_to_bytes "${line#*=}" | tail -n 1)
    fi
done < "$CONFIG_FILE"

echo "Final Reserved Memory: $RESERVED_MEMORY bytes"

# Calculate total size of log directory
total_size=$(du -sb "$LOG_DIR" | awk '{print $1}')
echo "Total size: $total_size bytes"

# Function to delete old log files if total size exceeds reserved memory
cleanup_files() {
    local freed_space=0
    local start_size=$total_size  # Store initial size
    
    while [ "$total_size" -gt "$RESERVED_MEMORY" ]; do
        # Find oldest log files and sort them by modification date
        files_to_delete=$(find "$LOG_DIR" -type f -name 'nfcapd.*' -printf '%T+ %p\n' | sort | awk '{print $2}')
        
        for file in $files_to_delete; do
            file_size=$(stat -c%s "$file")
            echo "$(date "+%Y-%m-%d %H:%M:%S") - Deleting $file ($file_size bytes)" | tee -a "$LOG_FILE"
            rm -f "$file"
            total_size=$((total_size - file_size))
            freed_space=$((freed_space + file_size))

            # Stop deleting if we reach the reserved memory limit
            if [ "$total_size" -le "$RESERVED_MEMORY" ]; then
                break
            fi
        done
    done

    echo "$(date "+%Y-%m-%d %H:%M:%S") - Cleanup completed. Freed: $freed_space bytes. Total size after cleanup: $total_size bytes." | tee -a "$LOG_FILE"
}

# Start cleanup if necessary
if [ "$total_size" -gt "$RESERVED_MEMORY" ]; then
    echo "$(date "+%Y-%m-%d %H:%M:%S") - Starting cleanup..." | tee -a "$LOG_FILE"
    cleanup_files
else
    echo "$(date "+%Y-%m-%d %H:%M:%S") - No cleanup needed." | tee -a "$LOG_FILE"
fi