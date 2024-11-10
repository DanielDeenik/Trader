import requests
import datetime
import json
import os
import pandas as pd

# Define constants
DANELFIN_API_BASE_URL = "https://apirest.danelfin.com/ranking"
API_KEY = "YOUR_API_KEY"
HEADERS = {'x-api-key': API_KEY}
CACHE_FILE = "ticker_data_cache.json"  # File to cache previous day's data

def fetch_top_tickers_data(date: str):
    """Fetches the top 100 tickers data for the given date."""
    params = {'date': date}
    response = requests.get(DANELFIN_API_BASE_URL, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def load_cached_data():
    """Loads cached data from a file, if available."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_data_to_cache(data):
    """Saves the current data to the cache file."""
    with open(CACHE_FILE, 'w') as file:
        json.dump(data, file)

def find_upgrades_downgrades(new_data, old_data):
    """Compares new data to old data to identify upgrades and downgrades."""
    upgrades = []
    downgrades = []
    
    for ticker, new_values in new_data.items():
        old_values = old_data.get(ticker, {})
        # Check if there's a change in scores (e.g., aiscore)
        if new_values['aiscore'] > old_values.get('aiscore', 0):
            upgrades.append({ticker: new_values})
        elif new_values['aiscore'] < old_values.get('aiscore', 0):
            downgrades.append({ticker: new_values})
    
    return upgrades, downgrades
