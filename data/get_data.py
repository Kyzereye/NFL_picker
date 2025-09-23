#!/usr/bin/env python3
"""
UPDATED NFL Data Scraper - Now uses the new modular architecture
This file has been updated to use the new scraper.py module for better efficiency and maintainability.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import ScrapingManager, ScrapeConfig
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_2025_week4_config():
    """Create configuration for scraping 2025 week 4 data"""
    return ScrapeConfig(
        season="2025",
        weeks=[4],
        base_url_pattern="https://www.espn.com/espn/betting/story/_/id/{story_id}/2025-nfl-week-{week}-schedule-odds-betting-point-spreads",
        output_file="nfl_2025_week4.json",
        story_ids={
            4: "46303232"
        }
    )

def main():
    """Main function - updated to use new scraper"""
    print("=" * 60)
    print("NFL DATA SCRAPER - UPDATED VERSION")
    print("=" * 60)
    print("This script now uses the new modular scraper architecture.")
    print("For more advanced features, use: python ../scraper.py")
    print("=" * 60)
    
    # Create configuration for current scraping task
    config = create_2025_week4_config()
    
    logger.info(f"Starting scrape for {config.season} season, weeks: {config.weeks}")
    
    # Run the scraping
    success = ScrapingManager.run_scraping(config)
    
    if success:
        print(f"\n✅ SUCCESS: Data scraped and saved to {config.output_file}")
        print("\nNext steps:")
        print("1. Check the generated JSON file")
        print("2. Update the main app data files if needed")
        print("3. Run the Flask app: python ../main.py")
    else:
        print("\n❌ FAILED: Scraping was not successful")
        print("Check the logs for more details")

# Legacy functions kept for compatibility (but now deprecated)
def scrape_fpi_and_moneyline_data(url):
    """
    DEPRECATED: Use the new scraper.py module instead
    This function is kept for backward compatibility only.
    """
    logger.warning("Using deprecated function. Please migrate to the new scraper.py module")
    from scraper import NFLDataScraper, ScrapeConfig
    import re
    
    # Extract story ID and week from URL
    story_match = re.search(r'/id/(\d+)/', url)
    week_match = re.search(r'week-?(\d+)', url, re.IGNORECASE)
    
    if not story_match or not week_match:
        logger.error("Could not extract story ID or week from URL")
        return None
    
    story_id = story_match.group(1)
    week = int(week_match.group(1))
    
    # Create temporary config
    config = ScrapeConfig(
        season="2025",
        weeks=[week],
        base_url_pattern="",
        output_file="temp.json",
        story_ids={week: story_id}
    )
    
    scraper = NFLDataScraper(config)
    return scraper.scrape_week_data(week, story_id)

def clean_and_format_data(raw_data_list, week_number):
    """
    DEPRECATED: Use models.GameDataProcessor.clean_and_format_raw_data instead
    This function is kept for backward compatibility only.
    """
    logger.warning("Using deprecated function. Please migrate to models.GameDataProcessor")
    from models import GameDataProcessor
    return GameDataProcessor.clean_and_format_raw_data(raw_data_list, week_number, "2025")

if __name__ == "__main__":
    main()

# LEGACY CODE SECTION - DEPRECATED
# The following code is kept for reference but should not be used
# Use the new scraper.py module instead

"""
# Old URL list - now handled by configuration
urls_to_scrape = [
    'https://www.espn.com/espn/betting/story/_/id/46303232/2025-nfl-week-4-schedule-odds-betting-point-spreads'
]

# Old scraping loop - replaced by ScrapingManager
all_data = []
for url in urls_to_scrape:
    raw_data_list = scrape_fpi_and_moneyline_data(url)
    week_match = re.search(r'week-(\d+)', url)
    week_number = int(week_match.group(1)) if week_match else 0
    
    print(f"\n--- Week {week_number} Raw Data ---")
    if raw_data_list:
        for game in raw_data_list:
            print(game)
        
        cleaned_week_data = clean_and_format_data(raw_data_list, week_number)
        all_data.append(cleaned_week_data)
    else:
        print(f"No moneyline or FPI data found for Week {week_number}.")

output_file = 'nfl_2025_week4.json'
with open(output_file, 'w') as f:
    json.dump(all_data, f, indent=2)

print(f"\nAll data successfully scraped and saved to {output_file}.")
"""