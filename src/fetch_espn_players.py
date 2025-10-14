import os, csv
from datetime import datetime
from dotenv import load_dotenv

# Defaults (override via env vars when you run it)
SEASON     = int(os.getenv("FF_ESPN_SEASON", datetime.now().year))
WEEK_START = int(os.getenv("FF_ESPN_WEEK_START", "1"))
WEEK_END   = int(os.getenv("FF_ESPN_WEEK_END", "6"))

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV  = os.path.join(BASE, ".env")
OUT  = os.path.join(BASE, "data", "processed", "players_weekly_espn.csv")

def _get(obj, *names, default=None):
    """Return the first present attribute among names, else default."""
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default

def _row_from_lineup_item(li, season, week):
    # Handle both legacy and newer espn_api attributes
    name = _get(li, "name", "playerName", default="")
    team = _get(li, "proTeam", default="") or ""
    pos  = _get(li, "position", default="") or ""
    slot = _get(li, "slot_position", default="") or ""
    pts  = _get(li, "points", "ppr_points", default=0.0) or 0.0

    # Skip bench/IR
    if str(slot).upper() in ("BE", "IR"):
        return None

    return {
        "player": str(name),
        "team": str(team).upper(),
        "position": str(pos).upper(),
        "season": int(season),
        "week": int(week),
        "ppr_points": float(pts),
    }

def main():
    # Load .env so we can read LEAGUE_ID / ESPN_S2 / SWID
    if os.path.exists(ENV):
        load_dotenv(ENV, override=True)

    league_id = os.getenv("LEAGUE_ID")
    espn_s2   = os.getenv("ESPN_S2")
    swid      = os.getenv("SWID")

    if not (league_id and espn_s2 and swid):
        raise SystemExit("[ERROR] Missing LEAGUE_ID/ESPN_S2/SWID in environment or .env at project root")

    try:
        from espn_api.football import League
    except Exception as e:
        raise SystemExit("[ERROR] espn-api not installed. Run: pip install espn-api python-dotenv") from e

    league = League(
        league_id=int(league_id),
        year=SEASON,
        espn_s2=espn_s2,
        swid=swid,
    )

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fieldnames = ["player","team","position","season","week","ppr_points"]
    rows = []

    for wk in range(WEEK_START, WEEK_END + 1):
        try:
            box_scores = league.box_scores(wk)
        except Exception as e:
            print(f"[WARN] week {wk}: {e}; skipping")
            continue

        if not box_scores:
            print(f"[WARN] week {wk}: no box scores returned")
            continue

        for bs in box_scores:
            # Home lineup
            for li in (getattr(bs, "home_lineup", None) or []):
                row = _row_from_lineup_item(li, SEASON, wk)
                if row:
                    rows.append(row)
            # Away lineup
            for li in (getattr(bs, "away_lineup", None) or []):
                row = _row_from_lineup_item(li, SEASON, wk)
                if row:
                    rows.append(row)

        print(f"[OK] ESPN pulled week {wk}: {len(rows)} cumulative rows")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[OK] Wrote {OUT} with {len(rows)} rows")

if __name__ == "__main__":
    main()
