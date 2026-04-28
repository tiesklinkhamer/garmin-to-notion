# Football Player Stats

A dark-themed web app showing live football player statistics, season projections, title race predictions, and relegation watch — powered by the free [football-data.org](https://www.football-data.org) API.

## Features

- **Top scorers & assists** — live leaderboard with goals-per-game and progress bars
- **League table** — standings with Champions League / Europa League / relegation zone colouring
- **Insights page** — smart statistics including:
  - Title race with win probability (catchability model)
  - Season projections (goals & assists at current pace)
  - Player ratings (0–10 scale)
  - Combined output leaders (G+A per game)
  - Best attack & defence rankings
  - Form guide (last 5 matches) + trend indicator
  - Relegation battle with points / wins needed
- **Player profiles** — tabs for Overview, Career, Matches, Bio; season projection banner
- **Team pages** — full squad by position with nationality flags
- **Live search** — instant dropdown as you type, searches across all 5 leagues
- **5 leagues** — Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿, La Liga 🇪🇸, Bundesliga 🇩🇪, Serie A 🇮🇹, Ligue 1 🇫🇷

## Setup

### 1. Get a free API key

Register at [football-data.org/client/register](https://www.football-data.org/client/register) — it's instant and free.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the API key

```bash
cp .env.example .env
# Edit .env and paste your API key
```

### 4. Run

```bash
python app.py
# → http://localhost:5000
```

## Tech stack

- **Backend** — Python / Flask
- **Frontend** — vanilla HTML/CSS/JS, Bootstrap Icons
- **Data** — [football-data.org](https://www.football-data.org) free tier API
- **Caching** — `functools.lru_cache` to minimise API calls
