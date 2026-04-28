import os
import math
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

# Total games in a full season per league
SEASON_GAMES = {"PL": 38, "PD": 38, "BL1": 34, "SA": 38, "FL1": 34}
# Number of CL spots per league
CL_SPOTS = {"PL": 4, "PD": 4, "BL1": 4, "SA": 4, "FL1": 3}

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


# ── API helpers ───────────────────────────────────────────────────────────────

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


# ── Statistical engine ────────────────────────────────────────────────────────

def compute_insights(scorers, table, league_code):
    """
    Derive smart statistics from raw API data:
    - Season projections (goals/assists at current pace over full season)
    - Player ratings (weighted goals+assists per game, 0-10 scale)
    - Involvement leaders (combined output per game)
    - Hidden gems (high efficiency, low public rank)
    - Title probability (catchability model based on gap, games remaining, PPG)
    - Relegation watch (points needed, wins needed)
    - Team attack/defence ratings
    - Form trend from form string
    """
    sg  = SEASON_GAMES.get(league_code, 38)
    cl  = CL_SPOTS.get(league_code, 4)
    n   = len(table)
    played_ref = table[0]["playedGames"] if table else 1

    # ── Scorer enrichment ─────────────────────────────────────────────────────
    scorer_stats = []
    for i, entry in enumerate(scorers):
        played   = entry.get("playedMatches") or 1
        goals    = entry.get("goals")   or 0
        assists  = entry.get("assists") or 0
        gpg      = goals   / played
        apg      = assists / played
        involvement = (goals + assists) / played
        # Rating: weighted (G×2.5 + A×1.5) per game, calibrated so ~1 G/game = 8.3
        raw = (goals * 2.5 + assists * 1.5) / played
        rating = round(min(10.0, raw / 3.0 * 10), 1)
        scorer_stats.append({
            **entry,
            "rank":               i + 1,
            "gpg":                round(gpg, 2),
            "apg":                round(apg, 2),
            "involvement":        round(involvement, 2),
            "rating":             rating,
            "projected_goals":    round(gpg * sg),
            "projected_assists":  round(apg * sg),
        })

    by_involvement = sorted(scorer_stats, key=lambda x: x["involvement"],     reverse=True)
    by_gpg         = sorted(scorer_stats, key=lambda x: x["gpg"],             reverse=True)
    by_proj        = sorted(scorer_stats, key=lambda x: x["projected_goals"], reverse=True)

    best_pace    = by_proj[0] if by_proj else None
    top_creator  = by_involvement[0] if by_involvement else None
    # Hidden gem: ranks outside top 5 by total goals but top 3 by efficiency
    hidden_gem   = next((s for s in by_gpg[:3] if s["rank"] > 5), None)

    # ── Team enrichment ───────────────────────────────────────────────────────
    team_stats = []
    for row in table:
        played  = row.get("playedGames") or 1
        pts     = row.get("points") or 0
        ppg     = pts / played
        rem     = sg - played
        gf      = row.get("goalsFor",     0) or 0
        ga      = row.get("goalsAgainst", 0) or 0
        gd      = row.get("goalDifference", 0)
        form    = row.get("form") or ""          # e.g. "WWDLW" last 5

        form_pts    = form.count("W") * 3 + form.count("D")
        form_games  = len([c for c in form if c in "WDL"])
        form_ppg    = form_pts / form_games if form_games else ppg
        # Recent form vs season average — are they trending up or down?
        trend = round(form_ppg - ppg, 2)

        team_stats.append({
            **row,
            "ppg":            round(ppg, 2),
            "projected_pts":  round(ppg * sg),
            "remaining":      rem,
            "max_possible":   pts + rem * 3,
            "gpg_att":        round(gf / played, 2) if gf else 0,
            "gpg_def":        round(ga / played, 2) if ga else 0,
            "form_str":       form,
            "form_ppg":       round(form_ppg, 2),
            "trend":          trend,
        })

    # Safe threshold = points held by team just above relegation zone (17th in 20)
    rel_edge = n - 3  # first safe position (0-indexed: index n-4 = 17th in 20-team)
    safe_pts = team_stats[rel_edge - 1]["points"] if n > 3 else 0

    # CL borderline points
    cl_pts = team_stats[cl - 1]["points"] if len(team_stats) >= cl else 0

    for t in team_stats:
        t["pts_to_cl"]    = max(0, cl_pts - t["points"] + 1)
        t["pts_to_safe"]  = max(0, safe_pts - t["points"] + 1)
        # ceiling division: wins needed
        t["wins_to_safe"] = math.ceil(t["pts_to_safe"] / 3) if t["pts_to_safe"] > 0 else 0

    # ── Title probability (catchability model) ────────────────────────────────
    if team_stats:
        leader_pts = team_stats[0]["points"]
        weights = []
        for t in team_stats:
            gap = leader_pts - t["points"]
            rem = t["remaining"]
            if rem <= 0:
                w = 100.0 if gap == 0 else 0.0
            elif gap == 0:
                # Leader advantage: boost by PPG
                w = 70.0 + t["ppg"] * 5
            elif gap > rem * 3:
                # Mathematically impossible
                w = 0.0
            else:
                # Catchability decays quadratically with gap relative to remaining
                catchability = 1.0 - (gap / (rem * 3))
                # Weight recent form more than season average
                form_boost = max(0, t["trend"]) * 10
                w = max(0.0, (catchability ** 2) * 80 + form_boost)
            weights.append(w)
            t["title_weight"] = w

        total_w = sum(weights) or 1.0
        for t in team_stats:
            t["title_prob"] = round(t["title_weight"] / total_w * 100)

    # ── Attack / Defence rankings ─────────────────────────────────────────────
    best_attack  = sorted(team_stats, key=lambda t: t["gpg_att"],  reverse=True)[:5]
    best_defence = sorted(team_stats, key=lambda t: t["gpg_def"])[:5]   # lower is better

    return {
        "scorer_stats":    scorer_stats,
        "by_involvement":  by_involvement,
        "by_gpg":          by_gpg,
        "by_proj":         by_proj,
        "best_pace":       best_pace,
        "top_creator":     top_creator,
        "hidden_gem":      hidden_gem,
        "team_stats":      team_stats,
        "best_attack":     best_attack,
        "best_defence":    best_defence,
        "season_games":    sg,
        "games_played":    played_ref,
        "games_remaining": sg - played_ref,
        "cl_spots":        cl,
        "safe_pts":        safe_pts,
        "cl_pts":          cl_pts,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE

    scorers_data  = get_scorers(league_code)
    scorers       = scorers_data.get("scorers", [])
    table         = get_total_table(league_code)
    insights      = compute_insights(scorers, table, league_code)

    max_goals     = max((e.get("goals")   or 0 for e in scorers), default=1) or 1
    max_assists   = max((e.get("assists") or 0 for e in scorers), default=1) or 1
    scorers_by_assists = sorted(scorers, key=lambda x: (x.get("assists") or 0), reverse=True)

    return render_template(
        "index.html",
        scorers=scorers,
        scorers_by_assists=scorers_by_assists,
        max_goals=max_goals,
        max_assists=max_assists,
        table=table,
        insights=insights,
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
        season=scorers_data.get("season", {}),
    )


@app.route("/insights/<league_code>")
def insights_page(league_code):
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE
    scorers_data = get_scorers(league_code)
    scorers      = scorers_data.get("scorers", [])
    table        = get_total_table(league_code)
    insights     = compute_insights(scorers, table, league_code)
    return render_template(
        "insights.html",
        insights=insights,
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
            "id":      r["player"]["id"],
            "name":    r["player"]["name"],
            "team":    (r["team"] or {}).get("shortName") or (r["team"] or {}).get("name", ""),
            "goals":   r["goals"],
            "assists": r["assists"],
            "nat":     r["player"].get("nationality", ""),
            "league":  r["league"]["short"],
        }
        for r in player_results[:7]
    ]
    teams = [
        {
            "id":     r["team"]["id"],
            "name":   r["team"].get("shortName") or r["team"]["name"],
            "crest":  r["team"].get("crest", ""),
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

    # Compute player-specific projections by searching scorers across leagues
    player_proj = None
    for code in LEAGUES:
        try:
            for entry in get_scorers(code).get("scorers", []):
                if entry["player"]["id"] == player_id:
                    sg = SEASON_GAMES.get(code, 38)
                    played  = entry.get("playedMatches") or 1
                    goals   = entry.get("goals")   or 0
                    assists = entry.get("assists")  or 0
                    gpg  = goals   / played
                    apg  = assists / played
                    raw  = (goals * 2.5 + assists * 1.5) / played
                    rating = round(min(10.0, raw / 3.0 * 10), 1)
                    player_proj = {
                        "goals":             goals,
                        "assists":           assists,
                        "played":            played,
                        "gpg":               round(gpg, 2),
                        "apg":               round(apg, 2),
                        "involvement":       round((goals + assists) / played, 2),
                        "rating":            rating,
                        "projected_goals":   round(gpg * sg),
                        "projected_assists": round(apg * sg),
                        "season_games":      sg,
                        "league_code":       code,
                        "league":            LEAGUES[code],
                    }
                    break
        except Exception:
            pass
        if player_proj:
            break

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
        player_proj=player_proj,
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

@app.template_filter("abs")
def abs_filter(value):
    return abs(value)

@app.template_filter("form_dots")
def form_dots_filter(form_str):
    """Convert 'WWDLW' → list of ('W','win'), ('W','win'), … for template rendering."""
    mapping = {"W": "win", "D": "draw", "L": "loss"}
    return [(c, mapping.get(c, "")) for c in (form_str or "") if c in mapping]


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
