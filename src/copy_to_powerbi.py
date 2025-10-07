# src/copy_to_powerbi.py
# Copies processed outputs into powerbi/data for easy PBIX binding.

import sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "data" / "processed"
DST  = ROOT / "powerbi" / "data"
DST.mkdir(parents=True, exist_ok=True)

FILES = [
    "espn_teams_clean.csv",
    "espn_scoreboard_clean.csv",
    "espn_master.csv",
    "espn_master.parquet",   # optional; ignore if missing
]

missing = []
copied = []
for name in FILES:
    s = SRC / name
    d = DST / name
    if s.exists():
        shutil.copy2(s, d)
        copied.append(str(d))
    else:
        missing.append(str(s))

print("[OK] Copied:", *copied, sep="\n  ")
if missing:
    print("[INFO] Missing (skipped):", *missing, sep="\n  ")

sys.exit(0)
