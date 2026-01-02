from __future__ import annotations

from typing import Dict, Iterable, Optional

from .utils import normalize_token


def _build_alias_map(entries: Dict[str, Iterable[str]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for canonical, aliases in entries.items():
        canonical_clean = canonical.strip()
        normalized_canonical = normalize_token(canonical_clean)
        if normalized_canonical:
            mapping.setdefault(normalized_canonical, canonical_clean)
        for alias in aliases:
            normalized_alias = normalize_token(alias)
            if not normalized_alias:
                continue
            mapping.setdefault(normalized_alias, canonical_clean)
    return mapping


_NHL_TEAM_SYNONYMS: Dict[str, Iterable[str]] = {
    "Anaheim Ducks": ["Ducks", "Anaheim"],
    "Arizona Coyotes": ["Coyotes", "Arizona", "Yotes"],
    "Boston Bruins": ["Bruins", "Boston", "BOS"],
    "Buffalo Sabres": ["Sabres", "Buffalo"],
    "Calgary Flames": ["Flames", "Calgary"],
    "Carolina Hurricanes": ["Hurricanes", "Canes", "Carolina"],
    "Chicago Blackhawks": ["Blackhawks", "Chicago", "Hawks"],
    "Colorado Avalanche": ["Avalanche", "Avs", "Colorado"],
    "Columbus Blue Jackets": ["Blue Jackets", "Jackets", "Columbus", "CBJ"],
    "Dallas Stars": ["Stars", "Dallas"],
    "Detroit Red Wings": ["Red Wings", "Wings", "Detroit"],
    "Edmonton Oilers": ["Oilers", "Edmonton"],
    "Florida Panthers": ["Panthers", "Florida"],
    "Los Angeles Kings": ["LA Kings", "Kings", "Los Angeles", "LA"],
    "Minnesota Wild": ["Wild", "Minnesota"],
    "Montreal Canadiens": ["Canadiens", "Habs", "Montreal"],
    "Nashville Predators": ["Predators", "Preds", "Nashville"],
    "New Jersey Devils": ["Devils", "New Jersey", "NJ Devils", "NJ"],
    "New York Islanders": ["Islanders", "NY Islanders", "NYI"],
    "New York Rangers": ["Rangers", "NY Rangers", "NYR"],
    "Ottawa Senators": ["Senators", "Sens", "Ottawa"],
    "Philadelphia Flyers": ["Flyers", "Philadelphia", "Philly"],
    "Pittsburgh Penguins": ["Penguins", "Pens", "Pittsburgh"],
    "San Jose Sharks": ["Sharks", "San Jose", "SJ Sharks", "SJ"],
    "Seattle Kraken": ["Kraken", "Seattle"],
    "St. Louis Blues": ["Saint Louis Blues", "St Louis Blues", "Blues", "St Louis", "STL"],
    "Tampa Bay Lightning": ["Lightning", "Bolts", "Tampa", "Tampa Bay"],
    "Toronto Maple Leafs": ["Maple Leafs", "Leafs", "Toronto"],
    "Utah Mammoth": ["Mammoth", "Utah"],
    "Vancouver Canucks": ["Canucks", "Vancouver", "Nucks"],
    "Vegas Golden Knights": ["Golden Knights", "VGK", "Vegas"],
    "Washington Capitals": ["Capitals", "Caps", "Washington"],
    "Winnipeg Jets": ["Jets", "Winnipeg"],
}


_NBA_TEAM_SYNONYMS: Dict[str, Iterable[str]] = {
    "Atlanta Hawks": ["Hawks", "Atlanta", "ATL"],
    "Boston Celtics": ["Celtics", "Boston", "BOS"],
    "Brooklyn Nets": ["Nets", "Brooklyn", "BKN"],
    "Charlotte Hornets": ["Hornets", "Charlotte", "CHA"],
    "Chicago Bulls": ["Bulls", "Chicago", "CHI"],
    "Cleveland Cavaliers": ["Cavaliers", "Cavs", "Cleveland", "CLE"],
    "Dallas Mavericks": ["Mavericks", "Mavs", "Dallas", "DAL"],
    "Denver Nuggets": ["Nuggets", "Denver", "DEN"],
    "Detroit Pistons": ["Pistons", "Detroit", "DET"],
    "Golden State Warriors": ["Warriors", "Golden State", "GSW", "Dubs"],
    "Houston Rockets": ["Rockets", "Houston", "HOU"],
    "Indiana Pacers": ["Pacers", "Indiana", "IND"],
    "Los Angeles Clippers": ["Clippers", "LA Clippers", "LAC"],
    "Los Angeles Lakers": ["Lakers", "LA Lakers", "LAL"],
    "Memphis Grizzlies": ["Grizzlies", "Memphis", "MEM", "Grizz"],
    "Miami Heat": ["Heat", "Miami", "MIA"],
    "Milwaukee Bucks": ["Bucks", "Milwaukee", "MIL"],
    "Minnesota Timberwolves": ["Timberwolves", "Wolves", "Minnesota", "MIN"],
    "New Orleans Pelicans": ["Pelicans", "New Orleans", "NOP", "NOLA"],
    "New York Knicks": ["Knicks", "New York", "NYK"],
    "Oklahoma City Thunder": ["Thunder", "Oklahoma City", "OKC"],
    "Orlando Magic": ["Magic", "Orlando", "ORL"],
    "Philadelphia 76ers": ["76ers", "Sixers", "Philadelphia", "PHI", "Philly"],
    "Phoenix Suns": ["Suns", "Phoenix", "PHX"],
    "Portland Trail Blazers": ["Trail Blazers", "Blazers", "Portland", "POR"],
    "Sacramento Kings": ["Kings", "Sacramento", "SAC"],
    "San Antonio Spurs": ["Spurs", "San Antonio", "SAS"],
    "Toronto Raptors": ["Raptors", "Toronto", "TOR"],
    "Utah Jazz": ["Jazz", "Utah", "UTA"],
    "Washington Wizards": ["Wizards", "Washington", "WAS"],
}


_TEAM_ALIAS_MAPS: Dict[str, Dict[str, str]] = {
    "nhl": _build_alias_map(_NHL_TEAM_SYNONYMS),
    "nba": _build_alias_map(_NBA_TEAM_SYNONYMS),
}


def get_team_alias_map(name: Optional[str]) -> Dict[str, str]:
    if not name:
        return {}
    return _TEAM_ALIAS_MAPS.get(name, {})

