from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

class AmazonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
    def get_title(self, soup):
        try:
            return soup.find("span", attrs={'id': 'productTitle'}).text.strip()
        except (AttributeError, Exception):
            return ""
            
    def get_price(self, soup):
        try:
            return soup.find("span", attrs={'class': 'a-offscreen'}).text
        except (AttributeError, Exception):
            return ""
            
    def scrape_product(self, link):
        try:
            product_page = requests.get(link, headers=self.headers, timeout=10)
            if product_page.status_code == 200:
                soup = BeautifulSoup(product_page.content, 'html.parser')
                return {
                    'title': self.get_title(soup),
                    'price': self.get_price(soup),
                    'link': link
                }
        except Exception as e:
            print(f"Error scraping {link}: {str(e)}")
        return None

    def scrape_amazon(self, keyword):
        url = f'https://www.amazon.in/s?k={keyword}'
        try:
            page = requests.get(url, headers=self.headers, timeout=10)
            if page.status_code != 200:
                return []
                
            soup = BeautifulSoup(page.content, 'html.parser')
            links = soup.find_all("a", attrs={'class':'a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal'})
            
            links_list = []
            for link in links[:10]:  # Limit to first 10 products
                href = link.get("href", "")
                if href:
                    full_link = "https://www.amazon.in" + href if not href.startswith("https://") else href
                    links_list.append(full_link)
            
            # Use ThreadPoolExecutor for parallel scraping
            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(self.scrape_product, links_list))
            
            # Filter out None results and create DataFrame
            results = [r for r in results if r]
            df = pd.DataFrame(results)
            
            if not df.empty:
                df['title'].replace('', np.nan, inplace=True)
                df = df.dropna(subset=['title'])
                return df.to_dict('records')
            return []
            
        except Exception as e:
            print(f"Error in scrape_amazon: {str(e)}")
            return []

scraper = AmazonScraper()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    keyword = request.form.get('keyword', '')
    if not keyword:
        return jsonify({'error': 'No keyword provided'}), 400
        
    try:
        results = scraper.scrape_amazon(keyword)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
