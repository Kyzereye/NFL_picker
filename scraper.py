"""
Modular NFL Data Scraper
- Configurable URLs and seasons
- Robust error handling and retry logic
- Extensible architecture for different data sources
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config import Config, SeasonConfig
from models import GameDataProcessor
from utils import save_json_file

logger = logging.getLogger(__name__)

@dataclass
class ScrapeConfig:
    """Configuration for scraping operations"""
    season: str
    weeks: List[int]
    base_url_pattern: str
    output_file: str
    story_ids: Dict[int, str] = None  # week -> story_id mapping
    
    def __post_init__(self):
        if self.story_ids is None:
            self.story_ids = {}

class NFLDataScraper:
    """Main scraper class with retry logic and error handling"""
    
    def __init__(self, config: ScrapeConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        
    def scrape_week_data(self, week: int, story_id: str) -> Optional[List[Dict[str, Any]]]:
        """Scrape data for a specific week with retry logic"""
        url = self._build_url(week, story_id)
        
        for attempt in range(Config.RETRY_ATTEMPTS):
            try:
                logger.info(f"Scraping week {week} (attempt {attempt + 1})")
                response = self._make_request(url)
                
                if response is None:
                    continue
                
                game_data = self._parse_page_content(response.content)
                
                if game_data:
                    logger.info(f"Successfully scraped {len(game_data)} games for week {week}")
                    return game_data
                else:
                    logger.warning(f"No game data found for week {week}")
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for week {week}: {e}")
                if attempt < Config.RETRY_ATTEMPTS - 1:
                    time.sleep(Config.RETRY_DELAY * (attempt + 1))  # Exponential backoff
        
        logger.error(f"Failed to scrape data for week {week} after {Config.RETRY_ATTEMPTS} attempts")
        return None
    
    def _build_url(self, week: int, story_id: str) -> str:
        """Build URL for specific week and story ID"""
        if self.config.season in SeasonConfig.URL_PATTERNS:
            pattern = SeasonConfig.URL_PATTERNS[self.config.season]
            return pattern.format(week=week, story_id=story_id)
        else:
            # Fallback to base pattern
            return self.config.base_url_pattern.format(week=week, story_id=story_id)
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def _parse_page_content(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse HTML content to extract game data"""
        soup = BeautifulSoup(content, 'html.parser')
        all_game_data = []
        
        # Find paragraphs containing game data
        game_sections = soup.find_all('p')
        
        for p_tag in game_sections:
            text = p_tag.get_text()
            
            # Check if paragraph contains both moneyline and FPI data
            if ('Money line' in text or 'Money Line' in text) and 'FPI favorite:' in text:
                game_data = self._extract_game_data(text)
                if game_data:
                    all_game_data.append(game_data)
        
        return all_game_data
    
    def _extract_game_data(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract game data from text using regex patterns"""
        try:
            game_data = {}
            
            # Extract FPI favorite
            fpi_pattern = re.compile(r'FPI favorite:\s*([A-Za-z\d\s\']{1,})')
            fpi_match = fpi_pattern.search(text)
            if fpi_match:
                game_data['FPI Favorite'] = fpi_match.group(1).strip()
            
            # Extract FPI percentage - handle multiple formats
            # Format 1: "66.4% probability to win outright"
            fpi_percentage_pattern1 = re.compile(r'(\d+\.?\d*)%\s+probability\s+to\s+win\s+(?:outright|the\s+game\s+outright)')
            fpi_percentage_match1 = fpi_percentage_pattern1.search(text)
            
            # Format 2: "66.4% to win outright"
            fpi_percentage_pattern2 = re.compile(r'(\d+\.?\d*)%\s+to\s+win\s+outright')
            fpi_percentage_match2 = fpi_percentage_pattern2.search(text)
            
            if fpi_percentage_match1:
                game_data['FPI Percentage'] = float(fpi_percentage_match1.group(1))
            elif fpi_percentage_match2:
                game_data['FPI Percentage'] = float(fpi_percentage_match2.group(1))
            
            # Extract moneyline data - handle both formats
            # Format 1: "Team (-300), Team (+250)" 
            moneyline_pattern1 = re.compile(r'([A-Za-z\d\s\']{2,})\s+\(([-+]\d+)\)')
            matches1 = moneyline_pattern1.findall(text)
            
            # Format 2: "Team -300, Team +250"
            moneyline_pattern2 = re.compile(r'([A-Za-z\d\s\']{2,})\s+([-+]\d+)')
            matches2 = moneyline_pattern2.findall(text)
            
            if matches1:
                odds_data = {}
                for team, odds in matches1:
                    odds_data[team.strip()] = odds.strip()
                game_data['Money Line'] = odds_data
            elif matches2:
                odds_data = {}
                for team, odds in matches2:
                    odds_data[team.strip()] = odds.strip()
                game_data['Money Line'] = odds_data
            
            # Return data only if both pieces are present
            if 'FPI Favorite' in game_data and 'Money Line' in game_data:
                return game_data
            
        except Exception as e:
            logger.error(f"Error extracting game data from text: {e}")
        
        return None
    
    def scrape_season(self) -> List[Dict[str, Any]]:
        """Scrape data for entire season"""
        all_season_data = []
        
        for week in self.config.weeks:
            story_id = self.config.story_ids.get(week)
            if not story_id:
                logger.warning(f"No story ID configured for week {week}, skipping")
                continue
            
            raw_data = self.scrape_week_data(week, story_id)
            if raw_data:
                # Clean and format the data
                cleaned_data = GameDataProcessor.clean_and_format_raw_data(
                    raw_data, week, self.config.season
                )
                all_season_data.append(cleaned_data)
                
                # Small delay between requests to be respectful
                time.sleep(1)
        
        return all_season_data

class ScrapingManager:
    """High-level manager for scraping operations"""
    
    @staticmethod
    def create_2025_config() -> ScrapeConfig:
        """Create configuration for 2025 season scraping"""
        # Load story IDs from JSON file
        story_ids = ScrapingManager.load_story_ids("2025")
        
        return ScrapeConfig(
            season="2025",
            weeks=[4],  # Default to week 4, can be overridden
            base_url_pattern="https://www.espn.com/espn/betting/story/_/id/{story_id}/2025-nfl-week-{week}-schedule-odds-betting-point-spreads",
            output_file="data/nfl_2025.json",  # Always use main file
            story_ids=story_ids
        )
    
    @staticmethod
    def load_story_ids(season: str) -> Dict[int, str]:
        """Load story IDs from JSON file"""
        try:
            with open('story_ids.json', 'r') as f:
                data = json.load(f)
            
            if season not in data:
                logger.warning(f"No story IDs found for season {season}")
                return {}
            
            # Convert string keys to integers and extract story IDs
            story_ids = {}
            for week_str, week_data in data[season]['weeks'].items():
                week_num = int(week_str)
                story_ids[week_num] = week_data['story_id']
            
            logger.info(f"Loaded story IDs for {len(story_ids)} weeks in {season}")
            return story_ids
            
        except FileNotFoundError:
            logger.error("story_ids.json file not found")
            return {}
        except Exception as e:
            logger.error(f"Error loading story IDs: {e}")
            return {}
    
    @staticmethod
    def create_config_from_urls(season: str, urls: List[str], output_file: str) -> ScrapeConfig:
        """Create configuration from list of URLs"""
        weeks = []
        story_ids = {}
        
        for url in urls:
            # Extract week number and story ID from URL
            week_match = re.search(r'week-?(\d+)', url, re.IGNORECASE)
            story_match = re.search(r'/id/(\d+)/', url)
            
            if week_match and story_match:
                week = int(week_match.group(1))
                story_id = story_match.group(1)
                weeks.append(week)
                story_ids[week] = story_id
        
        return ScrapeConfig(
            season=season,
            weeks=sorted(weeks),
            base_url_pattern="",  # Will be determined by season
            output_file=output_file,
            story_ids=story_ids
        )
    
    @staticmethod
    def run_scraping(config: ScrapeConfig) -> bool:
        """Run scraping operation with given configuration"""
        logger.info(f"Starting scraping for {config.season} season")
        logger.info(f"Weeks to scrape: {config.weeks}")
        
        scraper = NFLDataScraper(config)
        season_data = scraper.scrape_season()
        
        if season_data:
            # If output file is the main 2025 file, update it in place
            if config.output_file == "data/nfl_2025.json":
                success = ScrapingManager._update_main_file(season_data, config.weeks)
            else:
                success = save_json_file(season_data, config.output_file)
            
            if success:
                logger.info(f"Successfully updated data in {config.output_file}")
                return True
            else:
                logger.error(f"Failed to update data in {config.output_file}")
                return False
        else:
            logger.error("No data was scraped")
            return False
    
    @staticmethod
    def _update_main_file(new_data: List[Dict[str, Any]], weeks: List[int]) -> bool:
        """Update the main 2025 file with new data for specific weeks, preserving existing winners"""
        try:
            # Load existing main file
            with open("data/nfl_2025.json", 'r') as f:
                main_data = json.load(f)
            
            # Update specific weeks
            for new_week in new_data:
                week_num = new_week['week']
                for i, existing_week in enumerate(main_data):
                    if existing_week['week'] == week_num:
                        # Preserve existing winners and other data
                        ScrapingManager._merge_week_data(existing_week, new_week)
                        logger.info(f"Updated week {week_num} in main file (preserving winners)")
                        break
                else:
                    # Week not found, add it
                    main_data.append(new_week)
                    logger.info(f"Added week {week_num} to main file")
            
            # Save updated main file
            with open("data/nfl_2025.json", 'w') as f:
                json.dump(main_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating main file: {e}")
            return False
    
    @staticmethod
    def _merge_week_data(existing_week: Dict[str, Any], new_week: Dict[str, Any]) -> None:
        """Merge new week data with existing data, preserving winners and other important fields"""
        # Update basic fields
        existing_week['season'] = new_week['season']
        existing_week['week'] = new_week['week']
        
        # Create a mapping of existing games by matchup for quick lookup
        existing_games = {game['matchup']: game for game in existing_week['games']}
        
        # Update games with new data while preserving winners
        for new_game in new_week['games']:
            matchup = new_game['matchup']
            if matchup in existing_games:
                # Preserve existing winner and favorite_won
                existing_game = existing_games[matchup]
                winner = existing_game.get('winner', '')
                favorite_won = existing_game.get('favorite_won', False)
                
                # Update with new data
                existing_game.update(new_game)
                
                # Restore preserved fields
                existing_game['winner'] = winner
                existing_game['favorite_won'] = favorite_won
            else:
                # New game, add it
                existing_week['games'].append(new_game)
        
        # Sort games by odds difference
        existing_week['games'].sort(key=lambda x: x.get('odds_difference', 0), reverse=True)

def main():
    """Main function for running scraper as standalone script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NFL Data Scraper")
    parser.add_argument("--season", default="2025", help="Season to scrape")
    parser.add_argument("--weeks", nargs="+", type=int, help="Weeks to scrape")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    if args.season == "2025":
        config = ScrapingManager.create_2025_config()
        if args.weeks:
            config.weeks = args.weeks
        if args.output:
            config.output_file = args.output
    else:
        logger.error(f"Season {args.season} not yet configured")
        return
    
    success = ScrapingManager.run_scraping(config)
    if success:
        print("Scraping completed successfully!")
    else:
        print("Scraping failed!")

if __name__ == "__main__":
    main()
