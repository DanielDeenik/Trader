import os
import time
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv
import cronitor
import warnings
from urllib3.exceptions import NotOpenSSLWarning

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)




# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# Set up Cronitor API key
cronitor.api_key = os.getenv('CRONITOR_API_KEY')

# Establish database connection
engine = create_engine(DATABASE_URL)

# Set directories
DOWNLOADS_FOLDER = '/Users/danieldeenik/Downloads'
TARGET_FOLDER = '/path/to/your/project/data'  # Update this to your actual data directory path
table_name = 'danelfin_data'

def load_csv_to_db(file_path):
    """Load CSV file into database with timestamp, avoiding duplicates per day."""
    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path)
    
    # Add a timestamp column based on the current date
    file_date = datetime.today().strftime('%Y-%m-%d')
    df['timestamp'] = file_date

    # Check if the date already exists in the database
    with engine.connect() as connection:
        result = connection.execute(
            text(f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE timestamp = :file_date)"),
            {"file_date": file_date}
        ).scalar()

    # Only load data if no duplicate for the date is found
    if not result:
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            print(f"Data from {file_path} loaded successfully.")
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
    else:
        print(f"Data for {file_date} already exists in the database. Skipping file: {file_path}")

class DanelfinHandler(FileSystemEventHandler):
    """Handler for monitoring Danelfin files in the Downloads folder."""
    def on_created(self, event):
        # Check if the new file is a Danelfin CSV
        if event.is_directory:
            return
        if "Danelfin" in event.src_path and event.src_path.endswith('.csv'):
            print(f"New Danelfin file detected: {event.src_path}")
            # Move file to the target folder
            filename = os.path.basename(event.src_path)
            target_path = os.path.join(TARGET_FOLDER, filename)
            shutil.move(event.src_path, target_path)
            print(f"Moved {filename} to {TARGET_FOLDER}")
            # Load the CSV into the database
            load_csv_to_db(target_path)

if __name__ == "__main__":
    # Create observer
    event_handler = DanelfinHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DOWNLOADS_FOLDER, recursive=False)

    # Start observer
    observer.start()
    print(f"Monitoring {DOWNLOADS_FOLDER} for new Danelfin files...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
