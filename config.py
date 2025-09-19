"""
Configuration settings for the NFL Data Application
"""
import os
from typing import Dict, List

class Config:
    """Application configuration"""
    
    # Flask settings
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Data directories
    DATA_DIR = 'data'
    STATIC_DIR = 'static'
    TEMPLATES_DIR = 'templates'
    
    # Cache settings
    CACHE_TIMEOUT = 300  # 5 minutes
    ENABLE_CACHING = True
    
    # Scraping settings
    REQUEST_TIMEOUT = 30
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1
    
    # User agent for web scraping
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'

class SeasonConfig:
    """Season-specific configuration"""
    
    SEASONS = {
        '2023': {
            'file': 'nfl_2023_py1.json',
            'name': '2023 Season',
            'active': True
        },
        '2024': {
            'file': 'nfl_2024.json',
            'name': '2024 Season',
            'active': True
        },
        '2025': {
            'file': 'nfl_2025.json',
            'name': '2025 Season',
            'active': True
        }
    }
    
    # ESPN URL patterns for different years
    URL_PATTERNS = {
        '2023': 'https://www.espn.com/sports-betting/story/_/id/{story_id}/week-{week}-nfl-games-betting-odds-lines-picks-spreads-more',
        '2024': 'https://www.espn.com/espn/betting/story/_/id/{story_id}/week-{week}-nfl-games-betting-odds-lines-picks-spreads-more-2024-season',
        '2025': 'https://www.espn.com/espn/betting/story/_/id/{story_id}/2025-nfl-week-{week}-schedule-odds-betting-point-spreads'
    }
    
    # DraftKings URL patterns
    DRAFTKINGS_URLS = {
        'nfl_main': 'https://sportsbook.draftkings.com/leagues/football/nfl',
        'nfl_week': 'https://sportsbook.draftkings.com/leagues/football/nfl?category=game-lines&subcategory=game',
    }
    
    # Data source types
    DATA_SOURCES = {
        'ESPN': 'espn',
        'DRAFTKINGS': 'draftkings'
    }

class TeamConfig:
    """Team name mappings and abbreviations"""
    
    # Mapping for FPI abbreviations to full team names
    ABBREVIATION_MAP = {
        'A': 'Atlanta Falcons', 
        'B': 'Baltimore Ravens', 
        'C': 'Cincinnati Bengals', 
        'J': 'Jacksonville Jaguars',
        'M': 'Minnesota Vikings', 
        'N': 'New Orleans Saints', 
        'S': 'San Francisco 49ers', 
        'W': 'Washington Commanders',
        'D': 'Dallas Cowboys', 
        'P': 'New England Patriots', 
        'L': 'Los Angeles Chargers',
        'K': 'Kansas City Chiefs', 
        'H': 'Houston Texans', 
        'E': 'Philadelphia Eagles',
        '4': 'San Francisco 49ers', 
        'R': 'Las Vegas Raiders', 
        'V': 'Minnesota Vikings'
    }
    
    # Common team name variations for normalization
    TEAM_ALIASES = {
        'washington commanders': ['washington', 'commanders'],
        'las vegas raiders': ['raiders', 'las vegas'],
        'los angeles chargers': ['chargers', 'la chargers'],
        'los angeles rams': ['rams', 'la rams'],
        'new york giants': ['giants', 'ny giants'],
        'new york jets': ['jets', 'ny jets'],
        'new england patriots': ['patriots', 'new england'],
        'tampa bay buccaneers': ['buccaneers', 'bucs', 'tampa bay'],
        'green bay packers': ['packers', 'green bay'],
        'kansas city chiefs': ['chiefs', 'kc chiefs'],
        'san francisco 49ers': ['49ers', 'niners'],
    }
