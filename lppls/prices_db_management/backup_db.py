import sys
sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/lppls/common"
)

import subprocess
from datetime import datetime
import os
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

# Backup directory
BACKUP_DIR = "/Users/octaviantuchila/Development/backups/asset_prices_db"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Formatted date for the filename
today_str = datetime.now().strftime("%Y%m%d")
filename = f"asset_prices_backup_{today_str}.sql"

# Full path for the backup file
backup_file_path = os.path.join(BACKUP_DIR, filename)

# Check if a backup for today already exists
if os.path.exists(backup_file_path):
    print(f"A backup for today ({today_str}) already exists. No new backup created.")
else:
    # Command to run pg_dump
    command = f"zsh -c 'pg_dump -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -F c > {backup_file_path}'"

    # Set the environment variable for the password
    os.environ["PGPASSWORD"] = DB_PASSWORD

    try:
        # Run the pg_dump command
        subprocess.run(command, shell=True, check=True)
        print(f"Backup completed: {backup_file_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during backup: {e}")

    # Unset the PGPASSWORD environment variable
    del os.environ["PGPASSWORD"]