#!/bin/bash
LOG_DIR="/var/log/netflow"

# Проходимо по всіх підпапках (наприклад, 10.1.1.1, 10.1.1.3, 10.1.1.4)
for SUBDIR in "$LOG_DIR"/*/; do
    # Перевіряємо, чи це дійсно директорія
    if [[ -d "$SUBDIR" ]]; then
        echo "Processing directory: $SUBDIR"

        # Проходимо по всіх файлах nfcapd.* у цій директорії
        find "$SUBDIR" -maxdepth 1 -type f -name "nfcapd.*" | while read -r FILE; do
            # Витягуємо дату створення файлу з назви (формат YYYYMMDD)
            FILE_DATE=$(echo "$FILE" | grep -oP '\d{8}')

            # Перевіряємо, чи вдалося знайти дату
            if [[ -n "$FILE_DATE" ]]; then
                # Форматуємо FILE_DATE у вигляді YYYY/MM/DD
                FILE_DIR=$(date -d "$FILE_DATE" '+%Y/%m/%d')

                # Створюємо папку, якщо її ще немає
                mkdir -p "$SUBDIR/$FILE_DIR"

                # Переміщуємо файл у відповідну папку
                mv "$FILE" "$SUBDIR/$FILE_DIR/"
                echo "File $FILE has been moved to $SUBDIR/$FILE_DIR/"
            else
                echo "Could not evaluate a date for file $FILE. Skipping..."
            fi
        done
    fi
done