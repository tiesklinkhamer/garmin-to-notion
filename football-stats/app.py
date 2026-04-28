import os
import math
import requests
from flask import Flask, render_template, request, redirect, abort, jsonify
from functools import lru_cache
from dotenv import load_dotenv
from itertools import product as iproduct

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


def get_ha_tables(league_code):
    """Return (home_table, away_table) as lists of standing rows."""
    data = get_standings(league_code)
    home_t, away_t = [], []
    for group in data.get("standings", []):
        t = group.get("type")
        if t == "HOME":
            home_t = group.get("table", [])
        elif t == "AWAY":
            away_t = group.get("table", [])
    return home_t, away_t


@lru_cache(maxsize=128)
def get_team_matches(team_id, limit=15):
    """Return finished matches for a team (most recent first)."""
    try:
        data = api_get(f"/teams/{team_id}/matches", {"status": "FINISHED", "limit": limit})
        return data.get("matches", [])
    except Exception:
        return []


def _score_val(score_obj, key):
    """Handle both v4 ('home'/'away') and older ('homeTeam'/'awayTeam') score keys."""
    v = score_obj.get(key)
    if v is None:
        alt = "homeTeam" if key == "home" else "awayTeam"
        v = score_obj.get(alt)
    return v


def analyse_team_form(matches, team_id):
    """
    Compute form stats from a list of finished match objects.
    Returns dict with: results (list of dicts), btts_pct, over_1_5_pct,
    over_2_5_pct, over_3_5_pct, avg_scored, avg_conceded, cs_pct, win_pct, form_str.
    """
    results = []
    for m in matches:
        score = m.get("score", {})
        full  = score.get("fullTime", {})
        h_goals = _score_val(full, "home")
        a_goals = _score_val(full, "away")
        if h_goals is None or a_goals is None:
            continue
        h_id = (m.get("homeTeam") or {}).get("id")
        is_home = h_id == team_id
        scored    = h_goals if is_home else a_goals
        conceded  = a_goals if is_home else h_goals
        total     = h_goals + a_goals
        if scored > conceded:
            result = "W"
        elif scored == conceded:
            result = "D"
        else:
            result = "L"
        results.append({
            "match":     m,
            "is_home":   is_home,
            "scored":    scored,
            "conceded":  conceded,
            "total":     total,
            "result":    result,
            "btts":      scored > 0 and conceded > 0,
            "over_1_5":  total > 1,
            "over_2_5":  total > 2,
            "over_3_5":  total > 3,
        })

    n = len(results) or 1
    btts_pct    = round(sum(1 for r in results if r["btts"])     / n * 100)
    over_1_5    = round(sum(1 for r in results if r["over_1_5"]) / n * 100)
    over_2_5    = round(sum(1 for r in results if r["over_2_5"]) / n * 100)
    over_3_5    = round(sum(1 for r in results if r["over_3_5"]) / n * 100)
    avg_scored   = round(sum(r["scored"]   for r in results) / n, 2)
    avg_conceded = round(sum(r["conceded"] for r in results) / n, 2)
    cs_pct       = round(sum(1 for r in results if r["conceded"] == 0) / n * 100)
    win_pct      = round(sum(1 for r in results if r["result"] == "W")  / n * 100)
    form_str     = "".join(r["result"] for r in reversed(results))[-5:]

    return {
        "results":      results,
        "btts_pct":     btts_pct,
        "over_1_5_pct": over_1_5,
        "over_2_5_pct": over_2_5,
        "over_3_5_pct": over_3_5,
        "avg_scored":   avg_scored,
        "avg_conceded": avg_conceded,
        "cs_pct":       cs_pct,
        "win_pct":      win_pct,
        "form_str":     form_str,
    }


def poisson_pmf(k, lam):
    """P(X=k) for Poisson(lam)."""
    if lam <= 0 or k < 0:
        return 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def predict_match(home_ha, away_ha, league_home_avg, league_away_avg):
    """
    Dixon-Coles style Poisson prediction.
    home_ha / away_ha: dicts with 'avg_scored' and 'avg_conceded' from home/away splits.
    Returns dict of outcome probabilities and market percentages.
    """
    h_att = (home_ha.get("avg_scored",   league_home_avg) or league_home_avg) / (league_home_avg or 1.3)
    h_def = (home_ha.get("avg_conceded", league_away_avg) or league_away_avg) / (league_away_avg or 1.1)
    a_att = (away_ha.get("avg_scored",   league_away_avg) or league_away_avg) / (league_away_avg or 1.1)
    a_def = (away_ha.get("avg_conceded", league_home_avg) or league_home_avg) / (league_home_avg or 1.3)

    home_xg = max(0.15, h_att * a_def * league_home_avg)
    away_xg = max(0.15, a_att * h_def * league_away_avg)

    MAX_G = 9
    score_matrix = {}
    for hg in range(MAX_G):
        for ag in range(MAX_G):
            score_matrix[(hg, ag)] = poisson_pmf(hg, home_xg) * poisson_pmf(ag, away_xg)

    home_win = sum(v for (hg, ag), v in score_matrix.items() if hg > ag)
    draw     = sum(v for (hg, ag), v in score_matrix.items() if hg == ag)
    away_win = sum(v for (hg, ag), v in score_matrix.items() if hg < ag)

    total = home_win + draw + away_win or 1.0
    home_win /= total
    draw     /= total
    away_win /= total

    btts    = sum(v for (hg, ag), v in score_matrix.items() if hg > 0 and ag > 0)
    over_15 = sum(v for (hg, ag), v in score_matrix.items() if hg + ag > 1)
    over_25 = sum(v for (hg, ag), v in score_matrix.items() if hg + ag > 2)
    over_35 = sum(v for (hg, ag), v in score_matrix.items() if hg + ag > 3)
    over_45 = sum(v for (hg, ag), v in score_matrix.items() if hg + ag > 4)

    # Most likely score
    best_score = max(score_matrix, key=score_matrix.get)
    best_score_prob = score_matrix[best_score]

    # Top 5 most likely scores
    top_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)[:6]

    return {
        "home_xg":        round(home_xg, 2),
        "away_xg":        round(away_xg, 2),
        "home_win_pct":   round(home_win * 100),
        "draw_pct":       round(draw     * 100),
        "away_win_pct":   round(away_win * 100),
        "btts_pct":       round(btts    * 100),
        "over_1_5_pct":   round(over_15 * 100),
        "over_2_5_pct":   round(over_25 * 100),
        "over_3_5_pct":   round(over_35 * 100),
        "over_4_5_pct":   round(over_45 * 100),
        "best_score":     best_score,
        "best_score_pct": round(best_score_prob * 100),
        "top_scores":     [(s, round(p * 100, 1)) for s, p in top_scores],
    }


def get_league_ha_avgs(league_code):
    """Compute league-wide home and away goals-per-game averages from standings."""
    home_t, away_t = get_ha_tables(league_code)
    def avg_gpg(table):
        total_g = sum(r.get("goalsFor", 0) or 0 for r in table)
        total_m = sum(r.get("playedGames", 0) or 0 for r in table)
        return round(total_g / total_m, 3) if total_m else 1.3
    return avg_gpg(home_t), avg_gpg(away_t)


def get_team_ha_stats(team_id, home_table, away_table):
    """Extract a team's home and away performance from split standings tables."""
    def find(table):
        for row in table:
            if (row.get("team") or {}).get("id") == team_id:
                played = row.get("playedGames") or 1
                gf = row.get("goalsFor", 0) or 0
                ga = row.get("goalsAgainst", 0) or 0
                return {
                    "played":       played,
                    "pts":          row.get("points", 0),
                    "avg_scored":   round(gf / played, 2),
                    "avg_conceded": round(ga / played, 2),
                    "won":          row.get("won", 0),
                    "draw":         row.get("draw", 0),
                    "lost":         row.get("lost", 0),
                }
        return None
    return find(home_table), find(away_table)


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


@app.route("/predict")
def predict():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE

    home_id  = request.args.get("home_id",  type=int)
    away_id  = request.args.get("away_id",  type=int)

    # Load all teams for the selector
    teams_data = get_teams(league_code).get("teams", [])
    teams_data.sort(key=lambda t: t.get("shortName") or t.get("name", ""))

    prediction   = None
    home_team    = None
    away_team    = None
    home_form    = None
    away_form    = None
    home_ha_stats = None
    away_ha_stats = None

    if home_id and away_id and home_id != away_id:
        try:
            home_t, away_t = get_ha_tables(league_code)
            league_home_avg, league_away_avg = get_league_ha_avgs(league_code)

            home_ha, home_as_away = get_team_ha_stats(home_id, home_t, away_t)
            away_as_home, away_ha = get_team_ha_stats(away_id, home_t, away_t)

            # Home team: use their HOME stats for attacking/defending at home
            # Away team: use their AWAY stats for attacking/defending away
            h_stats = home_ha or {}
            a_stats = away_ha or {}

            prediction = predict_match(h_stats, a_stats, league_home_avg, league_away_avg)

            # Get team info
            for t in teams_data:
                if t["id"] == home_id:
                    home_team = t
                if t["id"] == away_id:
                    away_team = t

            # Form analysis (last 15 matches)
            home_matches = get_team_matches(home_id, 15)
            away_matches = get_team_matches(away_id, 15)
            home_form    = analyse_team_form(home_matches, home_id)
            away_form    = analyse_team_form(away_matches, away_id)
            home_ha_stats = {"home": home_ha, "away": home_as_away}
            away_ha_stats = {"home": away_as_home, "away": away_ha}
        except Exception as exc:
            prediction = {"error": str(exc)}

    return render_template(
        "predict.html",
        teams=teams_data,
        league_code=league_code,
        league=LEAGUES[league_code],
        leagues=LEAGUES,
        home_id=home_id,
        away_id=away_id,
        home_team=home_team,
        away_team=away_team,
        prediction=prediction,
        home_form=home_form,
        away_form=away_form,
        home_ha_stats=home_ha_stats,
        away_ha_stats=away_ha_stats,
    )


@app.route("/api/league-stats")
def api_league_stats():
    league_code = request.args.get("league", DEFAULT_LEAGUE)
    if league_code not in LEAGUES:
        league_code = DEFAULT_LEAGUE
    try:
        home_avg, away_avg = get_league_ha_avgs(league_code)
        total_avg = round(home_avg + away_avg, 2)
        # Estimate BTTS and over 2.5 from Poisson with league averages
        btts_est  = round((1 - math.exp(-home_avg)) * (1 - math.exp(-away_avg)) * 100)
        over25_est = round(sum(
            poisson_pmf(hg, home_avg) * poisson_pmf(ag, away_avg)
            for hg in range(9) for ag in range(9)
            if hg + ag > 2
        ) * 100)
        table = get_total_table(league_code)
        home_wins = away_wins = draws = 0
        for row in table:
            # wins from home table
            pass
        home_t, away_t = get_ha_tables(league_code)
        total_h_w = sum(r.get("won", 0) or 0 for r in home_t)
        total_a_w = sum(r.get("won", 0) or 0 for r in away_t)
        total_d   = sum(r.get("draw", 0) or 0 for r in home_t)
        total_m   = sum(r.get("playedGames", 0) or 0 for r in home_t)
        denom = total_m or 1
        return jsonify({
            "home_avg":   home_avg,
            "away_avg":   away_avg,
            "total_avg":  total_avg,
            "btts_pct":   btts_est,
            "over_2_5_pct": over25_est,
            "home_win_pct": round(total_h_w / denom * 100),
            "away_win_pct": round(total_a_w / denom * 100),
            "draw_pct":     round(total_d   / denom * 100),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

    # Detect the team's league from its competitions
    league_code = DEFAULT_LEAGUE
    for comp in (team_data.get("runningCompetitions") or []):
        if comp.get("code") in LEAGUES:
            league_code = comp["code"]
            break

    # Form analysis from last 15 matches
    matches = get_team_matches(team_id, 15)
    form_stats = analyse_team_form(matches, team_id)

    # Home/Away split from league standings
    home_ha = away_ha = None
    try:
        home_t, away_t = get_ha_tables(league_code)
        home_ha, away_ha = get_team_ha_stats(team_id, home_t, away_t)
    except Exception:
        pass

    return render_template(
        "team_detail.html",
        team=team_data,
        squad=squad,
        pos_abbr=POSITION_ABBR,
        pos_class=POSITION_CLASS,
        leagues=LEAGUES,
        league_code=league_code,
        form_stats=form_stats,
        home_ha=home_ha,
        away_ha=away_ha,
        team_id=team_id,
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
