import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv
import warnings
from urllib3.exceptions import NotOpenSSLWarning

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
§

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Establish database connection
engine = create_engine(DATABASE_URL)

# Directory where CSV files are stored
data_directory = 'data/'

# Define the database table name
table_name = 'danelfin_data'

def load_csv_to_db(file_path):
    """Load CSV file into database with timestamp, avoiding duplicates per day."""
    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path)
    
    # Add a timestamp column based on file name or current date
    file_date = datetime.today().strftime('%Y-%m-%d')
    df['timestamp'] = file_date  # Adjust if you want a different date format

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

def process_all_files():
    """Process all CSV files in the data directory."""
    for file_name in os.listdir(data_directory):
        if file_name.endswith('.csv'):
            file_path = os.path.join(data_directory, file_name)
            load_csv_to_db(file_path)

# Run the script to process all files in the directory
process_all_files()
