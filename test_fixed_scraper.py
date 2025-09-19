#!/usr/bin/env python3
"""
Test the fixed DraftKings scraper and compare with ESPN
"""

import sys
import os
import json
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from working_draftkings_scraper import WorkingDraftKingsScraper, create_summary_data
from scraper import NFLDataScraper, ScrapeConfig
from utils import save_json_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_draftkings():
    """Test the working DraftKings scraper"""
    logger.info("=== Testing DraftKings Scraper ===")
    
    scraper = WorkingDraftKingsScraper(headless=True)
    games = scraper.scrape_nfl_odds()
    
    if games:
        summary = create_summary_data(games)
        logger.info(f"✅ DraftKings: {summary['total_games']} games found")
        
        # Show some examples
        for game in summary['sample_games']:
            logger.info(f"  📊 {game['matchup']} - Odds: {game['odds_sample']}")
        
        return summary
    else:
        logger.error("❌ DraftKings scraper failed")
        return None

def test_espn():
    """Test the ESPN scraper for comparison"""
    logger.info("\n=== Testing ESPN Scraper ===")
    
    config = ScrapeConfig(
        season="2025",
        weeks=[3],
        base_url_pattern="",
        output_file="temp_espn.json",
        story_ids={3: "46264468"}
    )
    
    scraper = NFLDataScraper(config)
    espn_data = scraper.scrape_season()
    
    if espn_data:
        games_count = len(espn_data[0]['games']) if espn_data and 'games' in espn_data[0] else 0
        logger.info(f"✅ ESPN: {games_count} games found")
        
        # Show some examples
        if espn_data and 'games' in espn_data[0]:
            for i, game in enumerate(espn_data[0]['games'][:3]):
                matchup = game.get('matchup', 'Unknown')
                odds = game.get('moneyline_odds', {})
                logger.info(f"  📊 {matchup} - Odds: {odds}")
        
        return espn_data[0] if espn_data else None
    else:
        logger.error("❌ ESPN scraper failed")
        return None

def compare_results(dk_data, espn_data):
    """Compare DraftKings and ESPN results"""
    logger.info("\n=== COMPARISON ===")
    
    if dk_data and espn_data:
        dk_games = dk_data.get('total_games', 0)
        espn_games = len(espn_data.get('games', []))
        
        logger.info(f"🏈 DraftKings Games: {dk_games}")
        logger.info(f"🏈 ESPN Games: {espn_games}")
        logger.info(f"📈 DraftKings has {dk_games - espn_games} more games")
        
        # Check for common matchups
        dk_matchups = set()
        if 'all_games' in dk_data:
            dk_matchups = {game['matchup'].lower().replace(' ', '') for game in dk_data['all_games']}
        
        espn_matchups = set()
        if 'games' in espn_data:
            espn_matchups = {game['matchup'].lower().replace(' ', '') for game in espn_data['games']}
        
        common = len(dk_matchups.intersection(espn_matchups))
        logger.info(f"🤝 Common games found: {common}")
        
        return {
            'draftkings_games': dk_games,
            'espn_games': espn_games,
            'common_games': common,
            'draftkings_advantage': dk_games - espn_games
        }
    else:
        logger.error("❌ Cannot compare - missing data")
        return None

def main():
    """Main comparison test"""
    logger.info("🏈 NFL Odds Scraper Comparison Test")
    logger.info("=" * 50)
    
    # Test both scrapers
    dk_data = test_draftkings()
    espn_data = test_espn()
    
    # Compare results
    comparison = compare_results(dk_data, espn_data)
    
    # Save combined results
    if dk_data and espn_data:
        combined_results = {
            'timestamp': dk_data.get('scraped_at'),
            'comparison_summary': comparison,
            'draftkings_data': dk_data,
            'espn_data': espn_data
        }
        
        output_file = "data/fixed_comparison_results.json"
        with open(output_file, 'w') as f:
            json.dump(combined_results, f, indent=2)
        
        logger.info(f"\n✅ Combined results saved to {output_file}")
        logger.info("🎯 DraftKings integration is now working properly!")
    else:
        logger.error("❌ Test failed - could not get data from both sources")

if __name__ == "__main__":
    main()

