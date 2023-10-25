#!/bin/bash

# Change directory to the desired location
cd /Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated

TODAY=$(date "+%Y-%m-%d")
CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")

LOG_DIR="mac_automation/logs"
LOG_FILE="$LOG_DIR/daily_run_status.log"
CALLS_LOG_FILE="$LOG_DIR/script_calls.log"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

# Extract the last run date and status from the log
if [[ -f $LOG_FILE ]]; then
    LAST_LOG_ENTRY=$(tail -n 1 "$LOG_FILE")
    LAST_RUN_DATE=$(echo $LAST_LOG_ENTRY | cut -d ' ' -f 1)
    LAST_STATUS=$(echo $LAST_LOG_ENTRY | cut -d ' ' -f 2)

    echo "$CURRENT_TIME SCRIPT_STARTED" >> "$CALLS_LOG_FILE"

    # If the script was run today with a status of "SUCCESS" or "RUNNING", log and exit
    if [[ "$LAST_RUN_DATE" == "$TODAY" && ( "$LAST_STATUS" == "SUCCESS" || "$LAST_STATUS" == "RUNNING" ) ]]; then
        echo "$CURRENT_TIME SCRIPT_EXITED_EARLY with status $LAST_STATUS" >> "$CALLS_LOG_FILE"
        exit 0
    fi
else
    echo "$CURRENT_TIME SCRIPT_STARTED" >> "$CALLS_LOG_FILE"
fi

# Log the status as "RUNNING"
echo "$TODAY RUNNING" >> "$LOG_FILE"

osascript -e 'display notification "Sornette started" with title "Sornette Status"'
# Run the Python script
/Users/octaviantuchila/.pyenv/shims/python3 update_and_check_bubbles.py >> "$LOG_DIR/python_output.log" 2>&1
EXIT_CODE=$?

# Update the log with today's status based on the Python script's exit code
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "$TODAY SUCCESS" >> "$LOG_FILE"
        osascript -e 'display notification "Sornette finished successfully" with title "Sornette Status"'
else
    echo "$TODAY FAILED" >> "$LOG_FILE"
fi

echo "$CURRENT_TIME SCRIPT_FINISHED_WITH_CODE_$EXIT_CODE" >> "$CALLS_LOG_FILE"
