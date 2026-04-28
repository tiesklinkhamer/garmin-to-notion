import os
import requests
from flask import Flask, render_template, request, redirect, abort, jsonify
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY  = os.getenv("FOOTBALL_DATA_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
HEADERS  = {"X-Auth-Token": API_KEY}

DEFAULT_LEAGUE = "PL"

LEAGUES = {
    "PL":  {"name": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "England",  "short": "PL"},
    "PD":  {"name": "La Liga",         "flag": "🇪🇸",         "country": "Spain",    "short": "LaLiga"},
    "BL1": {"name": "Bundesliga",      "flag": "🇩🇪",         "country": "Germany",  "short": "BL"},
    "SA":  {"name": "Serie A",         "flag": "🇮🇹",         "country": "Italy",    "short": "SA"},
    "FL1": {"name": "Ligue 1",         "flag": "🇫🇷",         "country": "France",   "short": "L1"},
}

POSITION_ABBR = {
    "Goalkeeper": "GK",
    "Defence":    "DEF",
    "Midfield":   "MID",
    "Offence":    "FWD",
}

POSITION_CLASS = {
    "Goalkeeper": "pos-gk",
    "Defence":    "pos-def",
    "Midfield":   "pos-mid",
    "Offence":    "pos-fwd",
}

COUNTRY_FLAGS = {
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "France": "🇫🇷", "Spain": "🇪🇸", "Germany": "🇩🇪", "Italy": "🇮🇹",
    "Portugal": "🇵🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪",
    "Brazil": "🇧🇷", "Argentina": "🇦🇷", "Uruguay": "🇺🇾", "Colombia": "🇨🇴",
    "Chile": "🇨🇱", "Ecuador": "🇪🇨", "Paraguay": "🇵🇾", "Peru": "🇵🇪",
    "Mexico": "🇲🇽", "United States": "🇺🇸", "Canada": "🇨🇦", "Jamaica": "🇯🇲",
    "Norway": "🇳🇴", "Sweden": "🇸🇪", "Denmark": "🇩🇰", "Finland": "🇫🇮",
    "Switzerland": "🇨🇭", "Austria": "🇦🇹", "Poland": "🇵🇱", "Croatia": "🇭🇷",
    "Serbia": "🇷🇸", "Czech Republic": "🇨🇿", "Slovakia": "🇸🇰", "Hungary": "🇭🇺",
    "Romania": "🇷🇴", "Bulgaria": "🇧🇬", "Greece": "🇬🇷", "Turkey": "🇹🇷",
    "Ukraine": "🇺🇦", "Russia": "🇷🇺", "Ireland": "🇮🇪", "Iceland": "🇮🇸",
    "Montenegro": "🇲🇪", "Bosnia-Herzegovina": "🇧🇦", "North Macedonia": "🇲🇰",
    "Albania": "🇦🇱", "Kosovo": "🇽🇰", "Slovenia": "🇸🇮",
    "Senegal": "🇸🇳", "Nigeria": "🇳🇬", "Ghana": "🇬🇭", "Ivory Coast": "🇨🇮",
    "Morocco": "🇲🇦", "Algeria": "🇩🇿", "Egypt": "🇪🇬", "Cameroon": "🇨🇲",
    "Mali": "🇲🇱", "Guinea": "🇬🇳", "Congo DR": "🇨🇩", "Gabon": "🇬🇦",
    "Tunisia": "🇹🇳", "Cape Verde": "🇨🇻", "Togo": "🇹🇬", "Gambia": "🇬🇲",
    "Sierra Leone": "🇸🇱", "South Africa": "🇿🇦", "Angola": "🇦🇴",
    "Japan": "🇯🇵", "South Korea": "🇰🇷", "China PR": "🇨🇳", "Australia": "🇦🇺",
    "Iran": "🇮🇷", "Saudi Arabia": "🇸🇦", "Israel": "🇮🇱",
    "Latvia": "🇱🇻", "Lithuania": "🇱🇹", "Estonia": "🇪🇪",
    "Georgia": "🇬🇪", "Armenia": "🇦🇲", "Azerbaijan": "🇦🇿",
    "Trinidad and Tobago": "🇹🇹", "Haiti": "🇭🇹", "Cuba": "🇨🇺",
    "New Zealand": "🇳🇿", "Zimbabwe": "🇿🇼", "Zambia": "🇿🇲",
}


def api_get(path, params=None):
    resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=10)
    if resp.status_code == 403:
        abort(403)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=32)
def get_scorers(league_code):
    return api_get(f"/competitions/{league_code}/scorers", {"limit": 20})


@lru_cache(maxsize=32)
def get_standings(league_code):
    return api_get(f"/competitions/{league_code}/standings")


@lru_cache(maxsize=32)
def get_teams(league_code):
    return api_get(f"/competitions/{league_code}/teams")


@lru_cache(maxsize=64)
def get_team(team_id):
    return api_get(f"/teams/{team_id}")


@lru_cache(maxsize=64)
def get_person(person_id):
    return api_get(f"/persons/{person_id}")


@lru_cache(maxsize=64)
def get_person_matches(person_id):
    return api_get(f"/persons/{person_id}/matches", {"limit": 10, "status": "FINISHED"})


def get_total_table(league_code):
    data = get_standings(league_code)
    for group in data.get("standings", []):
        if group.get("type") == "TOTAL":
            return group.get("table", [])
    return []


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE

    scorers_data = get_scorers(league_code)
    scorers      = scorers_data.get("scorers", [])
    table        = get_total_table(league_code)

    max_goals   = max((e.get("goals")   or 0 for e in scorers), default=1) or 1
    max_assists = max((e.get("assists") or 0 for e in scorers), default=1) or 1
    scorers_by_assists = sorted(scorers, key=lambda x: (x.get("assists") or 0), reverse=True)

    return render_template(
        "index.html",
        scorers=scorers,
        scorers_by_assists=scorers_by_assists,
        max_goals=max_goals,
        max_assists=max_assists,
        table=table,
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
        season=scorers_data.get("season", {}),
    )


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect("/")
    q = query.lower()
    player_results, team_results = _do_search(q)
    return render_template(
        "search.html",
        player_results=player_results,
        team_results=team_results,
        query=query,
        leagues=LEAGUES,
        league_code=DEFAULT_LEAGUE,
    )


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"players": [], "teams": []})
    q = query.lower()
    player_results, team_results = _do_search(q)
    players = [
        {
            "id":       r["player"]["id"],
            "name":     r["player"]["name"],
            "team":     (r["team"] or {}).get("shortName") or (r["team"] or {}).get("name", ""),
            "goals":    r["goals"],
            "assists":  r["assists"],
            "nat":      r["player"].get("nationality", ""),
            "league":   r["league"]["short"],
        }
        for r in player_results[:7]
    ]
    teams = [
        {
            "id":    r["team"]["id"],
            "name":  r["team"].get("shortName") or r["team"]["name"],
            "crest": r["team"].get("crest", ""),
            "league": r["league"]["short"],
        }
        for r in team_results[:4]
    ]
    return jsonify({"players": players, "teams": teams})


def _do_search(q):
    player_results, team_results = [], []
    seen_pids, seen_tids = set(), set()
    for code in LEAGUES:
        try:
            for entry in get_scorers(code).get("scorers", []):
                p   = entry["player"]
                pid = p.get("id")
                t   = entry.get("team") or {}
                if pid not in seen_pids and (
                    q in p.get("name", "").lower() or
                    q in (p.get("nationality") or "").lower() or
                    q in t.get("name", "").lower()
                ):
                    seen_pids.add(pid)
                    player_results.append({
                        "player":  p,
                        "team":    t,
                        "goals":   entry.get("goals", 0),
                        "assists": entry.get("assists", 0),
                        "matches": entry.get("playedMatches", 0),
                        "league_code": code,
                        "league":  LEAGUES[code],
                    })
        except Exception:
            pass
    for code in LEAGUES:
        try:
            for team in get_teams(code).get("teams", []):
                tid = team.get("id")
                if tid not in seen_tids and (
                    q in team.get("name", "").lower() or
                    q in (team.get("shortName") or "").lower()
                ):
                    seen_tids.add(tid)
                    team_results.append({"team": team, "league_code": code, "league": LEAGUES[code]})
        except Exception:
            pass
    return player_results, team_results


@app.route("/teams")
def teams():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE
    data = get_teams(league_code)
    return render_template(
        "teams.html",
        teams=data.get("teams", []),
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
    )


@app.route("/team/<int:team_id>")
def team_detail(team_id):
    team_data = get_team(team_id)
    squad = team_data.get("squad", [])
    order = {"Goalkeeper": 0, "Defence": 1, "Midfield": 2, "Offence": 3}
    squad.sort(key=lambda p: (order.get(p.get("position", ""), 9), p.get("name", "")))
    return render_template(
        "team_detail.html",
        team=team_data,
        squad=squad,
        pos_abbr=POSITION_ABBR,
        pos_class=POSITION_CLASS,
        leagues=LEAGUES,
        league_code=DEFAULT_LEAGUE,
    )


@app.route("/player/<int:player_id>")
def player_detail(player_id):
    player = get_person(player_id)
    try:
        recent_matches = get_person_matches(player_id).get("matches", [])
    except Exception:
        recent_matches = []
    pos_abbr = POSITION_ABBR.get(player.get("position", ""), player.get("position", "—"))
    nat_flag = COUNTRY_FLAGS.get(player.get("nationality", ""), "")
    team_id  = (player.get("currentTeam") or {}).get("id")
    return render_template(
        "player_detail.html",
        player=player,
        pos_abbr=pos_abbr,
        nat_flag=nat_flag,
        team_id=team_id,
        recent_matches=recent_matches,
        leagues=LEAGUES,
        league_code=DEFAULT_LEAGUE,
    )


# ── Template filters ──────────────────────────────────────────────────────────

@app.template_filter("initials")
def initials_filter(name):
    parts = name.split()
    if len(parts) >= 2:
        return parts[0][0] + parts[-1][0]
    return name[:2].upper() if name else "?"


@app.template_filter("flag")
def flag_filter(nationality):
    return COUNTRY_FLAGS.get(nationality or "", "")


@app.template_filter("gpg")
def gpg_filter(entry):
    g = entry.get("goals") or 0
    m = entry.get("playedMatches") or 0
    if m == 0:
        return "—"
    return f"{g/m:.2f}"


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403,
        message="API key missing or invalid. Set FOOTBALL_DATA_API_KEY in your .env file.",
        leagues=LEAGUES, league_code=DEFAULT_LEAGUE), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found.",
        leagues=LEAGUES, league_code=DEFAULT_LEAGUE), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Error fetching data from API.",
        leagues=LEAGUES, league_code=DEFAULT_LEAGUE), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
