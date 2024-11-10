import os
import shutil
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv
import cronitor

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Define directories
DOWNLOADS_FOLDER = '/Users/danieldeenik/Downloads'
TARGET_FOLDER = '/Users/danieldeenik/Documents/Projects/trading_bot_template/data'
table_name = 'danelfin_data'
ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/8507095/25mllqh/"

# Define Cronitor monitor
monitor = cronitor.Monitor('danelfin-data-import')

def send_zapier_notification():
    """Notify via Zapier webhook."""
    response = requests.post(ZAPIER_WEBHOOK_URL, json={"status": "Danelfin data import complete"})
    if response.status_code == 200:
        print("Zapier webhook triggered successfully.")
    else:
        print("Failed to trigger Zapier webhook:", response.text)

def load_csv_to_db(file_path):
    """Load CSV into database, avoid duplicates."""
    df = pd.read_csv(file_path)
    file_date = datetime.today().strftime('%Y-%m-%d')
    df['timestamp'] = file_date

    with engine.connect() as connection:
        result = connection.execute(
            text(f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE timestamp = :file_date)"),
            {"file_date": file_date}
        ).scalar()

    if not result:
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            print(f"Data from {file_path} loaded successfully.")
            send_zapier_notification()
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
    else:
        print(f"Data for {file_date} already exists. Skipping: {file_path}")

def move_and_process_files():
    """Move Danelfin files, import to DB."""
    for file_name in os.listdir(DOWNLOADS_FOLDER):
        if "Danelfin" in file_name and file_name.endswith('.csv'):
            file_path = os.path.join(DOWNLOADS_FOLDER, file_name)
            target_path = os.path.join(TARGET_FOLDER, file_name)
            shutil.move(file_path, target_path)
            print(f"Moved {file_name} to {TARGET_FOLDER}")
            load_csv_to_db(target_path)

def run_import_process():
    """Run import with Cronitor monitoring."""
    try:
        monitor.ping(state='run')   # Start event
        move_and_process_files()
        monitor.ping(state='complete')  # Success event
    except Exception as e:
        monitor.ping(state='fail')  # Failure event
        print("An error occurred:", e)

if __name__ == "__main__":
    run_import_process()
