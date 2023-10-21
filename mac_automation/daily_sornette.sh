#!/bin/bash

# Change directory to the desired location
cd /Users/octaviantuchila/Documents/MonteCarlo/Sornette/lppls_python_updated

TODAY=$(date "+%Y-%m-%d")

LOG_DIR="$HOME/.lppls_logs"
LOG_FILE="$LOG_DIR/run_status.log"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

# Extract the last run date and status from the log
if [[ -f $LOG_FILE ]]; then
    LAST_LOG_ENTRY=$(tail -n 1 "$LOG_FILE")
    LAST_RUN_DATE=$(echo $LAST_LOG_ENTRY | cut -d ' ' -f 1)
    LAST_STATUS=$(echo $LAST_LOG_ENTRY | cut -d ' ' -f 2)
    TODAY=$(date "+%Y-%m-%d")

    # If the script was run today with a status of "SUCCESS" or "RUNNING", exit
    if [[ "$LAST_RUN_DATE" == "$TODAY" && ( "$LAST_STATUS" == "SUCCESS" || "$LAST_STATUS" == "RUNNING" ) ]]; then
        exit 0
    fi
fi

# Log the status as "RUNNING"
echo "$TODAY RUNNING" >> "$LOG_FILE"

# Run the Python script
/Users/octaviantuchila/.pyenv/shims/python3 update_and_check_bubbles.py >> "$LOG_DIR/python_output.log" 2>&1
EXIT_CODE=$?

# Update the log with today's status based on the Python script's exit code
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "$TODAY SUCCESS" >> "$LOG_FILE"
else
    echo "$TODAY FAILED" >> "$LOG_FILE"
fi
