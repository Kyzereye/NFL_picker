#!/usr/bin/env python3
"""
Simple test script for DraftKings scraping
"""

import sys
import os
import logging
import json
import requests
from bs4 import BeautifulSoup

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config, SeasonConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_request():
    """Test basic request to DraftKings NFL page"""
    url = "https://sportsbook.draftkings.com/leagues/football/nfl"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': Config.USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    try:
        logger.info(f"Making request to: {url}")
        response = session.get(url, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Save the HTML for analysis
            with open('/home/jeff/Projects/study/NFL/draftkings_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Look for key indicators
            content = response.text.lower()
            indicators = {
                'bills': 'bills' in content,
                'dolphins': 'dolphins' in content,
                'odds': any(term in content for term in ['+', '-', 'odds', 'moneyline']),
                'nfl': 'nfl' in content,
                'thursday': 'thursday' in content,
                'javascript': 'javascript' in content or 'script' in content
            }
            
            logger.info(f"Content indicators: {indicators}")
            logger.info(f"Page size: {len(response.text)} characters")
            
            # Try to find any JSON data
            import re
            json_pattern = re.compile(r'window\.__[A-Z_]+__\s*=\s*({.*?});', re.DOTALL)
            json_matches = json_pattern.findall(response.text)
            
            if json_matches:
                logger.info(f"Found {len(json_matches)} potential JSON objects")
                for i, match in enumerate(json_matches[:3]):  # Show first 3
                    try:
                        data = json.loads(match)
                        logger.info(f"JSON object {i+1} keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    except json.JSONDecodeError:
                        logger.info(f"JSON object {i+1}: Failed to parse")
            
            return True
        else:
            logger.error(f"Request failed with status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error making request: {e}")
        return False

def test_api_discovery():
    """Try to discover API endpoints"""
    url = "https://sportsbook.draftkings.com/leagues/football/nfl"
    
    session = requests.Session()
    session.headers.update({'User-Agent': Config.USER_AGENT})
    
    try:
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            import re
            
            # Look for API patterns
            api_patterns = [
                r'/api/[^"\'\s>]+',
                r'https://[^"\']*api[^"\'\s>]*',
                r'https://sportsbook-nash[^"\'\s>]*',
                r'/sportsbook-nash[^"\'\s>]*'
            ]
            
            all_endpoints = set()
            for pattern in api_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                all_endpoints.update(matches)
            
            if all_endpoints:
                logger.info(f"Found {len(all_endpoints)} potential API endpoints:")
                for endpoint in sorted(list(all_endpoints))[:10]:  # Show first 10
                    logger.info(f"  {endpoint}")
                
                # Try to access a few endpoints
                for endpoint in list(all_endpoints)[:3]:
                    try:
                        if endpoint.startswith('/'):
                            full_url = f"https://sportsbook.draftkings.com{endpoint}"
                        else:
                            full_url = endpoint
                        
                        logger.info(f"Trying endpoint: {full_url}")
                        api_response = session.get(full_url, timeout=10)
                        logger.info(f"  Status: {api_response.status_code}")
                        
                        if api_response.status_code == 200:
                            try:
                                data = api_response.json()
                                logger.info(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            except json.JSONDecodeError:
                                logger.info(f"  Content type: {api_response.headers.get('content-type', 'unknown')}")
                                logger.info(f"  Content preview: {api_response.text[:100]}...")
                    except Exception as e:
                        logger.info(f"  Error: {e}")
            else:
                logger.info("No API endpoints found")
                
    except Exception as e:
        logger.error(f"Error in API discovery: {e}")

def test_simple_selenium():
    """Test basic Selenium functionality"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        logger.info("Testing Selenium setup...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={Config.USER_AGENT}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        url = "https://sportsbook.draftkings.com/leagues/football/nfl"
        logger.info(f"Loading page with Selenium: {url}")
        
        driver.get(url)
        
        # Wait a bit for JavaScript to load
        import time
        time.sleep(5)
        
        # Get page title
        title = driver.title
        logger.info(f"Page title: {title}")
        
        # Look for common elements
        try:
            # Try to find any elements with team names
            team_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Bills') or contains(text(), 'Dolphins') or contains(text(), 'Chiefs')]")
            logger.info(f"Found {len(team_elements)} elements with team names")
            
            # Try to find elements with odds-like text
            odds_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '+') or contains(text(), '-')]")
            logger.info(f"Found {len(odds_elements)} elements with +/- characters")
            
            # Get page source and save it
            page_source = driver.page_source
            with open('/home/jeff/Projects/study/NFL/draftkings_selenium.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            
            logger.info(f"Selenium page source saved, length: {len(page_source)}")
            
        except Exception as e:
            logger.error(f"Error finding elements: {e}")
        
        driver.quit()
        logger.info("Selenium test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Selenium test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting DraftKings scraping tests...")
    
    # Test 1: Basic HTTP request
    logger.info("\n=== Test 1: Basic HTTP Request ===")
    test_basic_request()
    
    # Test 2: API discovery
    logger.info("\n=== Test 2: API Discovery ===")
    test_api_discovery()
    
    # Test 3: Simple Selenium
    logger.info("\n=== Test 3: Selenium Test ===")
    test_simple_selenium()
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    main()

