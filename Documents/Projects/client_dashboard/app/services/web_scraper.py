import requests
from bs4 import BeautifulSoup

class WebScraper:
    def __init__(self):
        pass

    def scrape_data(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.prettify()
        else:
            return f"Failed to retrieve data from {url}"
