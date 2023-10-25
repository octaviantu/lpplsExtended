import os
import subprocess
from datetime import datetime

# Set directories and file paths
working_directory = '/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated'
log_dir = 'mac_automation/logs'
log_file = os.path.join(log_dir, 'daily_run_status.log')
calls_log_file = os.path.join(log_dir, 'script_calls.log')
python_script = 'update_and_check_bubbles.py'
python_interpreter = '/Users/octaviantuchila/.pyenv/shims/python3'

# Create log directory if it doesn't exist
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Get current date and time
today = datetime.now().strftime('%Y-%m-%d')
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Read the last log entry
last_log_entry = None
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        lines = f.readlines()
        if lines:
            last_log_entry = lines[-1].strip()

# Log that the script has started
with open(calls_log_file, 'a') as f:
    f.write(f"{current_time} SCRIPT_STARTED\n")

if last_log_entry:
    last_run_date, last_status = last_log_entry.split(' ')
    if today == last_run_date and (last_status == 'SUCCESS' or last_status == 'RUNNING'):
        with open(calls_log_file, 'a') as f:
            f.write(f"{current_time} SCRIPT_EXITED_EARLY with status {last_status}\n")
        exit(0)
else:
    with open(calls_log_file, 'a') as f:
        f.write(f"{current_time} SCRIPT_STARTED\n")

# Log that the script is running
with open(log_file, 'a') as f:
    f.write(f"{today} RUNNING\n")

# Show macOS notification
subprocess.run(["osascript", "-e", 'display notification "Sornette started" with title "Sornette Status"'])

# Run the Python script
process = subprocess.run([python_interpreter, python_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working_directory)

# Get exit code of the Python script
exit_code = process.returncode

# Update log based on the Python script's exit code
with open(log_file, 'a') as f:
    if exit_code == 0:
        f.write(f"{today} SUCCESS\n")
        subprocess.run(["osascript", "-e", 'display notification "Sornette finished successfully" with title "Sornette Status"'])
    else:
        f.write(f"{today} FAILED\n")

# Log that the script finished
with open(calls_log_file, 'a') as f:
    f.write(f"{current_time} SCRIPT_FINISHED_WITH_CODE_{exit_code}\n")
