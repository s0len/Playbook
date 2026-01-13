from __future__ import annotations

from collections.abc import Iterable

from .utils import normalize_token


def _build_alias_map(entries: dict[str, Iterable[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
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


_NHL_TEAM_SYNONYMS: dict[str, Iterable[str]] = {
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

_EPL_TEAM_SYNONYMS: dict[str, Iterable[str]] = {
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


_NBA_TEAM_SYNONYMS: dict[str, Iterable[str]] = {
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

_UEFA_CHAMPIONS_LEAGUE_TEAM_SYNONYMS: dict[str, Iterable[str]] = {
    # Spanish clubs
    "Real Madrid": ["Real", "RM", "RMA", "Los Blancos", "Madrid"],
    "Barcelona": ["Barca", "FCB", "Blaugrana", "FC Barcelona"],
    "Atlético Madrid": [
        "Atletico Madrid",
        "Atletico",
        "Atleti",
        "ATM",
        "Atletico de Madrid",
    ],
    "Sevilla": ["Sevilla FC", "SEV"],
    "Real Sociedad": ["Sociedad", "La Real", "RSO"],
    "Villarreal": ["Villarreal CF", "Yellow Submarine", "VIL"],
    # German clubs
    "Bayern Munich": [
        "Bayern",
        "Bayern München",
        "Bayern Munchen",
        "FCB",
        "FC Bayern",
        "BAY",
    ],
    "Borussia Dortmund": ["Dortmund", "BVB", "Borussia", "BOR", "DOR"],
    "Borussia Mönchengladbach": [
        "Mönchengladbach",
        "Gladbach",
        "Monchengladbach",
        "BMG",
    ],
    "RB Leipzig": ["Leipzig", "RBL", "Red Bull Leipzig"],
    "Bayer Leverkusen": ["Leverkusen", "Bayer 04", "B04", "LEV"],
    "Eintracht Frankfurt": ["Frankfurt", "Eintracht", "SGE", "FRA"],
    # Italian clubs
    "Inter Milan": ["Inter", "Internazionale", "FC Internazionale", "INT"],
    "AC Milan": ["Milan", "Rossoneri", "ACM", "MIL"],
    "Juventus": ["Juve", "JUV", "Old Lady", "Bianconeri"],
    "Napoli": ["SSC Napoli", "NAP"],
    "Roma": ["AS Roma", "Giallorossi", "ROM"],
    "Atalanta": ["Atalanta BC", "ATA", "La Dea"],
    "Lazio": ["SS Lazio", "LAZ"],
    # English clubs
    "Manchester City": ["Man City", "MC", "City", "MCFC", "MCI"],
    "Liverpool": ["Liverpool FC", "LIV", "LFC", "Reds"],
    "Chelsea": ["Chelsea FC", "CHE", "CFC", "Blues"],
    "Manchester United": ["Man United", "Man Utd", "MUFC", "MUN", "Man U"],
    "Arsenal": ["Arsenal FC", "ARS", "Gunners"],
    "Tottenham Hotspur": ["Spurs", "Tottenham", "THFC", "TOT"],
    "Newcastle United": ["Newcastle", "NUFC", "Magpies"],
    "Aston Villa": ["Villa", "AVFC", "AVL"],
    # French clubs
    "Paris Saint-Germain": ["PSG", "Paris", "Paris SG"],
    "Monaco": ["AS Monaco", "ASM", "MON"],
    "Marseille": ["Olympique Marseille", "OM", "Olympique de Marseille"],
    "Lyon": ["Olympique Lyonnais", "OL", "Olympique Lyon"],
    "Lille": ["LOSC", "LOSC Lille", "Lille OSC"],
    # Portuguese clubs
    "Benfica": ["SL Benfica", "Sport Lisboa e Benfica", "BEN"],
    "Porto": ["FC Porto", "Dragões", "Dragoes", "POR"],
    "Sporting CP": ["Sporting Lisbon", "Sporting", "SCP"],
    "Braga": ["SC Braga", "BRA"],
    # Dutch clubs
    "Ajax": ["AFC Ajax", "Ajax Amsterdam", "AJA"],
    "PSV Eindhoven": ["PSV", "Philips Sport Vereniging"],
    "Feyenoord": ["Feyenoord Rotterdam", "FEY"],
    # Belgian clubs
    "Club Brugge": ["Brugge", "Club Bruges", "BRU"],
    "Union Saint-Gilloise": ["Union SG", "USG", "Union"],
    "Anderlecht": ["RSC Anderlecht", "AND"],
    # Other notable European clubs
    "Celtic": ["Celtic FC", "Glasgow Celtic", "CEL"],
    "Rangers": ["Glasgow Rangers", "RAN"],
    "Salzburg": ["Red Bull Salzburg", "RB Salzburg", "SAL"],
    "Shakhtar Donetsk": ["Shakhtar", "Shaktar", "SHA"],
    "Dinamo Zagreb": ["Zagreb", "Dinamo", "DZA"],
    "Galatasaray": ["Gala", "GAL", "Cimbom"],
    "Fenerbahce": ["Fenerbahçe", "Fener", "FEN"],
    "Besiktas": ["Beşiktaş", "BJK"],
    "Copenhagen": ["FC Copenhagen", "FCK"],
    "Young Boys": ["BSC Young Boys", "YB", "YBO"],
    "Red Star Belgrade": ["Crvena Zvezda", "Red Star", "RSB"],
    "Olympiacos": ["Olympiakos", "Olympiacos Piraeus", "OLY"],
    "PAOK": ["PAOK Thessaloniki", "PAO"],
    "Slavia Prague": ["Slavia Praha", "SLA"],
    "Sparta Prague": ["Sparta Praha", "SPP"],
    "Sturm Graz": ["Sturm", "STU"],
    "LASK": ["LASK Linz"],
    "Fiorentina": ["ACF Fiorentina", "Viola", "FIO"],
    "Bologna": ["Bologna FC", "BOL"],
}


_TEAM_ALIAS_MAPS: dict[str, dict[str, str]] = {
    "nhl": _build_alias_map(_NHL_TEAM_SYNONYMS),
    "nba": _build_alias_map(_NBA_TEAM_SYNONYMS),
    "premier_league": _build_alias_map(_EPL_TEAM_SYNONYMS),
    "uefa_champions_league": _build_alias_map(_UEFA_CHAMPIONS_LEAGUE_TEAM_SYNONYMS),
}


def get_team_alias_map(name: str | None) -> dict[str, str]:
    if not name:
        return {}
    return _TEAM_ALIAS_MAPS.get(name, {})
