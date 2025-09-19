"""
Refactored NFL Data Flask Application
- Eliminates code duplication
- Implements caching for better performance
- Uses data models for consistency
- Centralized error handling
"""

from flask import Flask, render_template, jsonify
from config import Config, SeasonConfig
from models import Season
from utils import cached, load_json_file, get_data_file_path, ErrorHandler, setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

def season_cache_key(season: str):
    """Generate cache key for season data"""
    return f"season_data_{season}"

@cached(cache_key_func=season_cache_key)
def load_season_data(season: str) -> dict:
    """Load and process season data with caching"""
    try:
        filepath = get_data_file_path(season)
        data = load_json_file(filepath)
        
        if data is None:
            raise FileNotFoundError(f"Could not load data for season {season}")
        
        # Load data using the Season model which handles processing
        season_obj = Season.from_json_file(filepath)
        return season_obj.to_dict()
        
    except FileNotFoundError:
        logger.error(f"Season data file not found for {season}")
        raise
    except Exception as e:
        logger.error(f"Error loading season data for {season}: {e}")
        raise

@app.route("/")
def index():
    """Home page"""
    return render_template("home.html")

@app.route("/<season>/")
def season_view(season: str):
    """Generic season view handler"""
    try:
        # Validate season
        if season not in SeasonConfig.SEASONS:
            return f"Error: Season {season} not supported.", 404
        
        if not SeasonConfig.SEASONS[season]['active']:
            return f"Error: Season {season} is not active.", 404
        
        # Load season data (cached)
        season_data = load_season_data(season)
        
        # Determine template name
        template_name = f"season_{season}.html"
        
        return render_template(template_name, 
                             season_data=season_data,
                             season_info=SeasonConfig.SEASONS[season])
    
    except FileNotFoundError:
        return ErrorHandler.handle_file_not_found(season)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e, f"loading {season} season")

@app.route("/api/season/<season>")
def api_season_data(season: str):
    """API endpoint for season data"""
    try:
        if season not in SeasonConfig.SEASONS:
            return jsonify({"error": f"Season {season} not supported"}), 404
        
        season_data = load_season_data(season)
        return jsonify({
            "season": season,
            "data": season_data,
            "info": SeasonConfig.SEASONS[season]
        })
    
    except FileNotFoundError:
        return jsonify({"error": f"Data file not found for season {season}"}), 404
    except Exception as e:
        logger.error(f"API error for season {season}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/seasons")
def api_available_seasons():
    """API endpoint for available seasons"""
    active_seasons = {
        season: info for season, info in SeasonConfig.SEASONS.items()
        if info['active']
    }
    return jsonify({"seasons": active_seasons})

@app.errorhandler(404)
def not_found(error):
    """Custom 404 handler"""
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {error}")
    return render_template("500.html"), 500

# Legacy route redirects for backward compatibility
@app.route("/2023/")
def season2023():
    """Redirect to generic season view"""
    return season_view("2023")

@app.route("/2024/")
def season2024():
    """Redirect to generic season view"""
    return season_view("2024")

@app.route("/2025/")
def season2025():
    """Redirect to generic season view"""
    return season_view("2025")

if __name__ == "__main__":
    logger.info("Starting NFL Data Application")
    app.run(debug=Config.DEBUG)