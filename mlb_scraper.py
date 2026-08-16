import json
import urllib.request
from datetime import datetime, timezone

BRON_URL = "https://www.mlb.com/standings/"

STANDINGS_API = (
    "https://statsapi.mlb.com/api/v1/standings"
    "?leagueId=103,104&season={season}&standingsTypes=regularSeason"
)
TEAMS_API = "https://statsapi.mlb.com/api/v1/teams?sportId=1&activeStatus=Y"
DIVISIONS_API = "https://statsapi.mlb.com/api/v1/divisions?sportId=1"

# Weergavevolgorde van de divisies (Oost, Centraal, West per league).
DIVISIE_VOLGORDE = [201, 202, 200, 204, 205, 203]


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_teams():
    data = fetch_json(TEAMS_API)
    teams = {}
    for team in data.get("teams", []):
        teams[team["id"]] = {
            "naam": team.get("name", "-"),
            "afkorting": team.get("abbreviation", "-"),
        }
    return teams


def fetch_divisienamen():
    data = fetch_json(DIVISIONS_API)
    namen = {}
    for divisie in data.get("divisions", []):
        namen[divisie["id"]] = divisie.get("name", "-")
    return namen


def logo_url(team_id):
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def parse_standings(standings_data, teams, divisienamen):
    result = {}
    volgorde_index = {div_id: i for i, div_id in enumerate(DIVISIE_VOLGORDE)}

    for record in standings_data.get("records", []):
        divisie_id = record.get("division", {}).get("id")
        divisie_naam = divisienamen.get(divisie_id, f"Divisie {divisie_id}")

        rijen = []
        for team_record in record.get("teamRecords", []):
            team_id = team_record.get("team", {}).get("id")
            team_info = teams.get(team_id, {"naam": team_record.get("team", {}).get("name", "-")})
            rij = {
                "positie": team_record.get("divisionRank", "-"),
                "team": team_info["naam"],
                "logo_url": logo_url(team_id) if team_id else "",
                "w": str(team_record.get("wins", "-")),
                "l": str(team_record.get("losses", "-")),
                "pct": team_record.get("winningPercentage", "-"),
                "gb": team_record.get("gamesBack", "-"),
            }
            rijen.append(rij)

        rijen.sort(key=lambda r: int(r["positie"]) if r["positie"].isdigit() else 99)
        result[divisie_naam] = {
            "divisie_id": divisie_id,
            "volgorde": volgorde_index.get(divisie_id, 99),
            "rijen": rijen,
        }

    # Sorteer de divisies zelf in de gewenste weergavevolgorde en maak er weer
    # een simpel dict van (naam -> rijen), net als bij de DBL-scraper.
    gesorteerd = sorted(result.items(), key=lambda kv: kv[1]["volgorde"])
    return {naam: info["rijen"] for naam, info in gesorteerd}


def main():
    season = datetime.now(timezone.utc).year
    print(f"Ophalen van teams en divisies...")
    teams = fetch_teams()
    divisienamen = fetch_divisienamen()

    print(f"Ophalen van standen voor seizoen {season}...")
    standings_data = fetch_json(STANDINGS_API.format(season=season))

    standen = parse_standings(standings_data, teams, divisienamen)
    print(f"Gevonden divisies: {list(standen.keys())}")
    for divisie, rijen in standen.items():
        print(f"\n{divisie}:")
        for r in rijen:
            print(f"  {r['positie']}. {r['team']} | W:{r['w']} L:{r['l']} PCT:{r['pct']} GB:{r['gb']}")

    output = {
        "bijgewerkt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bron": BRON_URL,
        "standen": standen,
    }
    with open("mlb_standen.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\nmlb_standen.json opgeslagen")


if __name__ == "__main__":
    main()
