import sys

sys.path.append(
    "/Users/octaviantuchila/Development/MonteCarlo/Sornette/lppls_python_updated/common"
)

import subprocess
from datetime import datetime
import os
from db_defaults import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
from typechecking import TypeCheckBase


class BackupDb(TypeCheckBase):
    @staticmethod
    def main():
        # Backup directory
        BACKUP_DIR = "/Users/octaviantuchila/Development/backups/asset_prices_db"
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        # Formatted date for the filename
        today_str = datetime.now().strftime("%Y%m%d")

        # Initialize the counter and backup file path
        counter = 0
        filename = f"asset_prices_backup_{today_str}.sql"
        backup_file_path = os.path.join(BACKUP_DIR, filename)

        # Increment the counter if the backup file for today already exists
        while os.path.exists(backup_file_path):
            counter += 1
            filename = f"asset_prices_backup_{today_str}_{counter}.sql"
            backup_file_path = os.path.join(BACKUP_DIR, filename)

        pg_dump_path = "/opt/homebrew/bin/pg_dump"  # Path to pg_dump
        # Command to run pg_dump
        command = [
            "zsh",
            "-c",
            f"{pg_dump_path} -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -F c > {backup_file_path}",
        ]

        # Set the environment variable for the password
        os.environ["PGPASSWORD"] = DB_PASSWORD

        try:
            # Run the pg_dump command
            subprocess.run(command, check=True)
            print(f"Backup completed: {backup_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred during backup: {e}")

        # Unset the PGPASSWORD environment variable
        del os.environ["PGPASSWORD"]


if __name__ == "__main__":
    BackupDb.main()
