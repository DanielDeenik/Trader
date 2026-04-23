import os
import shutil
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv
import requests
import cronitor
import warnings
from urllib3.exceptions import NotOpenSSLWarning

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
# Load environment variables from .env file
load_dotenv()

# Set up Cronitor API key
cronitor.api_key = os.getenv('CRONITOR_API_KEY')
print("Cronitor API Key:", cronitor.api_key)


# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


# Configure Cronitor
cronitor.api_key = CRONITOR_API_KEY
monitor = cronitor.Monitor.put(
    key='danelfin-data-import',
    type='job'
)

# Set directories
DOWNLOADS_FOLDER = '/Users/danieldeenik/Downloads'
TARGET_FOLDER = '/Users/danieldeenik/Documents/Projects/trading_bot_template/data'
table_name = 'danelfin_data'

# Database connection
engine = create_engine(DATABASE_URL)

# Zapier webhook URL
ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/8507095/25mllqh/"

def send_zapier_notification():
    """Send a notification to Zapier via webhook."""
    response = requests.post(ZAPIER_WEBHOOK_URL, json={"status": "Danelfin data import complete"})
    if response.status_code == 200:
        print("Zapier webhook triggered successfully.")
    else:
        print("Failed to trigger Zapier webhook:", response.text)

def load_csv_to_db(file_path):
    """Load CSV file into database with timestamp, avoiding duplicates per day."""
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
            # Trigger Zapier webhook after successful data import
            send_zapier_notification()
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
    else:
        print(f"Data for {file_date} already exists in the database. Skipping file: {file_path}")

def move_and_process_files():
    """Move Danelfin files from Downloads to data folder and import them into the database."""
    for file_name in os.listdir(DOWNLOADS_FOLDER):
        if "Danelfin" in file_name and file_name.endswith('.csv'):
            file_path = os.path.join(DOWNLOADS_FOLDER, file_name)
            target_path = os.path.join(TARGET_FOLDER, file_name)
            shutil.move(file_path, target_path)
            print(f"Moved {file_name} to {TARGET_FOLDER}")
            # Load the CSV into the database
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
