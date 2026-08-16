"""
MLB Scraper — uitslagen + programma in één run, één JSON.
Uitslagen: de wedstrijden van gisteren (Amerikaanse baseball-dag, Eastern Time)
Programma: de wedstrijden van vandaag

Gebruikt de officiële MLB Stats API (statsapi.mlb.com) in plaats van
browser-scraping: mlb.com/schedule wordt hier zelf ook door gevoed, en de API
geeft dezelfde data terug als nette JSON. Geen Playwright/Chromium nodig.
"""
import json
import urllib.request
import datetime as dt
from datetime import timezone
from zoneinfo import ZoneInfo

SCHEDULE_API = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&date={datum}&hydrate=team,linescore,probablePitcher"
)
TEAMS_API = "https://statsapi.mlb.com/api/v1/teams?sportId=1&activeStatus=Y"
JSON_FILE = "mlb_schedule.json"

# MLB organiseert de speeldag op Eastern Time (ET) — dezelfde referentie die
# officialDate/gameDate in de API gebruiken.
ET = ZoneInfo("America/New_York")


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_afkortingen():
    """Haalt de officiële MLB-afkortingen per team op (dynamisch, geen vaste lijst)."""
    data = fetch_json(TEAMS_API)
    afkortingen = {}
    for team in data.get("teams", []):
        afkortingen[team["name"]] = team.get("abbreviation", team["name"][:3].upper())
    return afkortingen


def afkorting(team, afkortingen):
    if team in afkortingen:
        return afkortingen[team]
    for naam, afk in afkortingen.items():
        if naam.lower() in team.lower() or team.lower() in naam.lower():
            return afk
    return team[:3].upper()


def et_tijd(game_date_iso):
    """Zet een UTC ISO-timestamp (gameDate) om naar HH:MM Eastern Time."""
    if not game_date_iso:
        return None
    ts = dt.datetime.strptime(game_date_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return ts.astimezone(ET).strftime("%H:%M")


def logo_url(team_id):
    if not team_id:
        return None
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def parse_score(waarde):
    if waarde is None:
        return None
    try:
        return int(waarde)
    except (TypeError, ValueError):
        return None


def haal_wedstrijden(datum, afkortingen):
    url = SCHEDULE_API.format(datum=datum)
    data = fetch_json(url)
    wedstrijden = []
    for dag in data.get("dates", []):
        wedstrijden.extend(dag.get("games", []))
    return wedstrijden


def bouw_uitslag(game, afkortingen):
    teams = game.get("teams", {})
    thuis = teams.get("home", {})
    uit = teams.get("away", {})
    thuis_naam = thuis.get("team", {}).get("name", "-")
    uit_naam = uit.get("team", {}).get("name", "-")
    status = game.get("status", {})
    abstract_state = status.get("abstractGameState", "-")
    return {
        "datum":       game.get("officialDate"),
        "tijdstip":    et_tijd(game.get("gameDate")),
        "start_utc":   game.get("gameDate"),
        "thuis":       thuis_naam,
        "thuis_afk":   afkorting(thuis_naam, afkortingen),
        "thuis_logo":  logo_url(thuis.get("team", {}).get("id")),
        "uit":         uit_naam,
        "uit_afk":     afkorting(uit_naam, afkortingen),
        "uit_logo":    logo_url(uit.get("team", {}).get("id")),
        "score_thuis": parse_score(thuis.get("score")),
        "score_uit":   parse_score(uit.get("score")),
        "locatie":     game.get("venue", {}).get("name"),
        "status":      status.get("detailedState", "-"),
        "gespeeld":    abstract_state == "Final",
        "live":        abstract_state == "Live",
    }


def bouw_programma_item(game, afkortingen):
    teams = game.get("teams", {})
    thuis = teams.get("home", {})
    uit = teams.get("away", {})
    thuis_naam = thuis.get("team", {}).get("name", "-")
    uit_naam = uit.get("team", {}).get("name", "-")
    return {
        "datum":        game.get("officialDate"),
        "tijdstip":     et_tijd(game.get("gameDate")),
        "start_utc":    game.get("gameDate"),
        "thuis":        thuis_naam,
        "thuis_afk":    afkorting(thuis_naam, afkortingen),
        "thuis_logo":   logo_url(thuis.get("team", {}).get("id")),
        "uit":          uit_naam,
        "uit_afk":      afkorting(uit_naam, afkortingen),
        "uit_logo":     logo_url(uit.get("team", {}).get("id")),
        "werper_thuis": thuis.get("probablePitcher", {}).get("fullName"),
        "werper_uit":   uit.get("probablePitcher", {}).get("fullName"),
        "locatie":      game.get("venue", {}).get("name"),
        "status":       game.get("status", {}).get("detailedState", "-"),
    }


def main():
    nu_et = dt.datetime.now(ET)
    vandaag = nu_et.date()
    gisteren = vandaag - dt.timedelta(days=1)
    print(f"Nu (ET): {nu_et.strftime('%Y-%m-%d %H:%M')} — vandaag={vandaag}, gisteren={gisteren}")

    print("Teamafkortingen ophalen...")
    afkortingen = fetch_afkortingen()

    print(f"\nUitslagen ophalen voor {gisteren}...")
    ruwe_uitslagen = haal_wedstrijden(str(gisteren), afkortingen)
    uitslagen = [
        bouw_uitslag(g, afkortingen) for g in ruwe_uitslagen
        if g.get("teams", {}).get("home", {}).get("score") is not None
        or g.get("teams", {}).get("away", {}).get("score") is not None
    ]
    uitslagen.sort(key=lambda w: (w["datum"] or "", w["tijdstip"] or ""))
    print(f"→ {len(uitslagen)} uitslagen")

    print(f"\nProgramma ophalen voor {vandaag}...")
    ruwe_programma = haal_wedstrijden(str(vandaag), afkortingen)
    programma = [bouw_programma_item(g, afkortingen) for g in ruwe_programma]
    programma.sort(key=lambda w: (w["datum"] or "", w["tijdstip"] or ""))
    print(f"→ {len(programma)} programma wedstrijden")

    output = {
        "bijgewerkt": dt.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uitslagen":  uitslagen,
        "programma":  programma,
    }
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n{JSON_FILE}: {len(uitslagen)} uitslagen, {len(programma)} programma")


if __name__ == "__main__":
    main()
