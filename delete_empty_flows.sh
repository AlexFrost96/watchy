#!/bin/bash
LOG_DIR="/var/log/netflow"
for SUBDIR in "$LOG_DIR"/*/; do
    # Check if it is a directory
    if [[ -d "$SUBDIR" ]]; then
        echo "Processing directory: $SUBDIR"
        # Find files with a depth of exactly 4
        find "$SUBDIR" -mindepth 4 -maxdepth 4 -type f -name "nfcapd.*" | while read -r FILE; do
            # echo "Processing file: $FILE"
            if nfdump -r "$FILE" | grep -q "No matching flows"; then
                echo "Empty flows in $FILE, removing it..."
                rm "$FILE"  # Delete the file if empty flows are detected
            fi
        done
    fi
done