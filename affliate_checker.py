import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin, urlparse
import time
from requests.exceptions import RequestException
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class WebsiteScanner:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.program_keywords = [
            'affiliate', 'brand ambassador', 'influencer program', 
            'partner program', 'partnership program', 'collaboration'
        ]
        self.social_platforms = {
            'facebook': r'facebook\.com\/[\w\.]+',
            'instagram': r'instagram\.com\/[\w\.]+',
            'twitter': r'twitter\.com\/[\w\.]+',
            'linkedin': r'linkedin\.com\/[\w\-]+',
            'youtube': r'youtube\.com\/[\w\-]+',
            'tiktok': r'tiktok\.com\/@[\w\-]+'
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_page_content(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def find_program_links(self, soup, base_url):
        program_links = []
        for keyword in self.program_keywords:
            # Search in link text and href
            links = soup.find_all('a', text=re.compile(keyword, re.I)) + \
                   soup.find_all('a', href=re.compile(keyword, re.I))
            
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    program_links.append(full_url)
        
        return list(set(program_links))

    def find_social_links(self, soup, base_url):
        social_links = {}
        all_links = soup.find_all('a', href=True)
        
        for platform, pattern in self.social_platforms.items():
            platform_links = []
            for link in all_links:
                href = link.get('href', '')
                if re.search(pattern, href, re.I):
                    full_url = urljoin(base_url, href)
                    platform_links.append(full_url)
            if platform_links:
                social_links[platform] = list(set(platform_links))
        
        return social_links

    def get_meta_description(self, soup):
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')
        return ''

    def get_website_name(self, soup, url):
        title = soup.find('title')
        if title:
            return title.text.strip()
        
        h1 = soup.find('h1')
        if h1:
            return h1.text.strip()
        
        return urlparse(url).netloc

    def scan_website(self, url):
        try:
            content = self.get_page_content(url)
            if not content:
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            return {
                'website_url': url,
                'website_name': self.get_website_name(soup, url),
                'meta_description': self.get_meta_description(soup),
                'program_links': self.find_program_links(soup, url),
                'social_links': self.find_social_links(soup, url)
            }
        except Exception as e:
            self.logger.error(f"Error scanning {url}: {str(e)}")
            return None

    def scan_websites(self, urls):
        results = []
        for url in urls:
            self.logger.info(f"Scanning: {url}")
            result = self.scan_website(url)
            if result:
                results.append(result)
            time.sleep(1)  # Be nice to servers
        return results

class GoogleSheetsIntegration:
    def __init__(self):
        # No need for credentials file in this method
        pass  # Add this line to make the empty method valid

    def get_websites_from_sheet(self, sheet_id, sheet_name):
        try:
            # Read the Google Sheet directly as a CSV
            df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/1XNcR65DLxGYqu3imnHww34GIrNbJdzS1DTmLv0z-tXw/gviz/tq?tqx=out:csv&sheet=Mega%20-%20General")
            return df['website_url'].tolist()  # Adjust column name as needed
        except Exception as e:
            logging.error(f"Error reading Google Sheet: {str(e)}")
            return []

    def save_results_to_sheet(self, results, sheet_url):
        try:
            # Open the spreadsheet
            workbook = self.client.open_by_url(sheet_url)
            # Create a new sheet with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            worksheet = workbook.add_worksheet(
                title=f'Scan_Results_{timestamp}',
                rows="1000", cols="20"
            )

            # Prepare headers
            headers = ['Website URL', 'Website Name', 'Meta Description', 'Program Links']
            for platform in results[0]['social_links'].keys():
                headers.append(f'{platform.title()} Links')

            # Prepare data
            data = [headers]
            for result in results:
                row = [
                    result['website_url'],
                    result['website_name'],
                    result['meta_description'],
                    '\n'.join(result['program_links'])
                ]
                for platform in headers[4:]:  # Social media platforms
                    platform_name = platform.split()[0].lower()
                    links = result['social_links'].get(platform_name, [])
                    row.append('\n'.join(links))
                data.append(row)

            # Update the sheet
            worksheet.update('A1', data)
            
            # Format headers
            worksheet.format('A1:Z1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
            })

        except Exception as e:
            logging.error(f"Error saving to Google Sheet: {str(e)}")

def main():
    # Initialize classes
    gs = GoogleSheetsIntegration()
    scanner = WebsiteScanner()
    
    # Google Sheet details
    sheet_id = 'your-sheet-id'
    sheet_name = 'your-sheet-name'
    
    # Get websites from Google Sheet
    websites = gs.get_websites_from_sheet(sheet_id, sheet_name)
    
    # Scan websites
    results = scanner.scan_websites(websites)
    
    # Save to Excel as backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = f'website_scanning_results_{timestamp}.xlsx'
    
    df = pd.DataFrame(results)
    df.to_excel(excel_filename, index=False)
    
if __name__ == "__main__":
    main()
