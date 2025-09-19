#!/usr/bin/env python3
"""
Improved DraftKings NFL Odds Scraper
Focuses on finding actual game events with complete odds data
"""

import sys
import os
import json
import re
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class DraftKingsGame:
    """Structured DraftKings game data"""
    home_team: str
    away_team: str
    moneyline_home: Optional[str] = None
    moneyline_away: Optional[str] = None
    spread_home: Optional[str] = None
    spread_away: Optional[str] = None
    spread_points: Optional[str] = None
    total_over: Optional[str] = None
    total_under: Optional[str] = None
    total_points: Optional[str] = None
    game_time: Optional[str] = None
    event_url: Optional[str] = None

class ImprovedDraftKingsScraper:
    """Improved scraper that focuses on finding complete game data"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.base_url = "https://sportsbook.draftkings.com/leagues/football/nfl"
        self.games = []
        
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
        
        # Disable images for faster loading
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
    
    def scrape_nfl_games(self) -> List[Dict[str, Any]]:
        """Scrape NFL games with improved logic"""
        try:
            self._setup_driver()
            logger.info(f"Loading DraftKings NFL page: {self.base_url}")
            
            self.driver.get(self.base_url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 20)
            time.sleep(5)  # Additional wait for dynamic content
            
            # Try multiple approaches to find games
            games = self._find_games_approach_1()
            if not games:
                games = self._find_games_approach_2()
            if not games:
                games = self._find_games_approach_3()
            
            # Deduplicate games
            unique_games = self._deduplicate_games(games)
            
            logger.info(f"Found {len(unique_games)} unique games")
            return unique_games
            
        except Exception as e:
            logger.error(f"Error scraping DraftKings: {e}")
            return []
        finally:
            self._close_driver()
    
    def _find_games_approach_1(self) -> List[Dict[str, Any]]:
        """Approach 1: Look for event cards or game containers"""
        games = []
        
        try:
            # Look for common game container patterns
            selectors = [
                '[data-testid*="event"]',
                '.sportsbook-event-accordion__wrapper',
                '.sportsbook-table__body tr',
                '[class*="event-cell"]',
                '[class*="game-card"]'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Trying selector '{selector}': found {len(elements)} elements")
                    
                    if elements:
                        for element in elements[:20]:  # Limit to first 20
                            game_data = self._extract_game_from_element(element)
                            if game_data:
                                games.append(game_data)
                        
                        if games:
                            logger.info(f"Approach 1 found {len(games)} games with selector: {selector}")
                            break
                            
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Approach 1 failed: {e}")
        
        return games
    
    def _find_games_approach_2(self) -> List[Dict[str, Any]]:
        """Approach 2: Look for team names and build games from there"""
        games = []
        
        try:
            # Find all elements containing NFL team names
            nfl_teams = [
                'Bills', 'Dolphins', 'Patriots', 'Jets',
                'Ravens', 'Bengals', 'Browns', 'Steelers', 
                'Texans', 'Colts', 'Jaguars', 'Titans',
                'Broncos', 'Chiefs', 'Raiders', 'Chargers',
                'Cowboys', 'Giants', 'Eagles', 'Commanders',
                'Bears', 'Lions', 'Packers', 'Vikings',
                'Falcons', 'Panthers', 'Saints', 'Buccaneers',
                'Cardinals', 'Rams', '49ers', 'Seahawks'
            ]
            
            team_elements = []
            for team in nfl_teams:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{team}')]")
                    team_elements.extend(elements)
                except:
                    continue
            
            logger.info(f"Found {len(team_elements)} elements with team names")
            
            # Group team elements by their parent containers
            game_containers = {}
            for element in team_elements:
                try:
                    # Find the parent container that likely represents a game
                    parent = element
                    for _ in range(5):  # Go up 5 levels max
                        parent = parent.find_element(By.XPATH, "..")
                        if self._looks_like_game_container(parent):
                            container_html = parent.get_attribute('outerHTML')
                            if container_html not in game_containers:
                                game_containers[container_html] = parent
                            break
                except:
                    continue
            
            logger.info(f"Found {len(game_containers)} potential game containers")
            
            # Extract games from containers
            for container in game_containers.values():
                game_data = self._extract_game_from_element(container)
                if game_data:
                    games.append(game_data)
            
        except Exception as e:
            logger.error(f"Approach 2 failed: {e}")
        
        return games
    
    def _find_games_approach_3(self) -> List[Dict[str, Any]]:
        """Approach 3: Look for specific patterns in page source"""
        games = []
        
        try:
            page_source = self.driver.page_source
            
            # Look for matchup patterns
            matchup_patterns = [
                r'([A-Za-z\s]+)\s+@\s+([A-Za-z\s]+)',
                r'([A-Za-z\s]+)\s+vs\.?\s+([A-Za-z\s]+)',
                r'([A-Za-z\s]+)\s+-\s+([A-Za-z\s]+)'
            ]
            
            found_matchups = set()
            for pattern in matchup_patterns:
                matches = re.findall(pattern, page_source)
                for away, home in matches:
                    away = away.strip()
                    home = home.strip()
                    if self._is_nfl_team(away) and self._is_nfl_team(home):
                        matchup = f"{away} @ {home}"
                        if matchup not in found_matchups:
                            found_matchups.add(matchup)
                            games.append({
                                'home_team': home,
                                'away_team': away,
                                'matchup': matchup,
                                'source': 'DraftKings_Pattern',
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                            })
            
            logger.info(f"Approach 3 found {len(games)} games via pattern matching")
            
        except Exception as e:
            logger.error(f"Approach 3 failed: {e}")
        
        return games
    
    def _looks_like_game_container(self, element) -> bool:
        """Check if an element looks like a game container"""
        try:
            html = element.get_attribute('outerHTML')
            class_name = element.get_attribute('class') or ''
            
            # Look for common game container indicators
            indicators = [
                'event' in class_name.lower(),
                'game' in class_name.lower(),
                'match' in class_name.lower(),
                'odds' in html.lower(),
                len(re.findall(r'[+-]\d{2,4}', html)) >= 2,  # Has multiple odds
            ]
            
            return sum(indicators) >= 2
            
        except:
            return False
    
    def _extract_game_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract game data from a DOM element"""
        try:
            html = element.get_attribute('outerHTML')
            text = element.text
            
            # Extract team names
            teams = self._extract_teams_from_text(text)
            if len(teams) < 2:
                teams = self._extract_teams_from_html(html)
            
            if len(teams) < 2:
                return None
            
            # Extract odds
            odds = re.findall(r'[+-]\d{2,4}', html)
            
            # Try to find event URL
            event_url = None
            try:
                link = element.find_element(By.TAG_NAME, 'a')
                href = link.get_attribute('href')
                if href and '/event/' in href:
                    event_url = href
            except:
                pass
            
            game_data = {
                'home_team': teams[1] if len(teams) > 1 else teams[0],
                'away_team': teams[0],
                'teams_found': teams,
                'odds_found': odds,
                'event_url': event_url,
                'source': 'DraftKings_Improved',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'raw_text': text[:200] if text else '',
            }
            
            return game_data
            
        except Exception as e:
            logger.debug(f"Error extracting game data: {e}")
            return None
    
    def _extract_teams_from_text(self, text: str) -> List[str]:
        """Extract team names from text"""
        if not text:
            return []
        
        # Common team name patterns
        nfl_teams = [
            'Bills', 'Dolphins', 'Patriots', 'Jets',
            'Ravens', 'Bengals', 'Browns', 'Steelers', 
            'Texans', 'Colts', 'Jaguars', 'Titans',
            'Broncos', 'Chiefs', 'Raiders', 'Chargers',
            'Cowboys', 'Giants', 'Eagles', 'Commanders',
            'Bears', 'Lions', 'Packers', 'Vikings',
            'Falcons', 'Panthers', 'Saints', 'Buccaneers',
            'Cardinals', 'Rams', '49ers', 'Seahawks'
        ]
        
        found_teams = []
        for team in nfl_teams:
            if team in text:
                found_teams.append(team)
        
        return list(set(found_teams))  # Remove duplicates
    
    def _extract_teams_from_html(self, html: str) -> List[str]:
        """Extract team names from HTML"""
        return self._extract_teams_from_text(html)
    
    def _is_nfl_team(self, name: str) -> bool:
        """Check if a name is an NFL team"""
        nfl_teams = [
            'Bills', 'Dolphins', 'Patriots', 'Jets',
            'Ravens', 'Bengals', 'Browns', 'Steelers', 
            'Texans', 'Colts', 'Jaguars', 'Titans',
            'Broncos', 'Chiefs', 'Raiders', 'Chargers',
            'Cowboys', 'Giants', 'Eagles', 'Commanders',
            'Bears', 'Lions', 'Packers', 'Vikings',
            'Falcons', 'Panthers', 'Saints', 'Buccaneers',
            'Cardinals', 'Rams', '49ers', 'Seahawks'
        ]
        
        return any(team in name for team in nfl_teams)
    
    def _deduplicate_games(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate games based on team matchups"""
        seen_matchups = set()
        unique_games = []
        
        for game in games:
            teams = game.get('teams_found', [])
            if len(teams) >= 2:
                # Create a normalized matchup key
                matchup_key = tuple(sorted(teams[:2]))
                
                if matchup_key not in seen_matchups:
                    seen_matchups.add(matchup_key)
                    unique_games.append(game)
        
        return unique_games

def main():
    """Test the improved scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("Testing improved DraftKings scraper...")
    
    scraper = ImprovedDraftKingsScraper(headless=True)
    games = scraper.scrape_nfl_games()
    
    if games:
        logger.info(f"Successfully found {len(games)} unique games")
        
        for i, game in enumerate(games):
            teams = game.get('teams_found', [])
            odds = game.get('odds_found', [])
            url = game.get('event_url', 'No URL')
            logger.info(f"Game {i+1}: {' vs '.join(teams)} | Odds: {odds[:4]} | URL: {url}")
        
        # Save results
        output_file = "data/improved_draftkings_test.json"
        with open(output_file, 'w') as f:
            json.dump(games, f, indent=2)
        logger.info(f"Results saved to {output_file}")
        
    else:
        logger.warning("No games found")

if __name__ == "__main__":
    main()

