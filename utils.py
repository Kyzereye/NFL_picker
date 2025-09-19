"""
Utility functions for the NFL application
"""
import os
import json
import time
from typing import Dict, Any, Optional
from functools import wraps
import logging
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleCache:
    """Simple in-memory cache with timeout"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() - entry['timestamp'] > Config.CACHE_TIMEOUT:
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for key: {key}")
        return entry['data']
    
    def set(self, key: str, value: Any):
        """Set value in cache with timestamp"""
        self._cache[key] = {
            'data': value,
            'timestamp': time.time()
        }
        logger.debug(f"Cache set for key: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        logger.info("Cache cleared")

# Global cache instance
cache = SimpleCache()

def cached(cache_key_func=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not Config.ENABLE_CACHING:
                return func(*args, **kwargs)
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        return wrapper
    return decorator

def file_exists(filepath: str) -> bool:
    """Check if file exists"""
    return os.path.exists(filepath)

def load_json_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Load JSON file with error handling"""
    try:
        if not file_exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Successfully loaded: {filepath}")
        return data
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None

def save_json_file(data: Any, filepath: str, indent: int = 2) -> bool:
    """Save data to JSON file with error handling"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=indent)
        
        logger.info(f"Successfully saved: {filepath}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False

def get_data_file_path(season: str) -> str:
    """Get the full path to a season's data file"""
    from config import SeasonConfig
    
    if season not in SeasonConfig.SEASONS:
        raise ValueError(f"Unknown season: {season}")
    
    filename = SeasonConfig.SEASONS[season]['file']
    return os.path.join(Config.DATA_DIR, filename)

def validate_season_data(data: Any) -> bool:
    """Validate season data structure"""
    if not isinstance(data, list):
        return False
    
    for week_data in data:
        if not isinstance(week_data, dict):
            return False
        
        required_keys = ['season', 'week', 'games']
        if not all(key in week_data for key in required_keys):
            return False
        
        if not isinstance(week_data['games'], list):
            return False
        
        for game in week_data['games']:
            if not isinstance(game, dict):
                return False
            
            game_required_keys = ['matchup', 'moneyline_odds', 'favorite']
            if not all(key in game for key in game_required_keys):
                return False
    
    return True

def setup_logging(log_level: str = "INFO"):
    """Setup application logging"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('nfl_app.log'),
            logging.StreamHandler()
        ]
    )

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_file_not_found(season: str) -> tuple:
        """Handle file not found errors"""
        error_msg = f"Error: NFL data for {season} season not found. Please ensure the data file is in the 'data' directory."
        logger.error(error_msg)
        return error_msg, 404
    
    @staticmethod
    def handle_invalid_data(season: str) -> tuple:
        """Handle invalid data format errors"""
        error_msg = f"Error: Invalid data format for {season} season."
        logger.error(error_msg)
        return error_msg, 500
    
    @staticmethod
    def handle_generic_error(error: Exception, context: str = "") -> tuple:
        """Handle generic errors"""
        error_msg = f"An error occurred{': ' + context if context else ''}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, 500
