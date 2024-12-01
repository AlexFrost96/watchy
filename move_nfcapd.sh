#!/bin/bash
LOG_DIR="/var/log/netflow"

# Iterate through all subdirectories (e.g., 10.1.1.1, 10.1.1.3, 10.1.1.4)
for SUBDIR in "$LOG_DIR"/*/; do
    # Check if it is a directory
    if [[ -d "$SUBDIR" ]]; then
        echo "Processing directory: $SUBDIR"

        # Find all nfcapd.* files in this directory
        find "$SUBDIR" -maxdepth 1 -type f -name "nfcapd.*" | while read -r FILE; do
            # Extract the file's creation date from its name (format YYYYMMDD)
            FILE_DATE=$(echo "$FILE" | grep -oP '\d{8}')

            # Check if a valid date was found
            if [[ -n "$FILE_DATE" ]]; then
                # Format FILE_DATE as YYYY/MM/DD
                FILE_DIR=$(date -d "$FILE_DATE" '+%Y/%m/%d')

                # Check if the file contains NetFlow data
                if nfdump -r "$FILE" | grep "No matching flows"; then
                    # If the file is older than 10 minutes, delete it
                    if [[ $(find "$FILE" -mmin +10 -print) ]]; then
                        echo "File $FILE is older than 10 minutes and contains no flows. Deleting..."
                        rm -f "$FILE"
                    else
                        echo "File $FILE contains no flows but is not older than 10 minutes. Skipping..."
                    fi
                else
                    # Move the file if it contains traffic flows
                    mkdir -p "$SUBDIR/$FILE_DIR"
                    mv "$FILE" "$SUBDIR/$FILE_DIR/"
                    echo "File $FILE has been moved to $SUBDIR/$FILE_DIR/"
                fi
            else
                echo "Could not evaluate a date for file $FILE. Checking if it can be deleted..."
                # Check if the file is older than 10 minutes
                if [[ $(find "$FILE" -mmin +10 -print) ]]; then
                    echo "File $FILE is older than 10 minutes and contains no flows. Deleting..."
                    rm -f "$FILE"
                else
                    echo "File $FILE contains no flows but is not older than 10 minutes. Skipping..."
                fi
            fi
        done
    fi
done