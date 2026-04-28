import os
import requests
from flask import Flask, render_template, request, abort
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

# Premier League has the richest open data availability
DEFAULT_LEAGUE = "PL"

LEAGUES = {
    "PL": {"name": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "England"},
    "PD": {"name": "La Liga", "flag": "🇪🇸", "country": "Spain"},
    "BL1": {"name": "Bundesliga", "flag": "🇩🇪", "country": "Germany"},
    "SA": {"name": "Serie A", "flag": "🇮🇹", "country": "Italy"},
    "FL1": {"name": "Ligue 1", "flag": "🇫🇷", "country": "France"},
}


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if resp.status_code == 403:
        abort(403)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=32)
def get_scorers(league_code, season=None):
    params = {"limit": 20}
    if season:
        params["season"] = season
    return api_get(f"/competitions/{league_code}/scorers", params)


@lru_cache(maxsize=32)
def get_standings(league_code, season=None):
    params = {}
    if season:
        params["season"] = season
    return api_get(f"/competitions/{league_code}/standings", params)


@lru_cache(maxsize=32)
def get_teams(league_code, season=None):
    params = {}
    if season:
        params["season"] = season
    return api_get(f"/competitions/{league_code}/teams", params)


@lru_cache(maxsize=64)
def get_team(team_id):
    return api_get(f"/teams/{team_id}")


@lru_cache(maxsize=64)
def get_person(person_id):
    return api_get(f"/persons/{person_id}")


@lru_cache(maxsize=64)
def get_person_matches(person_id):
    return api_get(f"/persons/{person_id}/matches", {"limit": 10, "status": "FINISHED"})


@app.route("/")
def index():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE

    scorers_data = get_scorers(league_code)
    standings_data = get_standings(league_code)

    table = []
    if standings_data.get("standings"):
        for group in standings_data["standings"]:
            if group.get("type") == "TOTAL":
                table = group.get("table", [])
                break

    return render_template(
        "index.html",
        scorers=scorers_data.get("scorers", []),
        table=table,
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
        season=scorers_data.get("season", {}),
    )


@app.route("/teams")
def teams():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE

    teams_data = get_teams(league_code)
    return render_template(
        "teams.html",
        teams=teams_data.get("teams", []),
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
    )


@app.route("/team/<int:team_id>")
def team_detail(team_id):
    team_data = get_team(team_id)
    squad = team_data.get("squad", [])

    # Sort squad: goalkeepers first, then by position
    position_order = {"Goalkeeper": 0, "Defence": 1, "Midfield": 2, "Offence": 3}
    squad.sort(key=lambda p: (position_order.get(p.get("position", ""), 9), p.get("name", "")))

    return render_template(
        "team_detail.html",
        team=team_data,
        squad=squad,
        leagues=LEAGUES,
    )


@app.route("/player/<int:player_id>")
def player_detail(player_id):
    player = get_person(player_id)
    try:
        matches_data = get_person_matches(player_id)
        recent_matches = matches_data.get("matches", [])
    except Exception:
        recent_matches = []

    return render_template(
        "player_detail.html",
        player=player,
        recent_matches=recent_matches,
        leagues=LEAGUES,
    )


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="API key missing or invalid. Set FOOTBALL_DATA_API_KEY in .env"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong fetching data."), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
