#!/usr/bin/env python
import os, sys, pandas as pd
from datetime import datetime
from pathlib import Path
try:
    from config import FF_CURRENT_SEASON, DATA_DIR, PLAYERS_WEEKLY_CSV, STRICT_2025_ONLY
except Exception as e:
    print(f"[FATAL] Could not import config: {e}"); sys.exit(1)
URL = f"https://github.com/nflverse/nflverse-data/releases/download/players/players_weekly_{FF_CURRENT_SEASON}.csv.gz"
def main():
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Target season: {FF_CURRENT_SEASON}")
    print(f"[INFO] Downloading: {URL}")
    try:
        df = pd.read_csv(URL, compression="gzip", low_memory=False)
    except Exception as e:
        print(f"[ERROR] Failed to read weekly data: {e}"); sys.exit(2)
    season_col = next((c for c in df.columns if c.lower()=="season"), None)
    if season_col is None: print("[ERROR] No 'season' column"); sys.exit(3)
    if STRICT_2025_ONLY:
        df = df[df[season_col] == FF_CURRENT_SEASON].copy()
    present = sorted(map(int, pd.unique(df[season_col].dropna())))
    print(f"[OK] Seasons present after filter: {present}")
    df.to_csv(PLAYERS_WEEKLY_CSV, index=False)
    print(f"[OK] Wrote {PLAYERS_WEEKLY_CSV} with {len(df):,} rows at {datetime.now()}")
if __name__ == "__main__": main()
