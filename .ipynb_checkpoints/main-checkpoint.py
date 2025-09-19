import json
from flask import Flask, render_template

app = Flask(__name__)

def calculate_odds_difference(odds):
    odds_values = list(odds.values())
    if len(odds_values) == 2:
        try:
            odds1 = int(odds_values[0].replace('+', ''))
            odds2 = int(odds_values[1].replace('+', '').replace('-', ''))
            return abs(odds1) + abs(odds2)
        except (ValueError, KeyError):
            return 0
    return 0

def normalize_team_name(name):
    """Normalizes team names for consistent comparison."""
    return name.lower().replace(" ", "")

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/2024/")
def season2024():
    try:
        with open('data/nfl_2024.json', 'r') as f:
            # Load the data directly, as the file is a list of week objects
            season_data = json.load(f)
            
            # Sort the games within each week
            for week in season_data:
                # Add odds_difference and check if the favorite won
                for game in week['games']:
                    game['odds_difference'] = calculate_odds_difference(game['moneyline_odds'])
                    
                    # Normalize names for comparison
                    normalized_favorite = normalize_team_name(game.get('favorite', ''))
                    normalized_winner = normalize_team_name(game.get('winner', ''))

                    # Check if the normalized winner contains the normalized favorite
                    game['favorite_won'] = normalized_favorite in normalized_winner
                    
                # Sort the games list within the current week
                week['games'] = sorted(week['games'], key=lambda x: x['odds_difference'], reverse=True)
            
            return render_template("season_2024.html", season_data=season_data)
    except FileNotFoundError:
        return "Error: nfl_2024.json not found.", 404

@app.route("/2025/")
def season2025():
    try:
        with open('data/nfl_2025.json', 'r') as f:
            season_data = json.load(f)
            
            for week in season_data:
                for game in week['games']:
                    game['odds_difference'] = calculate_odds_difference(game['moneyline_odds'])
                    
                    # Normalize names for comparison
                    normalized_favorite = normalize_team_name(game.get('favorite', ''))
                    normalized_winner = normalize_team_name(game.get('winner', ''))
                    
                    # Check if the normalized winner contains the normalized favorite
                    game['favorite_won'] = normalized_favorite in normalized_winner
                    
                week['games'] = sorted(week['games'], key=lambda x: x['odds_difference'], reverse=True)
            
            return render_template("season_2025.html", season_data=season_data)
    except FileNotFoundError:
        return "Error: nfl_2025.json not found. Please ensure it is in the 'data' directory.", 404

if __name__ == "__main__":
    app.run(debug=True)