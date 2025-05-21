# Importing library(ies)
from bs4 import BeautifulSoup as bs
import requests as rqs
import pandas as pd
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set headers to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ( HTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36'
}

# Configure retry strategy for requests
retry_strategy = Retry(
    total=5,                     # Retry up to 5 times
    backoff_factor=1,           # Wait time increases (1s, 2s, 4s, etc.)
    status_forcelist=[429, 500, 502, 503, 504],  # Retry for these status codes
    allowed_methods=["GET"]     # Retry only for GET requests
)

# Create a session with the retry strategy
adapter = HTTPAdapter(max_retries=retry_strategy)
session = rqs.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

# Scraping the link of each category from the navigation bar
home_request = session.get('https://thesun.ng/', headers=headers, timeout=60).text
home_soup = bs(home_request, 'lxml')

ul = home_soup.find('ul', class_='navbar-nav')
categories = ul.find_all('a', class_='nav-link')

data = []
excluded_categories = ['Home', 'The Sun Foundation']

# Loop through each category tag to get its link and name
for category_tag in categories:
    text = category_tag.get_text(strip=True)
    if text not in excluded_categories:
        category_name = text
        category_link = category_tag['href']

        print(f"[+] Scraping category: {category_name}")

        # Fetch the category page
        try:
            category_request = session.get(category_link, headers=headers, timeout=60).text
        except rqs.exceptions.RequestException as e:
            print(f"[!] Failed to fetch {category_link}: {e}")
            continue  # Skip to the next category
        category_soup = bs(category_request, 'lxml')

        article_links = []

        # Find the featured article link
        featured_articles = category_soup.find('h3', class_='post-title')
        featured_article_link = featured_articles.find('a')['href']
        article_links.append(featured_article_link)

        # Find other article links on the page
        other_articles = category_soup.find_all('a', class_="col-lg-4 archive-grid-single")
        for article in other_articles:
            article_links.append(article['href'])

        for article_link in article_links:
            try:
                print(f"    --> Scraping article: {article_link}")
                article_request = session.get(article_link, headers=headers, timeout=60)
                article_soup = bs(article_request.text, 'lxml')

                article_tag = article_soup.find('div', class_='post-content')

                if not article_tag:
                    print("[!] No post-content div found")
                    continue  # Skip this article if main content is missing

                normal_paragraphs = article_tag.find_all('p')
                if not normal_paragraphs:
                    print("[!] No paragraphs found in post-content")
                else:
                    for para in normal_paragraphs:
                        text = para.get_text(strip=True)
                        if text:
                            data.append({
                                'paragraph': text,
                                'category': category_name,
                                'source': article_link
                            })

                    # Delaying the code to avoid hammering the server
                    time.sleep(2)
            except Exception as e:
                print(f"[!] Failed to scrape {article_link}: {e}")

# Convert the list of dictionary 'data' into a DataFrame
df = pd.DataFrame(data)
# Save the DataFrame to CSV file
df.to_csv('articles_paragraphs.csv')
print(f"\n[✓] Saved {len(data)} rows to scraped_articles_paragraphs.csv")
