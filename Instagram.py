import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ratelimit import limits, sleep_and_retry

# Add these constants at the top of the file, after imports
CALLS_LIMIT = 20  # Maximum number of API calls
CALLS_PERIOD = 3600  # Time period in seconds (1 hour)

def load_websites_from_sheets(sheet_id, sheet_name):
    """
    Load websites from Google Sheets using the Sheets API
    Returns a list of website URLs
    """
    try:
        # You'll need to set up Google Sheets API authentication
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}")
        return df['website_url'].tolist()  # Adjust column name as needed
    except Exception as e:
        print(f"Error loading spreadsheet: {e}")
        return []

def find_instagram_link(url):
    """
    Scrapes a website to find Instagram links
    Returns the Instagram profile URL if found, None otherwise
    """
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Common patterns for Instagram links
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_\.]+/?',
            r'instagram\.com/[A-Za-z0-9_\.]+/?'
        ]
        
        # Search in all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Make relative URLs absolute
            full_url = urljoin(url, href)
            
            # Check against patterns
            for pattern in instagram_patterns:
                if re.search(pattern, full_url, re.IGNORECASE):
                    return full_url
                
        # Search in text content for Instagram handles
        text_content = soup.get_text()
        for pattern in instagram_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(0)
                
        return None
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def follow_instagram_account(driver, instagram_url):
    """
    Uses Selenium to follow an Instagram account
    Requires prior login to Instagram
    """
    try:
        driver.get(instagram_url)
        # Wait for the follow button to be clickable
        follow_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Follow')]"))
        )
        # Add random delay to avoid detection
        time.sleep(2 + random.random() * 3)
        follow_button.click()
        return True
    except Exception as e:
        print(f"Error following {instagram_url}: {e}")
        return False

def main():
    # Configuration
    SHEET_ID = '1XNcR65DLxGYqu3imnHww34GIrNbJdzS1DTmLv0z-tXw'
    SHEET_NAME = 'Mega - General'
    INSTAGRAM_USERNAME = 'your_username'
    INSTAGRAM_PASSWORD = 'your_password'
    
    # Load websites from Google Sheets
    websites = load_websites_from_sheets(SHEET_ID, SHEET_NAME)
    
    # Set up Selenium WebDriver
    driver = webdriver.Chrome()  # Make sure you have ChromeDriver installed
    
    try:
        # Log into Instagram
        driver.get('https://www.instagram.com/accounts/login/')
        
        # Wait for username field and enter username
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys(INSTAGRAM_USERNAME)
        
        # Enter password
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(INSTAGRAM_PASSWORD)
        
        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # Wait for login to complete (you may need to adjust this)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
        )
        
        print("Successfully logged in to Instagram")
        
        # Process each website
        for website in websites:
            print(f"Processing {website}")
            
            # Find Instagram link
            instagram_url = find_instagram_link(website)
            
            if instagram_url:
                print(f"Found Instagram: {instagram_url}")
                # Add delay between actions
                time.sleep(5 + random.random() * 5)
                
                # Follow the account (now rate-limited)
                success = follow_instagram_account(driver, instagram_url)
                if success:
                    print(f"Successfully followed {instagram_url}")
                else:
                    print(f"Failed to follow {instagram_url}")
            
            # Add delay between websites
            time.sleep(3 + random.random() * 3)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
