"""
Data models for NFL game data
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
import re
from config import TeamConfig

@dataclass
class MoneylineOdds:
    """Represents moneyline odds for a game"""
    team1: str
    odds1: str
    team2: str
    odds2: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format"""
        return {self.team1: self.odds1, self.team2: self.odds2}
    
    def calculate_difference(self) -> int:
        """Calculate the total odds difference"""
        try:
            odds1_val = int(self.odds1.replace('+', '').replace('-', ''))
            odds2_val = int(self.odds2.replace('+', '').replace('-', ''))
            return abs(odds1_val) + abs(odds2_val)
        except (ValueError, AttributeError):
            return 0

@dataclass
class Game:
    """Represents a single NFL game"""
    matchup: str
    moneyline_odds: Dict[str, str]
    favorite: str
    winner: str = ""
    fpi_percentage: float = 0.0  # FPI win probability percentage
    odds_difference: int = field(init=False)
    favorite_won: bool = field(init=False)
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        self.odds_difference = self._calculate_odds_difference()
        self.favorite_won = self._check_favorite_won()
    
    def _calculate_odds_difference(self) -> int:
        """Calculate the odds difference for this game"""
        odds_values = list(self.moneyline_odds.values())
        if len(odds_values) == 2:
            try:
                odds1 = int(odds_values[0].replace('+', '').replace('-', ''))
                odds2 = int(odds_values[1].replace('+', '').replace('-', ''))
                return abs(odds1) + abs(odds2)
            except (ValueError, AttributeError):
                return 0
        return 0
    
    def _check_favorite_won(self) -> bool:
        """Check if the favorite team won the game"""
        if not self.winner or not self.favorite:
            return False
        
        # Normalize team names for comparison
        normalized_favorite = self._normalize_team_name(self.favorite)
        normalized_winner = self._normalize_team_name(self.winner)
        
        return normalized_favorite in normalized_winner
    
    @staticmethod
    def _normalize_team_name(name: str) -> str:
        """Normalize team names for consistent comparison"""
        return name.lower().replace(" ", "").replace("'", "")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization"""
        return {
            'matchup': self.matchup,
            'moneyline_odds': self.moneyline_odds,
            'favorite': self.favorite,
            'winner': self.winner,
            'fpi_percentage': self.fpi_percentage,
            'odds_difference': self.odds_difference,
            'favorite_won': self.favorite_won
        }

@dataclass
class Week:
    """Represents a week of NFL games"""
    season: str
    week: int
    games: List[Game] = field(default_factory=list)
    
    def add_game(self, game: Game):
        """Add a game to this week"""
        self.games.append(game)
    
    def sort_games_by_odds(self, reverse: bool = True):
        """Sort games by odds difference"""
        self.games.sort(key=lambda x: x.odds_difference, reverse=reverse)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization"""
        return {
            'season': self.season,
            'week': self.week,
            'games': [game.to_dict() for game in self.games]
        }

@dataclass
class Season:
    """Represents a complete NFL season"""
    year: str
    weeks: List[Week] = field(default_factory=list)
    
    def add_week(self, week: Week):
        """Add a week to this season"""
        self.weeks.append(week)
    
    def get_week(self, week_number: int) -> Optional[Week]:
        """Get a specific week by number"""
        for week in self.weeks:
            if week.week == week_number:
                return week
        return None
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries for JSON serialization"""
        return [week.to_dict() for week in self.weeks]
    
    @classmethod
    def from_json_file(cls, filepath: str) -> 'Season':
        """Load season data from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        season = cls(year=str(data[0]['season']) if data else "unknown")
        
        for week_data in data:
            week = Week(
                season=week_data['season'],
                week=week_data['week']
            )
            
            for game_data in week_data['games']:
                game = Game(
                    matchup=game_data['matchup'],
                    moneyline_odds=game_data['moneyline_odds'],
                    favorite=game_data['favorite'],
                    winner=game_data.get('winner', ''),
                    fpi_percentage=game_data.get('fpi_percentage', 0.0)
                )
                week.add_game(game)
            
            # Sort games by odds difference
            week.sort_games_by_odds()
            season.add_week(week)
        
        return season

class GameDataProcessor:
    """Utility class for processing game data"""
    
    @staticmethod
    def clean_and_format_raw_data(raw_data_list: List[Dict], week_number: int, season: str = "2025") -> Dict[str, Any]:
        """Clean and format raw scraped data"""
        cleaned_games = []
        
        for game in raw_data_list:
            fpi_favorite_string = game.get('FPI Favorite', '').strip()
            moneyline_teams = list(game.get('Money Line', {}).keys())
            fpi_percentage = game.get('FPI Percentage', 0.0)
            
            # Extract favorite name
            favorite_name = GameDataProcessor._extract_favorite_name(fpi_favorite_string)
            
            # Create matchup string
            matchup = f"{moneyline_teams[0]} @ {moneyline_teams[1]}" if len(moneyline_teams) == 2 else ""
            
            # Create game object
            game_obj = Game(
                matchup=matchup,
                moneyline_odds=game.get('Money Line', {}),
                favorite=favorite_name,
                winner="",  # Left blank for manual entry
                fpi_percentage=fpi_percentage
            )
            
            cleaned_games.append(game_obj.to_dict())
        
        return {
            "season": season,
            "week": week_number,
            "games": cleaned_games
        }
    
    @staticmethod
    def _extract_favorite_name(fpi_favorite_string: str) -> str:
        """Extract team name from FPI favorite string"""
        favorite_match = re.search(r'^(.*?)\s+by', fpi_favorite_string)
        if favorite_match:
            favorite_name_raw = favorite_match.group(1).strip()
            
            # Check for abbreviations
            if favorite_name_raw in TeamConfig.ABBREVIATION_MAP:
                return TeamConfig.ABBREVIATION_MAP[favorite_name_raw]
            else:
                return favorite_name_raw
        else:
            return fpi_favorite_string
