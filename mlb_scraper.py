"""
MLB Speler-statistieken Scraper — batting, pitching en fielding van alle
spelers, in één JSON, opgebouwd als "headers + data" (zoals de Czech
Extraliga-scraper), zodat de bijbehorende PHP-widgets generiek kunnen
renderen zonder veldnamen hard te coderen.

Gebruikt de officiële MLB Stats API (statsapi.mlb.com), dezelfde bron als
mlb.com/stats zelf. Geen browser-scraping nodig.

LET OP: dit is een herstructurering t.o.v. de vorige versie van dit bestand
(die had aparte "hitting"/"pitching" lijsten zonder headers-metadata).
Vervang je oude mlb_stats_scraper.py door deze versie in zijn geheel.
"""
import json
import os
import urllib.request
import datetime as dt
from datetime import timezone

STATS_API = (
    "https://statsapi.mlb.com/api/v1/stats"
    "?stats=season&group={groep}&sportId=1&season={seizoen}"
    "&playerPool=all&limit={limiet}&offset={offset}"
)
TEAMS_API = "https://statsapi.mlb.com/api/v1/teams?sportId=1&activeStatus=Y"
JSON_FILE = "mlb_stats.json"
PAGINA_GROOTTE = 100

BATTING_HEADERS = [
    {"column": "name",     "label": "Player"},
    {"column": "teamcode", "label": "Team"},
    {"column": "g",        "label": "G",    "tooltip": "Games Played"},
    {"column": "ab",       "label": "AB",   "tooltip": "At Bats"},
    {"column": "r",        "label": "R",    "tooltip": "Runs"},
    {"column": "h",        "label": "H",    "tooltip": "Hits"},
    {"column": "doubles",  "label": "2B",   "tooltip": "Doubles"},
    {"column": "triples",  "label": "3B",   "tooltip": "Triples"},
    {"column": "hr",       "label": "HR",   "tooltip": "Home Runs"},
    {"column": "rbi",      "label": "RBI",  "tooltip": "Runs Batted In"},
    {"column": "bb",       "label": "BB",   "tooltip": "Walks (Base on Balls)"},
    {"column": "so",       "label": "SO",   "tooltip": "Strikeouts"},
    {"column": "sb",       "label": "SB",   "tooltip": "Stolen Bases"},
    {"column": "avg",      "label": "AVG",  "tooltip": "Batting Average"},
    {"column": "obp",      "label": "OBP",  "tooltip": "On-Base Percentage"},
    {"column": "slg",      "label": "SLG",  "tooltip": "Slugging Percentage"},
    {"column": "ops",      "label": "OPS",  "tooltip": "On-base Plus Slugging"},
]

PITCHING_HEADERS = [
    {"column": "name",     "label": "Player"},
    {"column": "teamcode", "label": "Team"},
    {"column": "w",        "label": "W",    "tooltip": "Wins"},
    {"column": "l",        "label": "L",    "tooltip": "Losses"},
    {"column": "era",      "label": "ERA",  "tooltip": "Earned Run Average"},
    {"column": "g",        "label": "G",    "tooltip": "Games Pitched"},
    {"column": "gs",       "label": "GS",   "tooltip": "Games Started"},
    {"column": "sv",       "label": "SV",   "tooltip": "Saves"},
    {"column": "ip",       "label": "IP",   "tooltip": "Innings Pitched"},
    {"column": "h",        "label": "H",    "tooltip": "Hits Allowed"},
    {"column": "r",        "label": "R",    "tooltip": "Runs Allowed"},
    {"column": "er",       "label": "ER",   "tooltip": "Earned Runs"},
    {"column": "hr",       "label": "HR",   "tooltip": "Home Runs Allowed"},
    {"column": "bb",       "label": "BB",   "tooltip": "Walks (Base on Balls)"},
    {"column": "so",       "label": "SO",   "tooltip": "Strikeouts"},
    {"column": "whip",     "label": "WHIP", "tooltip": "Walks + Hits per Inning Pitched"},
]

FIELDING_HEADERS = [
    {"column": "name",     "label": "Player"},
    {"column": "teamcode", "label": "Team"},
    {"column": "positie",  "label": "Pos"},
    {"column": "g",        "label": "G",    "tooltip": "Games Played"},
    {"column": "po",       "label": "PO",   "tooltip": "Put Outs"},
    {"column": "a",        "label": "A",    "tooltip": "Assists"},
    {"column": "e",        "label": "E",    "tooltip": "Errors"},
    {"column": "dp",       "label": "DP",   "tooltip": "Double Plays"},
    {"column": "fld",      "label": "FLD%", "tooltip": "Fielding Percentage"},
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def logo_url(team_id):
    if not team_id:
        return None
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def speler_link(speler_id):
    if not speler_id:
        return None
    return f"https://www.mlb.com/player/{speler_id}"


def fetch_teaminfo():
    """Haalt per team-id de officiële afkorting én volledige naam op (dynamisch)."""
    data = fetch_json(TEAMS_API)
    info = {}
    for team in data.get("teams", []):
        info[team["id"]] = {
            "code": team.get("abbreviation", team["name"][:3].upper()),
            "naam": team.get("name", "-"),
        }
    return info


def fetch_alle_splits(groep, seizoen):
    """Haalt alle spelers voor een stat-groep (batting/pitching/fielding) op, gepagineerd."""
    alle_splits = []
    offset = 0
    totaal = None
    while totaal is None or offset < totaal:
        url = STATS_API.format(groep=groep, seizoen=seizoen, limiet=PAGINA_GROOTTE, offset=offset)
        data = fetch_json(url)
        stats_blokken = data.get("stats", [])
        if not stats_blokken:
            break
        blok = stats_blokken[0]
        if totaal is None:
            totaal = blok.get("totalSplits", 0)
            print(f"  {groep}: {totaal} regels in totaal")
        splits = blok.get("splits", [])
        if not splits:
            break
        alle_splits.extend(splits)
        offset += PAGINA_GROOTTE
    return alle_splits


def basisvelden(split, teaminfo):
    speler = split.get("player", {})
    team = split.get("team", {})
    team_id = team.get("id")
    speler_id = speler.get("id")
    return {
        "speler_id":  speler_id,
        "name":       speler.get("fullName", "-"),
        "team_id":    team_id,
        "teamcode":   teaminfo.get(team_id, {}).get("code", "-"),
        "team":       team.get("name", "-"),
        "team_logo":  logo_url(team_id),
        "link":       speler_link(speler_id),
    }


def bouw_batting_rij(split, teaminfo):
    stat = split.get("stat", {})
    rij = basisvelden(split, teaminfo)
    rij.update({
        "g":       stat.get("gamesPlayed"),
        "ab":      stat.get("atBats"),
        "r":       stat.get("runs"),
        "h":       stat.get("hits"),
        "doubles": stat.get("doubles"),
        "triples": stat.get("triples"),
        "hr":      stat.get("homeRuns"),
        "rbi":     stat.get("rbi"),
        "bb":      stat.get("baseOnBalls"),
        "so":      stat.get("strikeOuts"),
        "sb":      stat.get("stolenBases"),
        "avg":     stat.get("avg"),
        "obp":     stat.get("obp"),
        "slg":     stat.get("slg"),
        "ops":     stat.get("ops"),
    })
    return rij


def bouw_pitching_rij(split, teaminfo):
    stat = split.get("stat", {})
    rij = basisvelden(split, teaminfo)
    rij.update({
        "w":    stat.get("wins"),
        "l":    stat.get("losses"),
        "era":  stat.get("era"),
        "g":    stat.get("gamesPitched"),
        "gs":   stat.get("gamesStarted"),
        "sv":   stat.get("saves"),
        "ip":   stat.get("inningsPitched"),
        "h":    stat.get("hits"),
        "r":    stat.get("runs"),
        "er":   stat.get("earnedRuns"),
        "hr":   stat.get("homeRuns"),
        "bb":   stat.get("baseOnBalls"),
        "so":   stat.get("strikeOuts"),
        "whip": stat.get("whip"),
    })
    return rij


def bouw_fielding_rij(split, teaminfo):
    stat = split.get("stat", {})
    positie = split.get("position", {})
    rij = basisvelden(split, teaminfo)
    rij.update({
        "positie": positie.get("abbreviation", "-"),
        "g":       stat.get("gamesPlayed"),
        "po":      stat.get("putOuts"),
        "a":       stat.get("assists"),
        "e":       stat.get("errors"),
        "dp":      stat.get("doublePlays"),
        "fld":     stat.get("fielding"),
    })
    return rij


def parse_getal(waarde):
    """Zet een stat-waarde (int, of string als '.314'/'139.0') om naar float, of None."""
    if waarde is None:
        return None
    try:
        return float(waarde)
    except (TypeError, ValueError):
        return None


def sorteer_batting(batting_data):
    """
    Beste spelers eerst: batting average, maar alleen 'gekwalificeerd' als
    AB >= 25% van de AB van de leider (de speler met de meeste at-bats dit
    seizoen). Niet-gekwalificeerde spelers blijven zichtbaar, maar staan
    onder de gekwalificeerde groep (net als bij officiële titel-races).
    """
    ab_waarden = [parse_getal(r.get("ab")) for r in batting_data]
    ab_waarden = [w for w in ab_waarden if w is not None]
    max_ab = max(ab_waarden) if ab_waarden else 0
    drempel = 0.25 * max_ab

    def sleutel(r):
        ab = parse_getal(r.get("ab")) or 0
        avg = parse_getal(r.get("avg"))
        gekwalificeerd = drempel > 0 and ab >= drempel
        avg_waarde = avg if avg is not None else -1
        return (0 if gekwalificeerd else 1, -avg_waarde)

    batting_data.sort(key=sleutel)
    return drempel


def sorteer_pitching(pitching_data):
    """
    Beste spelers eerst: ERA, maar alleen 'gekwalificeerd' als IP >= 10% van
    de IP van de leider (de pitcher met de meeste innings pitched dit
    seizoen). Niet-gekwalificeerde spelers blijven zichtbaar, maar staan
    onder de gekwalificeerde groep.
    """
    ip_waarden = [parse_getal(r.get("ip")) for r in pitching_data]
    ip_waarden = [w for w in ip_waarden if w is not None]
    max_ip = max(ip_waarden) if ip_waarden else 0
    drempel = 0.10 * max_ip

    def sleutel(r):
        ip = parse_getal(r.get("ip")) or 0
        era = parse_getal(r.get("era"))
        gekwalificeerd = drempel > 0 and ip >= drempel
        era_waarde = era if era is not None else 999
        return (0 if gekwalificeerd else 1, era_waarde)

    pitching_data.sort(key=sleutel)
    return drempel


def dedupliceer_fielding(fielding_data):
    """
    De MLB-fielding-API levert per gespeelde positie een aparte regel, dus
    een speler die op meerdere posities speelde (bv. 1B + C + DH) komt
    meerdere keren voor. Hou per speler alleen de regel met de meeste
    gespeelde wedstrijden aan (zijn hoofdpositie), zodat elke speler maar
    één keer in de lijst staat.
    """
    per_speler = {}
    for rij in fielding_data:
        sleutel = rij.get("speler_id") or rij.get("name")
        huidige = per_speler.get(sleutel)
        if huidige is None or (parse_getal(rij.get("g")) or 0) > (parse_getal(huidige.get("g")) or 0):
            per_speler[sleutel] = rij
    return list(per_speler.values())


def bouw_teams_lookup(teaminfo):
    """team-lookup (naam + logo) per teamcode, voor de Teams-tab in de PHP-widget."""
    lookup = {}
    for team_id, info in teaminfo.items():
        lookup[info["code"]] = {
            "team_id": team_id,
            "naam":    info["naam"],
            "logo":    logo_url(team_id),
        }
    return lookup


def laad_bestaand():
    if not os.path.exists(JSON_FILE):
        return None
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def main():
    seizoen = dt.datetime.now(timezone.utc).year
    print(f"Seizoen: {seizoen}")

    print("\nTeaminformatie ophalen...")
    teaminfo = fetch_teaminfo()

    print("\nBatting-statistieken ophalen...")
    batting_splits = fetch_alle_splits("hitting", seizoen)
    batting_data = [bouw_batting_rij(s, teaminfo) for s in batting_splits]
    ab_drempel = sorteer_batting(batting_data)
    print(f"→ {len(batting_data)} batters (AB-kwalificatiedrempel: {ab_drempel:.1f})")

    print("\nPitching-statistieken ophalen...")
    pitching_splits = fetch_alle_splits("pitching", seizoen)
    pitching_data = [bouw_pitching_rij(s, teaminfo) for s in pitching_splits]
    ip_drempel = sorteer_pitching(pitching_data)
    print(f"→ {len(pitching_data)} pitchers (IP-kwalificatiedrempel: {ip_drempel:.1f})")

    print("\nFielding-statistieken ophalen...")
    fielding_splits = fetch_alle_splits("fielding", seizoen)
    fielding_data_ruw = [bouw_fielding_rij(s, teaminfo) for s in fielding_splits]
    fielding_data = dedupliceer_fielding(fielding_data_ruw)
    fielding_data.sort(key=lambda r: -(parse_getal(r.get("g")) or 0))
    print(f"→ {len(fielding_data)} spelers ({len(fielding_data_ruw)} regels vóór dedupliceren op hoofdpositie)")

    nu = dt.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nieuw = {
        "batting":  {"headers": BATTING_HEADERS,  "data": batting_data},
        "pitching": {"headers": PITCHING_HEADERS, "data": pitching_data},
        "fielding": {"headers": FIELDING_HEADERS, "data": fielding_data},
        "teams":    bouw_teams_lookup(teaminfo),
    }

    # last_updated verandert alleen als de spelersdata ook echt anders is;
    # last_checked wordt elke run bijgewerkt, zodat je op de site kunt zien
    # of de scraper nog actief draait, los van of er nieuwe standen zijn.
    bestaand = laad_bestaand()
    ongewijzigd = (
        bestaand is not None
        and bestaand.get("batting", {}).get("data") == batting_data
        and bestaand.get("pitching", {}).get("data") == pitching_data
        and bestaand.get("fielding", {}).get("data") == fielding_data
    )
    last_updated = bestaand["meta"]["last_updated"] if ongewijzigd and bestaand.get("meta") else nu

    output = {
        "meta": {
            "seizoen":       seizoen,
            "last_updated":  last_updated,
            "last_checked":  nu,
            "ab_drempel":    round(ab_drempel, 1),
            "ip_drempel":    round(ip_drempel, 1),
        },
        **nieuw,
    }
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n{JSON_FILE}: {len(batting_data)} batters, {len(pitching_data)} pitchers, "
          f"{len(fielding_data)} fielding-regels (gewijzigd: {not ongewijzigd})")


if __name__ == "__main__":
    main()
