# src/transform_data.py
# Reads the ESPN CSVs, cleans columns, merges, and writes a master file.
# Exits 0 on success, 1 on failure. Clear messages all the way.

import sys, os
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IN_DIR  = PROJECT_ROOT / "data" / "processed"
OUT_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEAMS_CSV = IN_DIR / "espn_teams.csv"
SB_CSV    = IN_DIR / "espn_scoreboard.csv"

def _fail(msg):
    print("[ERROR]", msg, file=sys.stderr)
    sys.exit(1)

def _ok(msg):
    print("[OK]", msg, flush=True)

# --- 0) sanity checks ---
missing = []
if not TEAMS_CSV.exists(): missing.append(str(TEAMS_CSV))
if not SB_CSV.exists():    missing.append(str(SB_CSV))
if missing:
    _fail(f"Required input file(s) not found: {', '.join(missing)}")

# --- 1) load files ---
try:
    teams = pd.read_csv(TEAMS_CSV)
    sb    = pd.read_csv(SB_CSV)
    _ok(f"Loaded {TEAMS_CSV.name} ({len(teams)} rows)")
    _ok(f"Loaded {SB_CSV.name} ({len(sb)} rows)")
except Exception as e:
    _fail(f"Reading CSVs failed: {e}")

# --- 2) clean column names (lowercase, underscores) ---
def clean_columns(df):
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"[^0-9a-zA-Z]+", "_", regex=True)
                  .str.strip("_")
    )
    return df

teams = clean_columns(teams)
sb    = clean_columns(sb)

# --- 3) derive simple metrics ---
# win_pct for teams
for col in ["wins", "losses", "ties"]:
    if col not in teams.columns:
        teams[col] = 0
games = teams[["wins", "losses", "ties"]].sum(axis=1)
teams["games_played"] = games
teams["win_pct"] = teams["wins"] / teams["games_played"].where(teams["games_played"] != 0, 1)

# total points per matchup (scoreboard)
if all(c in sb.columns for c in ["home_score", "away_score"]):
    sb["total_points"] = sb["home_score"] + sb["away_score"]

# --- 4) write cleaned outputs ---
try:
    teams_out = OUT_DIR / "espn_teams_clean.csv"
    sb_out    = OUT_DIR / "espn_scoreboard_clean.csv"
    master_out_csv  = OUT_DIR / "espn_master.csv"
    master_out_parq = OUT_DIR / "espn_master.parquet"

    # cleaned standalones
    teams.to_csv(teams_out, index=False)
    sb.to_csv(sb_out, index=False)
    _ok(f"Wrote {teams_out}")
    _ok(f"Wrote {sb_out}")

    # lightweight "master" (tagged union)
    t1 = teams.copy(); t1["table"] = "teams"
    t2 = sb.copy();    t2["table"] = "scoreboard"
    master = pd.concat([t1, t2], ignore_index=True, sort=False)

    master.to_csv(master_out_csv, index=False)
    _ok(f"Wrote {master_out_csv}")

    # parquet is optional; don't fail if dependency missing
    try:
        master.to_parquet(master_out_parq, index=False)
        _ok(f"Wrote {master_out_parq}")
    except Exception:
        _ok("Parquet optional dependency missing; wrote CSV only")

except Exception as e:
    _fail(f"Writing outputs failed: {e}")

print("[DONE] transform_data.py completed successfully")
sys.exit(0)
