"""
Unified NFL Odds Scraper
Supports multiple data sources: ESPN and DraftKings
"""

import logging
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from scraper import NFLDataScraper, ScrapeConfig
from draftkings_scraper import DraftKingsScraper, DraftKingsAPI
from config import Config, SeasonConfig
from utils import save_json_file

logger = logging.getLogger(__name__)

class DataSource(Enum):
    ESPN = "espn"
    DRAFTKINGS = "draftkings"

@dataclass
class UnifiedScrapeConfig:
    """Configuration for unified scraping operations"""
    source: DataSource
    season: str = "2025"
    week: Optional[int] = None
    output_file: str = "unified_odds_data.json"
    
    # ESPN-specific fields
    story_ids: Optional[Dict[int, str]] = None
    
    # DraftKings-specific fields
    headless: bool = True

class UnifiedScraper:
    """Main scraper that can handle multiple data sources"""
    
    def __init__(self, config: UnifiedScrapeConfig):
        self.config = config
        
    def scrape_odds(self) -> List[Dict[str, Any]]:
        """Scrape odds from the configured data source"""
        if self.config.source == DataSource.ESPN:
            return self._scrape_espn()
        elif self.config.source == DataSource.DRAFTKINGS:
            return self._scrape_draftkings()
        else:
            raise ValueError(f"Unsupported data source: {self.config.source}")
    
    def _scrape_espn(self) -> List[Dict[str, Any]]:
        """Scrape odds from ESPN using existing scraper"""
        logger.info("Scraping odds from ESPN...")
        
        if not self.config.week or not self.config.story_ids:
            raise ValueError("ESPN scraping requires week number and story_ids")
        
        # Create ESPN scrape config
        espn_config = ScrapeConfig(
            season=self.config.season,
            weeks=[self.config.week],
            base_url_pattern="",  # Will use URL_PATTERNS from config
            output_file=self.config.output_file,
            story_ids=self.config.story_ids
        )
        
        scraper = NFLDataScraper(espn_config)
        return scraper.scrape_season()
    
    def _scrape_draftkings(self) -> List[Dict[str, Any]]:
        """Scrape odds from DraftKings using selenium scraper"""
        logger.info("Scraping odds from DraftKings...")
        
        scraper = DraftKingsScraper(headless=self.config.headless)
        raw_data = scraper.scrape_nfl_odds()
        
        # Format the data to match our expected structure
        formatted_data = []
        if raw_data:
            formatted_data.append({
                'week': self.config.week or 'current',
                'season': self.config.season,
                'source': 'DraftKings',
                'games': raw_data,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_games': len(raw_data)
            })
        
        return formatted_data

class MultiSourceScraper:
    """Scraper that can fetch from multiple sources simultaneously"""
    
    def __init__(self):
        pass
    
    def scrape_all_sources(self, week: int, season: str = "2025") -> Dict[str, List[Dict[str, Any]]]:
        """Scrape from all available sources"""
        results = {}
        
        # Scrape DraftKings
        try:
            dk_config = UnifiedScrapeConfig(
                source=DataSource.DRAFTKINGS,
                season=season,
                week=week,
                output_file=f"draftkings_{season}_week{week}.json"
            )
            dk_scraper = UnifiedScraper(dk_config)
            results['draftkings'] = dk_scraper.scrape_odds()
            logger.info("Successfully scraped DraftKings data")
        except Exception as e:
            logger.error(f"Failed to scrape DraftKings: {e}")
            results['draftkings'] = []
        
        # Scrape ESPN (if story_id available)
        try:
            # Load story IDs from JSON file
            story_ids = self._load_story_ids(season)
            
            if week in story_ids:
                espn_config = UnifiedScrapeConfig(
                    source=DataSource.ESPN,
                    season=season,
                    week=week,
                    story_ids={week: story_ids[week]},
                    output_file=f"espn_{season}_week{week}.json"
                )
                espn_scraper = UnifiedScraper(espn_config)
                results['espn'] = espn_scraper.scrape_odds()
                logger.info("Successfully scraped ESPN data")
            else:
                logger.warning(f"No ESPN story ID available for week {week}")
                results['espn'] = []
        except Exception as e:
            logger.error(f"Failed to scrape ESPN: {e}")
            results['espn'] = []
        
        return results
    
    def save_combined_results(self, results: Dict[str, List[Dict[str, Any]]], output_file: str) -> bool:
        """Save combined results from all sources"""
        combined_data = {
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'sources': results,
            'summary': {
                'total_sources': len([k for k, v in results.items() if v]),
                'sources_with_data': [k for k, v in results.items() if v],
                'total_games': sum(len(v) for v in results.values() if v)
            }
        }
        
        return save_json_file(combined_data, output_file)
    
    def _load_story_ids(self, season: str) -> Dict[int, str]:
        """Load story IDs from JSON file"""
        try:
            import json
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
            
            return story_ids
            
        except FileNotFoundError:
            logger.error("story_ids.json file not found")
            return {}
        except Exception as e:
            logger.error(f"Error loading story IDs: {e}")
            return {}
    
def create_draftkings_scraper_config() -> UnifiedScrapeConfig:
    """Create a configuration for DraftKings scraping"""
    return UnifiedScrapeConfig(
        source=DataSource.DRAFTKINGS,
        season="2025",
        week=4,  # Current week
        output_file="data/draftkings_2025_week4.json",
        headless=True
    )

def main():
    """Main function for testing unified scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("Starting unified NFL odds scraper...")
    
    # Test DraftKings scraping
    logger.info("Testing DraftKings scraper...")
    dk_config = create_draftkings_scraper_config()
    dk_scraper = UnifiedScraper(dk_config)
    
    try:
        dk_data = dk_scraper.scrape_odds()
        if dk_data:
            logger.info(f"Successfully scraped DraftKings data: {len(dk_data)} entries")
            save_json_file(dk_data, dk_config.output_file)
        else:
            logger.warning("No data returned from DraftKings scraper")
    except Exception as e:
        logger.error(f"Error testing DraftKings scraper: {e}")
    
    # Test multi-source scraping
    logger.info("Testing multi-source scraper...")
    multi_scraper = MultiSourceScraper()
    
    try:
        all_results = multi_scraper.scrape_all_sources(week=4, season="2025")
        output_file = "data/combined_odds_2025_week4.json"
        
        if multi_scraper.save_combined_results(all_results, output_file):
            logger.info(f"Successfully saved combined results to {output_file}")
        else:
            logger.error("Failed to save combined results")
            
        # Print summary
        for source, data in all_results.items():
            logger.info(f"{source.upper()}: {len(data)} entries")
            
    except Exception as e:
        logger.error(f"Error testing multi-source scraper: {e}")

if __name__ == "__main__":
    main()

