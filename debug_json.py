#!/usr/bin/env python3
"""
Debug script to examine DraftKings JSON structure
"""

import sys
import os
import json
import re
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from draftkings_parser import DraftKingsParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def explore_json_structure(data, path="", max_depth=3, current_depth=0):
    """Recursively explore JSON structure"""
    if current_depth >= max_depth:
        return
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                if value:  # Non-empty dict
                    logger.info(f"{new_path}: dict with {len(value)} keys: {list(value.keys())[:5]}...")
                    explore_json_structure(value, new_path, max_depth, current_depth + 1)
                else:
                    logger.info(f"{new_path}: empty dict")
            elif isinstance(value, list):
                logger.info(f"{new_path}: list with {len(value)} items")
                if value and current_depth < max_depth - 1:
                    logger.info(f"{new_path}[0]: {type(value[0])}")
                    if isinstance(value[0], dict):
                        explore_json_structure(value[0], f"{new_path}[0]", max_depth, current_depth + 1)
            else:
                logger.info(f"{new_path}: {type(value)} = {str(value)[:100]}...")

def search_for_teams(data, teams=['Bills', 'Dolphins', 'Chiefs', 'Ravens']):
    """Search for team names in the data structure"""
    found_items = []
    
    def search_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                search_recursive(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_recursive(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            for team in teams:
                if team.lower() in obj.lower():
                    found_items.append({
                        'path': path,
                        'text': obj[:200],
                        'team_found': team
                    })
                    break
    
    search_recursive(data)
    return found_items

def search_for_odds(data):
    """Search for odds-like patterns in the data"""
    found_items = []
    odds_pattern = re.compile(r'[+-]\d{2,4}')
    
    def search_recursive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                search_recursive(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_recursive(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            if odds_pattern.search(obj):
                found_items.append({
                    'path': path,
                    'text': obj[:200]
                })
        elif isinstance(obj, (int, float)):
            # Check if it looks like odds
            if isinstance(obj, int) and (100 <= abs(obj) <= 9999):
                found_items.append({
                    'path': path,
                    'value': obj
                })
    
    search_recursive(data)
    return found_items

def main():
    """Debug the JSON structure"""
    parser = DraftKingsParser()
    
    html_file = '/home/jeff/Projects/study/NFL/draftkings_selenium.html'
    if not os.path.exists(html_file):
        logger.error(f"HTML file not found: {html_file}")
        return
    
    logger.info(f"Reading HTML from {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract JSON
    json_data = parser.extract_json_from_html(html_content)
    
    if not json_data:
        logger.error("Failed to extract JSON data")
        return
    
    logger.info("=== JSON Structure Exploration ===")
    explore_json_structure(json_data, max_depth=2)
    
    logger.info("\n=== Searching for Team Names ===")
    team_findings = search_for_teams(json_data)
    for finding in team_findings[:10]:  # Show first 10
        logger.info(f"Found '{finding['team_found']}' at {finding['path']}: {finding['text'][:100]}...")
    
    logger.info(f"Total team name findings: {len(team_findings)}")
    
    logger.info("\n=== Searching for Odds ===")
    odds_findings = search_for_odds(json_data)
    for finding in odds_findings[:10]:  # Show first 10
        if 'text' in finding:
            logger.info(f"Found odds pattern at {finding['path']}: {finding['text'][:100]}...")
        else:
            logger.info(f"Found odds value at {finding['path']}: {finding['value']}")
    
    logger.info(f"Total odds findings: {len(odds_findings)}")
    
    # Check specific keys that might contain game data
    interesting_keys = ['sports', 'featured', 'content', 'stadiumEventData', 'stadiumLeagueData', 'wildcardLiveData']
    
    logger.info("\n=== Examining Interesting Keys ===")
    for key in interesting_keys:
        if key in json_data:
            data = json_data[key]
            logger.info(f"{key}: {type(data)}")
            if isinstance(data, dict) and data:
                logger.info(f"  Keys: {list(data.keys())[:5]}...")
                explore_json_structure(data, key, max_depth=1)
            elif isinstance(data, list) and data:
                logger.info(f"  Length: {len(data)}")
                logger.info(f"  First item type: {type(data[0])}")

if __name__ == "__main__":
    main()

