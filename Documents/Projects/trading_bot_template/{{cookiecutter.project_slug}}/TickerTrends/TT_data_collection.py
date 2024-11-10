import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

TICKERTRENDS_API_KEY = os.getenv("TICKERTRENDS_API_KEY")
TICKERTRENDS_API_URL = "https://api.tickertrends.com/v1/trends"
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

def collect_data_from_tickertrends(tickers):
    data =       for ticker in tickers:
        params = {"ticker": ticker, "api_key": TICKERTRENDS_API_KEY}
        try:
            response = requests.get(TICKERTRENDS_API_URL, params=params)
            response.raise_for_status()
            trends = response.json()
            for trend in trends:
                data.append({"text": trend["text"], "ticker": ticker})
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {ticker}: {e}")
    return data

def collect_data_from_discord(channel_id, token):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Discord: {e}")
        return   def get_trending_tickers(num_tickers=10):
    try:
        url = f"{TICKERTRENDS_API_URL}?api_key={TICKERTRENDS_API_KEY}&limit={num_tickers}"
        response = requests.get(url)
        response.raise_for_status()
        return [trend["ticker"] for trend in response.json()]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching trending tickers: {e}")
        return   # Example usage
if __name__ == "__main__":
    tickers = get_trending_tickers()
    ticker_data = collect_data_from_tickertrends(tickers)
    discord_data = collect_data_from_discord(DISCORD_CHANNEL_ID, DISCORD_BOT_TOKEN)
    print(ticker_data)
    print(discord_data)
