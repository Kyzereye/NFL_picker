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
            if 'Money Line' in text and 'FPI favorite:' in text:
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
            
            # Extract moneyline data
            moneyline_pattern = re.compile(r'([A-Za-z\d\s\']{2,})\s+\(([-+]\d+)\)')
            matches = moneyline_pattern.findall(text)
            
            if matches:
                odds_data = {}
                for team, odds in matches:
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
        return ScrapeConfig(
            season="2025",
            weeks=[3],  # Currently configured for week 3
            base_url_pattern="https://www.espn.com/espn/betting/story/_/id/{story_id}/2025-nfl-week-{week}-schedule-odds-betting-point-spreads",
            output_file="data/nfl_2025_week3.json",
            story_ids={
                3: "46264468"  # Week 3 story ID
            }
        )
    
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
            success = save_json_file(season_data, config.output_file)
            if success:
                logger.info(f"Successfully saved data to {config.output_file}")
                return True
            else:
                logger.error(f"Failed to save data to {config.output_file}")
                return False
        else:
            logger.error("No data was scraped")
            return False

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
