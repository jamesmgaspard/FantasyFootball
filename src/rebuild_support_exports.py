#!/usr/bin/env python
import os, sys, pandas as pd
from pathlib import Path
from datetime import datetime
try:
    from config import (
        FF_CURRENT_SEASON, FF_ALLOWED_POS, FF_MAX_WEEKS_CURRENT,
        DATA_DIR, PLAYERS_WEEKLY_CSV, TOP_BY_POSITION_CSV, TOP_DST_CSV, STRICT_2025_ONLY
    )
except Exception as e:
    print(f"[FATAL] Could not import config: {e}"); sys.exit(1)
def first_existing(cols, candidates):
    for n in candidates:
        if n in cols: return n
    return None
def main():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(PLAYERS_WEEKLY_CSV):
        print(f"[ERROR] Missing {PLAYERS_WEEKLY_CSV}. Run fetch_nflverse.py first."); sys.exit(2)
    df = pd.read_csv(PLAYERS_WEEKLY_CSV, low_memory=False)
    cols = set(df.columns)
    season = first_existing(cols, ["season","Season"])
    week   = first_existing(cols, ["week","Week"])
    pos    = first_existing(cols, ["position","pos","Position","Pos"])
    name   = first_existing(cols, ["player_name","full_name","name","Name"])
    team   = first_existing(cols, ["recent_team","team","Team"])
    pid    = first_existing(cols, ["player_id","gsis_id","pfr_id","nfl_id","player","id"])
    ppr    = first_existing(cols, ["fantasy_points_ppr","ppr_points","ppr"])
    for need in [season, week, pos, name]:
        if need is None:
            print("[ERROR] Missing a required column (season/week/position/name)."); sys.exit(3)
    if STRICT_2025_ONLY:
        df = df[df[season] == FF_CURRENT_SEASON].copy()
    try:
        df[week] = pd.to_numeric(df[week], errors="coerce")
        df = df[df[week] <= FF_MAX_WEEKS_CURRENT]
    except Exception: pass
    df[pos] = df[pos].astype(str).str.upper()
    df = df[df[pos].isin([p.upper() for p in FF_ALLOWED_POS])].copy()
    if ppr is None:
        df["__ppr_points__"] = 0.0; ppr = "__ppr_points__"
    keys = ([pid] if pid else []) + [name, pos, season] + ([team] if team else [])
    agg = df.groupby(keys, dropna=False)[ppr].agg(ppr_points="sum", games_played="count").reset_index()
    agg["ppr_avg"] = (agg["ppr_points"] / agg["games_played"]).round(2)
    agg = agg.sort_values(["ppr_avg","ppr_points"], ascending=[False, False])
    agg.to_csv(TOP_BY_POSITION_CSV, index=False)
    print(f"[OK] Wrote {TOP_BY_POSITION_CSV} with {len(agg):,} rows at {datetime.now()}")
    if not os.path.exists(TOP_DST_CSV):
        pd.DataFrame({"note":["placeholder for PBIX stability"],"timestamp":[datetime.now()]}).to_csv(TOP_DST_CSV, index=False)
        print(f"[SKIP] D/ST not computed (placeholder created): {TOP_DST_CSV}")
if __name__ == "__main__": main()
