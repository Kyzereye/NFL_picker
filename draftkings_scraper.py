"""
DraftKings NFL Odds Scraper
Specialized scraper for DraftKings sportsbook NFL odds
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class DraftKingsGame:
    """Data structure for a DraftKings game"""
    home_team: str
    away_team: str
    home_odds: str
    away_odds: str
    spread_home: str
    spread_away: str
    over_under: str
    game_time: str
    
class DraftKingsScraper:
    """Scraper specifically designed for DraftKings NFL odds"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.base_url = "https://sportsbook.draftkings.com/leagues/football/nfl"
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={Config.USER_AGENT}")
        
        # Disable images and CSS for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
    
    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def scrape_nfl_odds(self) -> List[Dict[str, Any]]:
        """Scrape NFL odds from DraftKings"""
        games_data = []
        
        try:
            self._setup_driver()
            logger.info(f"Loading DraftKings NFL page: {self.base_url}")
            
            self.driver.get(self.base_url)
            
            # Wait for the page to load and odds to appear
            wait = WebDriverWait(self.driver, 20)
            
            # Try multiple selectors for game containers
            game_selectors = [
                '[data-testid="event-cell"]',
                '.sportsbook-event-accordion__wrapper',
                '.sportsbook-table__body',
                '[class*="event"]',
                '[class*="game"]'
            ]
            
            games_found = False
            for selector in game_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    games = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if games:
                        logger.info(f"Found {len(games)} game elements using selector: {selector}")
                        games_data = self._parse_games(games, selector)
                        games_found = True
                        break
                except TimeoutException:
                    continue
            
            if not games_found:
                # Fallback: try to extract any odds-related information
                logger.warning("Could not find game elements with standard selectors, trying fallback approach")
                games_data = self._fallback_scrape()
                
        except Exception as e:
            logger.error(f"Error scraping DraftKings: {e}")
        finally:
            self._close_driver()
        
        return games_data
    
    def _parse_games(self, games, selector: str) -> List[Dict[str, Any]]:
        """Parse game elements to extract odds data"""
        games_data = []
        
        for i, game in enumerate(games[:10]):  # Limit to first 10 games to avoid timeout
            try:
                game_data = self._extract_game_data(game, i)
                if game_data:
                    games_data.append(game_data)
            except Exception as e:
                logger.error(f"Error parsing game {i}: {e}")
                continue
        
        return games_data
    
    def _extract_game_data(self, game_element, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single game element"""
        try:
            # Get the HTML content of the game element
            game_html = game_element.get_attribute('outerHTML')
            soup = BeautifulSoup(game_html, 'html.parser')
            
            # Try to find team names
            team_elements = soup.find_all(text=re.compile(r'(Bills|Dolphins|Chiefs|Ravens|Steelers|Browns|Bengals|Texans|Colts|Titans|Jaguars|Broncos|Chargers|Raiders|Cowboys|Giants|Eagles|Commanders|Packers|Bears|Lions|Vikings|Saints|Falcons|Panthers|Buccaneers|Cardinals|Rams|49ers|Seahawks|Patriots|Jets)', re.IGNORECASE))
            
            # Try to find odds (format like +150, -110, etc.)
            odds_pattern = re.compile(r'[+-]\d{2,4}')
            odds_elements = odds_pattern.findall(game_html)
            
            # Try to find spreads (format like -3.5, +7, etc.)
            spread_pattern = re.compile(r'[+-]?\d+\.?5?')
            
            game_data = {
                'source': 'DraftKings',
                'teams_found': team_elements[:2] if team_elements else [],
                'odds_found': odds_elements[:4] if odds_elements else [],
                'raw_html_snippet': game_html[:200] + '...' if len(game_html) > 200 else game_html,
                'index': index,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Only return if we found some relevant data
            if team_elements or odds_elements:
                return game_data
                
        except Exception as e:
            logger.error(f"Error extracting data from game element: {e}")
        
        return None
    
    def _fallback_scrape(self) -> List[Dict[str, Any]]:
        """Fallback scraping method when standard selectors fail"""
        try:
            # Get the entire page source and look for patterns
            page_source = self.driver.page_source
            
            # Look for JSON data that might contain odds
            json_pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', re.DOTALL)
            json_matches = json_pattern.findall(page_source)
            
            fallback_data = []
            
            if json_matches:
                try:
                    for json_str in json_matches:
                        data = json.loads(json_str)
                        fallback_data.append({
                            'source': 'DraftKings_Fallback',
                            'data_type': 'JSON_Extract',
                            'data_keys': list(data.keys()) if isinstance(data, dict) else 'Not a dict',
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                except json.JSONDecodeError:
                    pass
            
            # Look for any text that contains team names and odds
            team_pattern = re.compile(r'(Bills|Dolphins|Chiefs|Ravens|Steelers|Browns|Bengals|Texans|Colts|Titans|Jaguars|Broncos|Chargers|Raiders|Cowboys|Giants|Eagles|Commanders|Packers|Bears|Lions|Vikings|Saints|Falcons|Panthers|Buccaneers|Cardinals|Rams|49ers|Seahawks|Patriots|Jets)', re.IGNORECASE)
            odds_pattern = re.compile(r'[+-]\d{2,4}')
            
            teams_found = team_pattern.findall(page_source)
            odds_found = odds_pattern.findall(page_source)
            
            if teams_found or odds_found:
                fallback_data.append({
                    'source': 'DraftKings_Fallback',
                    'data_type': 'Text_Extract',
                    'teams_found': list(set(teams_found))[:10],  # Unique teams, limit to 10
                    'odds_found': odds_found[:20],  # Limit to 20 odds
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error in fallback scraping: {e}")
            return []

class DraftKingsAPI:
    """Alternative approach using requests to find API endpoints"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.base_url = "https://sportsbook.draftkings.com"
    
    def find_api_endpoints(self) -> List[str]:
        """Try to find API endpoints that might contain odds data"""
        try:
            response = self.session.get(f"{self.base_url}/leagues/football/nfl")
            
            # Look for API calls in the page source
            api_pattern = re.compile(r'(/api/[^"\'>\s]+)', re.IGNORECASE)
            api_endpoints = api_pattern.findall(response.text)
            
            # Look for specific odds-related endpoints
            odds_endpoints = [ep for ep in api_endpoints if any(keyword in ep.lower() for keyword in ['odds', 'event', 'game', 'sport', 'nfl'])]
            
            return list(set(odds_endpoints))[:10]  # Return unique endpoints, limit to 10
            
        except Exception as e:
            logger.error(f"Error finding API endpoints: {e}")
            return []
    
    def try_api_endpoint(self, endpoint: str) -> Optional[Dict]:
        """Try to fetch data from an API endpoint"""
        try:
            full_url = f"{self.base_url}{endpoint}"
            response = self.session.get(full_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'text': response.text[:500]}  # Return first 500 chars if not JSON
            else:
                return {'status_code': response.status_code, 'error': 'Non-200 response'}
                
        except Exception as e:
            return {'error': str(e)}

def main():
    """Main function for testing the DraftKings scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("Starting DraftKings NFL odds scraper...")
    
    # Try the Selenium approach first
    scraper = DraftKingsScraper(headless=True)
    games_data = scraper.scrape_nfl_odds()
    
    if games_data:
        logger.info(f"Successfully scraped {len(games_data)} games from DraftKings")
        print(json.dumps(games_data, indent=2))
    else:
        logger.warning("No games data found with Selenium approach")
    
    # Try the API approach as fallback
    logger.info("Trying API endpoint discovery...")
    api_scraper = DraftKingsAPI()
    endpoints = api_scraper.find_api_endpoints()
    
    if endpoints:
        logger.info(f"Found {len(endpoints)} potential API endpoints")
        for endpoint in endpoints[:3]:  # Try first 3 endpoints
            logger.info(f"Trying endpoint: {endpoint}")
            data = api_scraper.try_api_endpoint(endpoint)
            if data and 'error' not in data:
                print(f"Data from {endpoint}:", json.dumps(data, indent=2)[:500])
    else:
        logger.warning("No API endpoints found")

if __name__ == "__main__":
    main()

