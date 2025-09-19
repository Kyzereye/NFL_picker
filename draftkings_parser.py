#!/usr/bin/env python3
"""
DraftKings JSON Data Parser
Extracts and parses odds data from DraftKings NFL pages
"""

import sys
import os
import json
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

logger = logging.getLogger(__name__)

@dataclass
class NFLGame:
    """Structured NFL game data"""
    home_team: str
    away_team: str
    game_time: str
    moneyline_home: Optional[str] = None
    moneyline_away: Optional[str] = None
    spread_home: Optional[str] = None
    spread_away: Optional[str] = None
    spread_points: Optional[str] = None
    total_over: Optional[str] = None
    total_under: Optional[str] = None
    total_points: Optional[str] = None

class DraftKingsParser:
    """Parser for DraftKings JSON data"""
    
    def __init__(self):
        self.team_name_mapping = self._create_team_mapping()
    
    def _create_team_mapping(self) -> Dict[str, str]:
        """Create mapping for team name variations"""
        return {
            'buf': 'Buffalo Bills',
            'mia': 'Miami Dolphins',
            'ne': 'New England Patriots',
            'nyj': 'New York Jets',
            'bal': 'Baltimore Ravens',
            'cin': 'Cincinnati Bengals',
            'cle': 'Cleveland Browns',
            'pit': 'Pittsburgh Steelers',
            'hou': 'Houston Texans',
            'ind': 'Indianapolis Colts',
            'jax': 'Jacksonville Jaguars',
            'ten': 'Tennessee Titans',
            'den': 'Denver Broncos',
            'kc': 'Kansas City Chiefs',
            'lv': 'Las Vegas Raiders',
            'lac': 'Los Angeles Chargers',
            'dal': 'Dallas Cowboys',
            'nyg': 'New York Giants',
            'phi': 'Philadelphia Eagles',
            'was': 'Washington Commanders',
            'chi': 'Chicago Bears',
            'det': 'Detroit Lions',
            'gb': 'Green Bay Packers',
            'min': 'Minnesota Vikings',
            'atl': 'Atlanta Falcons',
            'car': 'Carolina Panthers',
            'no': 'New Orleans Saints',
            'tb': 'Tampa Bay Buccaneers',
            'ari': 'Arizona Cardinals',
            'lar': 'Los Angeles Rams',
            'sf': 'San Francisco 49ers',
            'sea': 'Seattle Seahawks'
        }
    
    def extract_json_from_html(self, html_content: str) -> Optional[Dict]:
        """Extract JSON data from HTML content"""
        try:
            # Look for the main state object
            pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                logger.warning("Could not find __INITIAL_STATE__ in HTML")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return None
    
    def parse_games_from_json(self, json_data: Dict) -> List[NFLGame]:
        """Parse NFL games from JSON data structure"""
        games = []
        
        try:
            # Navigate through the JSON structure to find events and markets
            if 'eventGroups' in json_data:
                event_groups = json_data['eventGroups']
                logger.info(f"Found {len(event_groups)} event groups")
                
                for group_id, group_data in event_groups.items():
                    if isinstance(group_data, dict) and 'events' in group_data:
                        for event_id, event_data in group_data['events'].items():
                            game = self._parse_single_event(event_data, json_data)
                            if game:
                                games.append(game)
            
            # Alternative: look in events directly
            if 'events' in json_data and not games:
                events = json_data['events']
                logger.info(f"Found {len(events)} events directly")
                
                for event_id, event_data in events.items():
                    game = self._parse_single_event(event_data, json_data)
                    if game:
                        games.append(game)
            
            # Try to find events in offers structure
            if 'offers' in json_data and not games:
                offers = json_data['offers']
                logger.info(f"Found {len(offers)} offers")
                
                # Group offers by event
                events_from_offers = {}
                for offer_id, offer_data in offers.items():
                    if isinstance(offer_data, dict) and 'eventId' in offer_data:
                        event_id = offer_data['eventId']
                        if event_id not in events_from_offers:
                            events_from_offers[event_id] = []
                        events_from_offers[event_id].append(offer_data)
                
                for event_id, event_offers in events_from_offers.items():
                    game = self._parse_event_from_offers(event_id, event_offers, json_data)
                    if game:
                        games.append(game)
                        
        except Exception as e:
            logger.error(f"Error parsing games from JSON: {e}")
        
        logger.info(f"Successfully parsed {len(games)} games")
        return games
    
    def _parse_single_event(self, event_data: Dict, full_json: Dict) -> Optional[NFLGame]:
        """Parse a single event into an NFLGame object"""
        try:
            if not isinstance(event_data, dict):
                return None
            
            # Extract basic event info
            event_name = event_data.get('name', '')
            start_time = event_data.get('startTime', '')
            
            # Try to extract team names from event name or participants
            teams = self._extract_teams_from_event(event_data)
            if len(teams) < 2:
                return None
            
            # Create game object
            game = NFLGame(
                home_team=teams[0],
                away_team=teams[1],
                game_time=start_time
            )
            
            # Try to find associated markets/odds
            self._add_odds_to_game(game, event_data, full_json)
            
            return game
            
        except Exception as e:
            logger.error(f"Error parsing single event: {e}")
            return None
    
    def _parse_event_from_offers(self, event_id: str, offers: List[Dict], full_json: Dict) -> Optional[NFLGame]:
        """Parse an event from its offers"""
        try:
            # Try to find event details in the main events section
            event_data = None
            if 'events' in full_json and event_id in full_json['events']:
                event_data = full_json['events'][event_id]
            
            if not event_data:
                # Try to construct from offers
                first_offer = offers[0] if offers else {}
                event_name = first_offer.get('label', '')
                
                teams = self._extract_teams_from_text(event_name)
                if len(teams) < 2:
                    return None
                
                game = NFLGame(
                    home_team=teams[0],
                    away_team=teams[1],
                    game_time=first_offer.get('startTime', '')
                )
            else:
                teams = self._extract_teams_from_event(event_data)
                if len(teams) < 2:
                    return None
                
                game = NFLGame(
                    home_team=teams[0],
                    away_team=teams[1],
                    game_time=event_data.get('startTime', '')
                )
            
            # Add odds from offers
            self._add_odds_from_offers(game, offers, full_json)
            
            return game
            
        except Exception as e:
            logger.error(f"Error parsing event from offers: {e}")
            return None
    
    def _extract_teams_from_event(self, event_data: Dict) -> List[str]:
        """Extract team names from event data"""
        teams = []
        
        # Try participants first
        if 'participants' in event_data:
            for participant in event_data['participants']:
                if isinstance(participant, dict) and 'name' in participant:
                    teams.append(participant['name'])
        
        # Try event name
        if not teams and 'name' in event_data:
            teams = self._extract_teams_from_text(event_data['name'])
        
        # Normalize team names
        normalized_teams = []
        for team in teams:
            normalized = self._normalize_team_name(team)
            if normalized:
                normalized_teams.append(normalized)
        
        return normalized_teams
    
    def _extract_teams_from_text(self, text: str) -> List[str]:
        """Extract team names from text using patterns"""
        # Common patterns: "Team A vs Team B", "Team A @ Team B"
        patterns = [
            r'(.+?)\s+vs\s+(.+)',
            r'(.+?)\s+@\s+(.+)',
            r'(.+?)\s+-\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return [match.group(1).strip(), match.group(2).strip()]
        
        return []
    
    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to full name"""
        # Clean the name
        clean_name = team_name.strip().lower()
        
        # Check direct mapping
        if clean_name in self.team_name_mapping:
            return self.team_name_mapping[clean_name]
        
        # Check if it's already a full name
        for full_name in self.team_name_mapping.values():
            if clean_name in full_name.lower() or full_name.lower() in clean_name:
                return full_name
        
        # Return as-is if we can't map it
        return team_name.title()
    
    def _add_odds_to_game(self, game: NFLGame, event_data: Dict, full_json: Dict):
        """Add odds information to game from event data"""
        # This would need to be implemented based on the actual structure
        # For now, we'll leave it as a placeholder
        pass
    
    def _add_odds_from_offers(self, game: NFLGame, offers: List[Dict], full_json: Dict):
        """Add odds information to game from offers"""
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            
            # Try to identify the type of bet
            label = offer.get('label', '').lower()
            
            if 'moneyline' in label or 'money line' in label:
                # Handle moneyline odds
                pass
            elif 'spread' in label or 'point spread' in label:
                # Handle spread odds
                pass
            elif 'total' in label or 'over/under' in label:
                # Handle total odds
                pass

def main():
    """Test the parser"""
    logging.basicConfig(level=logging.INFO)
    
    parser = DraftKingsParser()
    
    # Try to read the saved HTML file
    html_file = '/home/jeff/Projects/study/NFL/draftkings_selenium.html'
    if os.path.exists(html_file):
        logger.info(f"Reading HTML from {html_file}")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract JSON
        json_data = parser.extract_json_from_html(html_content)
        
        if json_data:
            logger.info("Successfully extracted JSON data")
            logger.info(f"Top-level keys: {list(json_data.keys())}")
            
            # Parse games
            games = parser.parse_games_from_json(json_data)
            
            if games:
                logger.info(f"Found {len(games)} games:")
                for i, game in enumerate(games):
                    logger.info(f"Game {i+1}: {game.away_team} @ {game.home_team} at {game.game_time}")
            else:
                logger.warning("No games found in parsed data")
                
                # Debug: show structure
                if 'eventGroups' in json_data:
                    logger.info(f"EventGroups keys: {list(json_data['eventGroups'].keys())}")
                if 'events' in json_data:
                    logger.info(f"Events count: {len(json_data['events'])}")
                if 'offers' in json_data:
                    logger.info(f"Offers count: {len(json_data['offers'])}")
        else:
            logger.error("Failed to extract JSON data")
    else:
        logger.error(f"HTML file not found: {html_file}")

if __name__ == "__main__":
    main()

