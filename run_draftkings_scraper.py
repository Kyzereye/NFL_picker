#!/usr/bin/env python3
"""
DraftKings NFL Odds Scraper - Main Script
Usage: python3 run_draftkings_scraper.py
"""

import sys
import os
import logging
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_scraper import UnifiedScraper, UnifiedScrapeConfig, DataSource, MultiSourceScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nfl_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def scrape_draftkings_only():
    """Scrape odds from DraftKings only"""
    logger.info("Starting DraftKings NFL odds scraping...")
    
    config = UnifiedScrapeConfig(
        source=DataSource.DRAFTKINGS,
        season="2025",
        week=3,  # Current week
        output_file=f"data/draftkings_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        headless=True
    )
    
    scraper = UnifiedScraper(config)
    
    try:
        results = scraper.scrape_odds()
        
        if results:
            logger.info(f"✅ Successfully scraped {len(results)} data entries from DraftKings")
            
            # Display summary
            for entry in results:
                games = entry.get('games', [])
                logger.info(f"📊 Found {len(games)} games with odds data")
                
                for i, game in enumerate(games[:5]):  # Show first 5 games
                    teams = game.get('teams_found', [])
                    odds = game.get('odds_found', [])
                    if teams:
                        logger.info(f"  🏈 Game {i+1}: {' vs '.join(teams)} - Odds: {odds[:4]}")
            
            return True
        else:
            logger.warning("❌ No data returned from DraftKings")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error scraping DraftKings: {e}")
        return False

def scrape_all_sources():
    """Scrape from both DraftKings and ESPN"""
    logger.info("Starting multi-source NFL odds scraping...")
    
    multi_scraper = MultiSourceScraper()
    
    try:
        # Scrape from all sources
        all_results = multi_scraper.scrape_all_sources(week=3, season="2025")
        
        # Save combined results
        output_file = f"data/combined_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        success = multi_scraper.save_combined_results(all_results, output_file)
        
        if success:
            logger.info(f"✅ Combined results saved to {output_file}")
            
            # Display summary
            total_games = 0
            for source, data in all_results.items():
                if data:
                    entry = data[0]
                    games_count = entry.get('total_games', len(entry.get('games', [])))
                    total_games += games_count
                    logger.info(f"📊 {source.upper()}: {games_count} games")
                else:
                    logger.info(f"📊 {source.upper()}: No data")
            
            logger.info(f"🎯 Total games across all sources: {total_games}")
            return True
        else:
            logger.error("❌ Failed to save combined results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in multi-source scraping: {e}")
        return False

def main():
    """Main function"""
    print("🏈 NFL Odds Scraper - DraftKings Integration")
    print("=" * 50)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    choice = input("\nChoose scraping mode:\n1. DraftKings only\n2. All sources (DraftKings + ESPN)\nEnter choice (1 or 2): ")
    
    if choice == "1":
        success = scrape_draftkings_only()
    elif choice == "2":
        success = scrape_all_sources()
    else:
        print("❌ Invalid choice. Please enter 1 or 2.")
        return
    
    if success:
        print("\n✅ Scraping completed successfully!")
        print("📁 Check the 'data' directory for output files.")
    else:
        print("\n❌ Scraping failed. Check the logs for details.")

if __name__ == "__main__":
    main()

