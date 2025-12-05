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
    "Anaheim Ducks": ["Ducks", "Anaheim", "ANA"],
    "Arizona Coyotes": ["Coyotes", "Arizona", "Yotes", "ARI"],
    "Boston Bruins": ["Bruins", "Boston", "BOS"],
    "Buffalo Sabres": ["Sabres", "Buffalo", "BUF"],
    "Calgary Flames": ["Flames", "Calgary", "CGY"],
    "Carolina Hurricanes": ["Hurricanes", "Canes", "Carolina", "CAR"],
    "Chicago Blackhawks": ["Blackhawks", "Chicago", "Hawks", "CHI"],
    "Colorado Avalanche": ["Avalanche", "Avs", "Colorado", "COL"],
    "Columbus Blue Jackets": ["Blue Jackets", "Jackets", "Columbus", "CBJ"],
    "Dallas Stars": ["Stars", "Dallas", "DAL"],
    "Detroit Red Wings": ["Red Wings", "Wings", "Detroit", "DET"],
    "Edmonton Oilers": ["Oilers", "Edmonton", "EDM"],
    "Florida Panthers": ["Panthers", "Florida", "FLA"],
    "Los Angeles Kings": ["LA Kings", "Kings", "Los Angeles", "LA", "LAK"],
    "Minnesota Wild": ["Wild", "Minnesota", "MIN"],
    "Montreal Canadiens": ["Canadiens", "Habs", "Montreal", "MTL"],
    "Nashville Predators": ["Predators", "Preds", "Nashville", "NSH"],
    "New Jersey Devils": ["Devils", "New Jersey", "NJ Devils", "NJ", "NJD"],
    "New York Islanders": ["Islanders", "NY Islanders", "NYI"],
    "New York Rangers": ["Rangers", "NY Rangers", "NYR"],
    "Ottawa Senators": ["Senators", "Sens", "Ottawa", "OTT"],
    "Philadelphia Flyers": ["Flyers", "Philadelphia", "Philly", "PHI"],
    "Pittsburgh Penguins": ["Penguins", "Pens", "Pittsburgh", "PIT"],
    "San Jose Sharks": ["Sharks", "San Jose", "SJ Sharks", "SJ", "SJS"],
    "Seattle Kraken": ["Kraken", "Seattle", "SEA"],
    "St. Louis Blues": ["Saint Louis Blues", "St Louis Blues", "Blues", "St Louis", "STL"],
    "Tampa Bay Lightning": ["Lightning", "Bolts", "Tampa", "Tampa Bay", "TBL"],
    "Toronto Maple Leafs": ["Maple Leafs", "Leafs", "Toronto", "TOR"],
    "Utah Mammoth": ["Mammoth", "Utah", "UTA"],
    "Vancouver Canucks": ["Canucks", "Vancouver", "Nucks", "VAN"],
    "Vegas Golden Knights": ["Golden Knights", "VGK", "Vegas"],
    "Washington Capitals": ["Capitals", "Caps", "Washington", "WSH"],
    "Winnipeg Jets": ["Jets", "Winnipeg", "WPG"],
}

_EPL_TEAM_SYNONYMS: Dict[str, Iterable[str]] = {
    "Arsenal": ["Arsenal FC", "Gunners", "ARS"],
    "Aston Villa": ["Villa", "AVFC", "AVL"],
    "Bournemouth": ["AFC Bournemouth", "Cherries", "BOU"],
    "Brentford": ["Brentford FC", "BRE"],
    "Brighton & Hove Albion": [
        "Brighton",
        "Brighton and Hove Albion",
        "Brighton Hove Albion",
        "Albion",
        "BHAFC",
        "BHA",
    ],
    "Burnley": ["Burnley FC", "Clarets", "BUR"],
    "Chelsea": ["Chelsea FC", "Blues", "CHE", "CFC"],
    "Crystal Palace": ["Palace", "CPFC", "CRY"],
    "Everton": ["Everton FC", "Toffees", "EVE", "EFC"],
    "Fulham": ["Fulham FC", "Cottagers", "FUL"],
    "Ipswich Town": ["Ipswich", "ITFC"],
    "Leeds United": ["Leeds", "Leeds Utd", "Leeds United FC", "LUFC"],
    "Leicester City": ["Leicester", "Foxes", "LCFC", "LEI"],
    "Liverpool": ["Liverpool FC", "Reds", "LIV", "LFC"],
    "Luton Town": ["Luton", "Hatters", "LTFC"],
    "Manchester City": ["Man City", "Manchester C", "MCFC", "MCI"],
    "Manchester United": ["Man United", "Man Utd", "MUFC", "MUN", "Man U"],
    "Newcastle United": ["Newcastle", "Magpies", "NUFC"],
    "Nottingham Forest": ["Nottingham", "Forest", "NFFC", "NOT"],
    "Sheffield United": ["Sheffield Utd", "Blades", "SUFC", "SHU"],
    "Southampton": ["Saints", "Southampton FC", "SOU"],
    "Tottenham Hotspur": ["Spurs", "Tottenham", "THFC", "TOT"],
    "West Ham United": ["West Ham", "Hammers", "WHU", "WHFC"],
    "Wolverhampton Wanderers": ["Wolves", "Wolverhampton", "WWFC", "WOL"],
    "Sunderland": ["SAFC", "Sunderland AFC", "Black Cats", "SUN"],
}


_TEAM_ALIAS_MAPS: Dict[str, Dict[str, str]] = {
    "nhl": _build_alias_map(_NHL_TEAM_SYNONYMS),
    "premier_league": _build_alias_map(_EPL_TEAM_SYNONYMS),
}


def get_team_alias_map(name: Optional[str]) -> Dict[str, str]:
    if not name:
        return {}
    return _TEAM_ALIAS_MAPS.get(name, {})

