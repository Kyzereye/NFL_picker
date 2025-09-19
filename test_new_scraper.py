#!/usr/bin/env python3
"""
Test script to demonstrate the new DraftKings scraping capability
"""

import sys
import os
import logging
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_scraper import UnifiedScraper, UnifiedScrapeConfig, DataSource, MultiSourceScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_draftkings_scraper():
    """Test the DraftKings scraper"""
    logger.info("=== Testing DraftKings Scraper ===")
    
    # Create DraftKings scraper configuration
    config = UnifiedScrapeConfig(
        source=DataSource.DRAFTKINGS,
        season="2025",
        week=3,
        output_file="data/test_draftkings_odds.json",
        headless=True
    )
    
    # Create and run scraper
    scraper = UnifiedScraper(config)
    
    try:
        logger.info("Starting DraftKings odds scraping...")
        results = scraper.scrape_odds()
        
        if results:
            logger.info(f"Successfully scraped {len(results)} data entries from DraftKings")
            
            # Save results
            with open(config.output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {config.output_file}")
            
            # Display summary
            for i, result in enumerate(results):
                logger.info(f"Entry {i+1}: {result.get('source', 'Unknown')} - {result.get('total_games', 0)} games")
                if 'games' in result:
                    for j, game in enumerate(result['games'][:3]):  # Show first 3 games
                        teams = game.get('teams_found', [])
                        odds = game.get('odds_found', [])
                        logger.info(f"  Game {j+1}: Teams: {teams}, Odds: {odds[:4]}")
        else:
            logger.warning("No results returned from DraftKings scraper")
            
    except Exception as e:
        logger.error(f"Error testing DraftKings scraper: {e}")

def test_multi_source_scraper():
    """Test the multi-source scraper"""
    logger.info("\n=== Testing Multi-Source Scraper ===")
    
    multi_scraper = MultiSourceScraper()
    
    try:
        logger.info("Starting multi-source scraping (Week 3, 2025)...")
        all_results = multi_scraper.scrape_all_sources(week=3, season="2025")
        
        output_file = "data/test_combined_odds.json"
        success = multi_scraper.save_combined_results(all_results, output_file)
        
        if success:
            logger.info(f"Combined results saved to {output_file}")
        else:
            logger.error("Failed to save combined results")
        
        # Display summary
        for source, data in all_results.items():
            logger.info(f"{source.upper()}: {len(data)} entries")
            if data:
                first_entry = data[0]
                games_count = first_entry.get('total_games', len(first_entry.get('games', [])))
                logger.info(f"  First entry has {games_count} games")
                
    except Exception as e:
        logger.error(f"Error testing multi-source scraper: {e}")

def show_current_data():
    """Show what data we currently have"""
    logger.info("\n=== Current Data Files ===")
    
    data_dir = "/home/jeff/Projects/study/NFL/data"
    if os.path.exists(data_dir):
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        logger.info(f"Found {len(data_files)} JSON data files:")
        
        for file in sorted(data_files):
            file_path = os.path.join(data_dir, file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    logger.info(f"  {file}: {len(data)} entries (list)")
                elif isinstance(data, dict):
                    logger.info(f"  {file}: {len(data)} keys (dict)")
                    if 'sources' in data:
                        logger.info(f"    Multi-source file with sources: {list(data['sources'].keys())}")
                else:
                    logger.info(f"  {file}: {type(data)}")
                    
            except Exception as e:
                logger.info(f"  {file}: Error reading - {e}")
    else:
        logger.info("Data directory not found")

def main():
    """Main test function"""
    logger.info("Starting NFL Odds Scraper Tests")
    logger.info("=" * 50)
    
    # Show current data
    show_current_data()
    
    # Test DraftKings scraper
    test_draftkings_scraper()
    
    # Test multi-source scraper
    test_multi_source_scraper()
    
    logger.info("\n" + "=" * 50)
    logger.info("All tests completed!")
    
    # Show updated data
    show_current_data()

if __name__ == "__main__":
    main()

