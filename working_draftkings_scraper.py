#!/usr/bin/env python3
"""
Working DraftKings NFL Odds Scraper - Simplified approach that gets both games and odds
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

class WorkingDraftKingsScraper:
    """Simplified working DraftKings scraper"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        
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
        
    def scrape_nfl_odds(self) -> List[Dict[str, Any]]:
        """Scrape NFL odds - simplified approach"""
        try:
            self._setup_driver()
            logger.info("Loading DraftKings NFL page...")
            
            self.driver.get("https://sportsbook.draftkings.com/leagues/football/nfl")
            time.sleep(8)  # Wait for content to load
            
            # Get page source and parse it directly
            page_source = self.driver.page_source
            
            # Extract games from event URLs
            games = self._extract_games_from_source(page_source)
            
            # Extract odds from the page
            odds_data = self._extract_odds_from_source(page_source)
            
            # Combine games with odds where possible
            enriched_games = self._combine_games_and_odds(games, odds_data)
            
            logger.info(f"Found {len(enriched_games)} games with data")
            return enriched_games
            
        except Exception as e:
            logger.error(f"Error scraping DraftKings: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_games_from_source(self, page_source: str) -> List[Dict[str, Any]]:
        """Extract games from page source"""
        games = []
        
        # Find event URLs like "/event/team1-%40-team2/id"
        event_pattern = r'/event/([^/]+)/\d+'
        matches = re.findall(event_pattern, page_source)
        
        seen_matchups = set()
        for match in matches:
            if '%40' in match:  # @ symbol encoded
                try:
                    parts = match.split('%40')
                    if len(parts) == 2:
                        away_team = self._format_team_name(parts[0])
                        home_team = self._format_team_name(parts[1])
                        
                        matchup = f"{away_team} @ {home_team}"
                        if matchup not in seen_matchups:
                            seen_matchups.add(matchup)
                            games.append({
                                'away_team': away_team,
                                'home_team': home_team,
                                'matchup': matchup,
                                'source': 'DraftKings'
                            })
                except:
                    continue
        
        return games
    
    def _extract_odds_from_source(self, page_source: str) -> Dict[str, List[str]]:
        """Extract all odds from page source"""
        odds_data = {}
        
        # Find all odds patterns (like -110, +150, etc.)
        odds_pattern = r'[+-]\d{2,4}'
        all_odds = re.findall(odds_pattern, page_source)
        
        # Find spread patterns (like +3.5, -7)
        spread_pattern = r'[+-]\d+\.5'
        spreads = re.findall(spread_pattern, page_source)
        
        # Find total patterns (like O 47.5, U 44.5)
        total_pattern = r'[OU]\s*\d+\.5'
        totals = re.findall(total_pattern, page_source)
        
        odds_data['all_odds'] = all_odds
        odds_data['spreads'] = spreads  
        odds_data['totals'] = totals
        
        return odds_data
    
    def _format_team_name(self, raw_name: str) -> str:
        """Format team name from URL format"""
        # Convert from "mia-dolphins" to "Miami Dolphins"
        parts = raw_name.split('-')
        formatted_parts = []
        
        for part in parts:
            if part.lower() in ['mia', 'miami']:
                formatted_parts.append('Miami')
            elif part.lower() in ['buf', 'buffalo']:
                formatted_parts.append('Buffalo')
            elif part.lower() in ['ne', 'new', 'england']:
                if part.lower() == 'ne':
                    formatted_parts.extend(['New', 'England'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['ny', 'new', 'york']:
                if part.lower() == 'ny':
                    formatted_parts.extend(['New', 'York'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['gb', 'green', 'bay']:
                if part.lower() == 'gb':
                    formatted_parts.extend(['Green', 'Bay'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['tb', 'tampa', 'bay']:
                if part.lower() == 'tb':
                    formatted_parts.extend(['Tampa', 'Bay'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['no', 'new', 'orleans']:
                if part.lower() == 'no':
                    formatted_parts.extend(['New', 'Orleans'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['la', 'los', 'angeles']:
                if part.lower() == 'la':
                    formatted_parts.extend(['Los', 'Angeles'])
                else:
                    formatted_parts.append(part.title())
            elif part.lower() in ['lv', 'las', 'vegas']:
                if part.lower() == 'lv':
                    formatted_parts.extend(['Las', 'Vegas'])
                else:
                    formatted_parts.append(part.title())
            else:
                formatted_parts.append(part.title())
        
        return ' '.join(formatted_parts)
    
    def _combine_games_and_odds(self, games: List[Dict], odds_data: Dict) -> List[Dict]:
        """Combine games with odds data"""
        all_odds = odds_data.get('all_odds', [])
        spreads = odds_data.get('spreads', [])
        totals = odds_data.get('totals', [])
        
        # Add summary odds info to each game
        for i, game in enumerate(games):
            # Distribute odds across games
            start_idx = (i * 4) % len(all_odds) if all_odds else 0
            game_odds = all_odds[start_idx:start_idx+4] if all_odds else []
            
            game.update({
                'odds_sample': game_odds,
                'total_odds_on_page': len(all_odds),
                'total_spreads_on_page': len(spreads),
                'total_totals_on_page': len(totals),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return games

def create_summary_data(games: List[Dict]) -> Dict:
    """Create a summary of the scraped data"""
    if not games:
        return {'error': 'No games found'}
    
    return {
        'total_games': len(games),
        'source': 'DraftKings',
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'sample_games': [
            {
                'matchup': game['matchup'],
                'odds_sample': game.get('odds_sample', [])
            }
            for game in games[:5]  # First 5 games
        ],
        'all_games': games
    }

def main():
    """Test the working scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("Testing working DraftKings scraper...")
    
    scraper = WorkingDraftKingsScraper(headless=True)
    games = scraper.scrape_nfl_odds()
    
    if games:
        logger.info(f"Successfully scraped {len(games)} games")
        
        # Show sample results
        for i, game in enumerate(games[:5]):
            logger.info(f"Game {i+1}: {game['matchup']}")
            logger.info(f"  Sample odds: {game.get('odds_sample', [])}")
        
        # Create summary
        summary = create_summary_data(games)
        
        # Save results
        output_file = "data/working_draftkings_odds.json"
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Results saved to {output_file}")
        
        # Print summary
        logger.info(f"SUMMARY: {summary['total_games']} games found")
        if 'all_games' in summary and summary['all_games']:
            first_game = summary['all_games'][0]
            logger.info(f"Total odds found on page: {first_game.get('total_odds_on_page', 0)}")
        
    else:
        logger.warning("No games found")

if __name__ == "__main__":
    main()

