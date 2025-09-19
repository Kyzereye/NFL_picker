#!/usr/bin/env python3
"""
Final DraftKings NFL Odds Scraper - Based on actual page analysis
"""

import sys
import os
import json
import re
import time
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

logger = logging.getLogger(__name__)

class FinalDraftKingsScraper:
    """Final working DraftKings scraper based on page analysis"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.base_url = "https://sportsbook.draftkings.com/leagues/football/nfl"
        
    def _setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--user-agent={Config.USER_AGENT}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        logger.info("Chrome WebDriver initialized")
        
    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            
    def scrape_nfl_odds(self) -> List[Dict[str, Any]]:
        """Scrape NFL odds using the correct approach"""
        try:
            self._setup_driver()
            logger.info(f"Loading DraftKings NFL page: {self.base_url}")
            
            self.driver.get(self.base_url)
            time.sleep(8)  # Wait for dynamic content
            
            # Get all event links (we found 112 of these)
            event_links = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/event/")]')
            logger.info(f"Found {len(event_links)} event links")
            
            # Extract unique games from event links
            games = self._extract_games_from_links(event_links)
            
            # Get additional odds data from the page
            games = self._enrich_games_with_odds(games)
            
            logger.info(f"Successfully extracted {len(games)} games")
            return games
            
        except Exception as e:
            logger.error(f"Error scraping DraftKings: {e}")
            return []
        finally:
            self._close_driver()
    
    def _extract_games_from_links(self, event_links) -> List[Dict[str, Any]]:
        """Extract games from event links"""
        games = {}  # Use dict to avoid duplicates
        
        for link in event_links:
            try:
                href = link.get_attribute('href')
                if not href or '/event/' not in href:
                    continue
                
                # Extract teams from URL like "/event/min-vikings-%40-pit-steelers/32225655"
                url_part = href.split('/event/')[-1].split('/')[0]
                
                # Parse team names from URL
                if '%40' in url_part:  # @ symbol encoded
                    parts = url_part.split('%40')
                    if len(parts) == 2:
                        away_team = self._clean_team_name(parts[0])
                        home_team = self._clean_team_name(parts[1])
                        
                        game_key = f"{away_team}_at_{home_team}"
                        if game_key not in games:
                            games[game_key] = {
                                'away_team': away_team,
                                'home_team': home_team,
                                'matchup': f"{away_team} @ {home_team}",
                                'event_url': href,
                                'source': 'DraftKings',
                                'moneyline_odds': {},
                                'spread_odds': {},
                                'total_odds': {},
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                        
            except Exception as e:
                logger.debug(f"Error processing link: {e}")
                continue
        
        return list(games.values())
    
    def _clean_team_name(self, raw_name: str) -> str:
        """Clean and format team name"""
        # Remove hyphens and convert to proper case
        cleaned = raw_name.replace('-', ' ').title()
        
        # Handle special cases
        team_mappings = {
            'Min Vikings': 'Minnesota Vikings',
            'Pit Steelers': 'Pittsburgh Steelers',
            'No Saints': 'New Orleans Saints',
            'Buf Bills': 'Buffalo Bills',
            'Cle Browns': 'Cleveland Browns',
            'Det Lions': 'Detroit Lions',
            'Phi Eagles': 'Philadelphia Eagles',
            'Tb Buccaneers': 'Tampa Bay Buccaneers',
            'Ten Titans': 'Tennessee Titans',
            'Hou Texans': 'Houston Texans',
            'Gb Packers': 'Green Bay Packers',
            'Dal Cowboys': 'Dallas Cowboys',
            'Ny Jets': 'New York Jets',
            'Mia Dolphins': 'Miami Dolphins',
            'Cin Bengals': 'Cincinnati Bengals',
            'Den Broncos': 'Denver Broncos',
            'Sea Seahawks': 'Seattle Seahawks',
            'Ari Cardinals': 'Arizona Cardinals'
        }
        
        return team_mappings.get(cleaned, cleaned)
    
    def _enrich_games_with_odds(self, games: List[Dict]) -> List[Dict]:
        """Add odds data to games by parsing the page"""
        try:
            # Find all betting buttons with odds
            odds_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="component-builder-market-button"]')
            logger.info(f"Found {len(odds_buttons)} odds buttons")
            
            # Group odds by their parent containers
            for game in games:
                try:
                    # Look for this specific game's odds
                    game_odds = self._find_odds_for_game(game)
                    if game_odds:
                        game.update(game_odds)
                except Exception as e:
                    logger.debug(f"Error enriching game {game.get('matchup', 'unknown')}: {e}")
            
            return games
            
        except Exception as e:
            logger.error(f"Error enriching games with odds: {e}")
            return games
    
    def _find_odds_for_game(self, game: Dict) -> Dict:
        """Find odds for a specific game"""
        try:
            # Look for the game's container on the page
            away_team = game['away_team'].split()[-1]  # Get last word (team name)
            home_team = game['home_team'].split()[-1]
            
            # Find elements containing both team names
            xpath = f"//*[contains(text(), '{away_team}') and contains(text(), '{home_team}')]"
            
            try:
                game_elements = self.driver.find_elements(By.XPATH, xpath)
                if not game_elements:
                    # Try with shorter team names
                    away_short = away_team[:3]
                    home_short = home_team[:3]
                    xpath = f"//*[contains(text(), '{away_short}') and contains(text(), '{home_short}')]"
                    game_elements = self.driver.find_elements(By.XPATH, xpath)
                
                if game_elements:
                    # Find the parent container with odds
                    for element in game_elements:
                        parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'cb-static-parlay__event-wrapper')]")
                        if parent:
                            return self._extract_odds_from_container(parent)
                            
            except Exception as e:
                logger.debug(f"Could not find odds for {game['matchup']}: {e}")
                
        except Exception as e:
            logger.debug(f"Error finding odds for game: {e}")
        
        return {}
    
    def _extract_odds_from_container(self, container) -> Dict:
        """Extract odds from a game container"""
        odds_data = {}
        
        try:
            # Find all odds buttons in this container
            buttons = container.find_elements(By.CSS_SELECTOR, 'button[data-testid="component-builder-market-button"]')
            
            odds_values = []
            spreads = []
            totals = []
            
            for button in buttons:
                try:
                    # Get odds value
                    odds_elem = button.find_element(By.CSS_SELECTOR, '[data-testid="button-odds-market-board"]')
                    odds_text = odds_elem.text.strip()
                    if odds_text:
                        odds_values.append(odds_text)
                    
                    # Get spread/total points
                    try:
                        points_elem = button.find_element(By.CSS_SELECTOR, '[data-testid="button-points-market-board"]')
                        points_text = points_elem.text.strip()
                        if points_text:
                            if points_text.startswith(('+', '-')) and '.' in points_text:
                                spreads.append(f"{points_text}:{odds_text}")
                            elif points_text.replace('.', '').isdigit():
                                totals.append(f"{points_text}:{odds_text}")
                    except:
                        pass
                        
                except Exception as e:
                    logger.debug(f"Error extracting from button: {e}")
                    continue
            
            if odds_values:
                odds_data['odds_found'] = odds_values
            if spreads:
                odds_data['spreads_found'] = spreads
            if totals:
                odds_data['totals_found'] = totals
                
        except Exception as e:
            logger.debug(f"Error extracting odds from container: {e}")
        
        return odds_data

def main():
    """Test the final scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("Testing final DraftKings scraper...")
    
    scraper = FinalDraftKingsScraper(headless=True)
    games = scraper.scrape_nfl_odds()
    
    if games:
        logger.info(f"Successfully scraped {len(games)} games")
        
        for i, game in enumerate(games[:10]):  # Show first 10
            logger.info(f"Game {i+1}: {game['matchup']}")
            logger.info(f"  Odds: {game.get('odds_found', [])}")
            logger.info(f"  Spreads: {game.get('spreads_found', [])}")
            logger.info(f"  Totals: {game.get('totals_found', [])}")
        
        # Save results
        output_file = "data/final_draftkings_odds.json"
        with open(output_file, 'w') as f:
            json.dump(games, f, indent=2)
        logger.info(f"Results saved to {output_file}")
        
    else:
        logger.warning("No games found")

if __name__ == "__main__":
    main()

