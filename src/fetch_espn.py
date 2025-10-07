# src/fetch_espn.py
# One clean version: loads .env, validates, connects, writes CSVs, and exits with clear codes.

import os, sys
from pathlib import Path

# ---- 1) Load .env from project root (…\hello\.env) ----
try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] python-dotenv not installed in this venv. Run: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]          # ...\hello
ENV_FILE = PROJECT_ROOT / ".env"
print("[DIAG] .env path:", ENV_FILE)

if not ENV_FILE.exists():
    print("[ERROR] .env file not found at:", ENV_FILE, file=sys.stderr)
    sys.exit(1)

load_dotenv(dotenv_path=str(ENV_FILE))

# ---- 2) Read and validate required values ----
ESPN_S2   = os.getenv("ESPN_S2")
SWID      = os.getenv("SWID")                # must include {curly braces}
LEAGUE_ID = os.getenv("LEAGUE_ID")
SEASON    = os.getenv("SEASON", "2025")

def _mask(v):
    if not v: return "<missing>"
    return f"{v[:4]}...{v[-4:]}" if len(v) >= 8 else "<short>"

print("[DIAG] ESPN_S2:", _mask(ESPN_S2))
print("[DIAG] SWID   :", _mask(SWID))
print("[DIAG] LEAGUE_ID:", LEAGUE_ID, " SEASON:", SEASON)

problems = []
if not ESPN_S2: problems.append("ESPN_S2")
if not SWID or not (SWID.startswith("{") and SWID.endswith("}")):
    problems.append("SWID (must include curly braces)")
if not LEAGUE_ID or not LEAGUE_ID.isdigit():
    problems.append("LEAGUE_ID (digits only)")
try:
    int(SEASON)
except Exception:
    problems.append("SEASON (must be an integer)")

if problems:
    print("[ERROR] Missing/invalid env vars:", ", ".join(problems), file=sys.stderr)
    sys.exit(1)

LEAGUE_ID = int(LEAGUE_ID)
SEASON    = int(SEASON)

# ---- 3) Ensure output folders exist ----
OUT_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- 4) Connect to ESPN ----
try:
    from espn_api.football import League
except ImportError:
    print("[ERROR] espn-api not installed in this venv. Run: pip install espn-api", file=sys.stderr)
    sys.exit(1)

try:
    league = League(league_id=LEAGUE_ID, year=SEASON, espn_s2=ESPN_S2, swid=SWID)
    print(f"[OK] Connected to ESPN league {LEAGUE_ID} year {SEASON}")
except Exception as e:
    print("[ERROR] Failed to connect to ESPN League:", e, file=sys.stderr)
    sys.exit(1)

# ---- 5) Export teams ----
import pandas as pd

try:
    teams = league.teams
    team_rows = [{
        "team_id": t.team_id,
        "team_name": t.team_name,
        "wins": t.wins,
        "losses": t.losses,
        "ties": t.ties
    } for t in teams]
    (OUT_DIR / "espn_teams.csv").write_text("")  # touch/clear (optional)
    pd.DataFrame(team_rows).to_csv(OUT_DIR / "espn_teams.csv", index=False)
    print("[OK] Wrote", OUT_DIR / "espn_teams.csv")
except Exception as e:
    print("[ERROR] Writing teams CSV failed:", e, file=sys.stderr)
    sys.exit(1)

# ---- 6) Export current-week scoreboard ----
try:
    scoreboard = league.scoreboard()
    sb_rows = [{
        "week": league.current_week,
        "home_team": m.home_team.team_name,
        "away_team": m.away_team.team_name,
        "home_score": m.home_score,
        "away_score": m.away_score
    } for m in scoreboard]
    pd.DataFrame(sb_rows).to_csv(OUT_DIR / "espn_scoreboard.csv", index=False)
    print("[OK] Wrote", OUT_DIR / "espn_scoreboard.csv")
except Exception as e:
    print("[ERROR] Writing scoreboard CSV failed:", e, file=sys.stderr)
    sys.exit(1)

# ---- 7) All good ----
print("[DONE] fetch_espn.py completed successfully")
sys.exit(0)
