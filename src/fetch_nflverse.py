import os
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED = os.path.join(BASE, "data", "processed")
os.makedirs(PROCESSED, exist_ok=True)
OUT = os.path.join(PROCESSED, "players_weekly.csv")

def try_imports():
    try:
        import nflreadpy as nfl   # optional, may not be installed
        return ("nflreadpy", nfl)
    except Exception:
        try:
            import nfl_data_py as nfl
            return ("nfl_data_py", nfl)
        except Exception as e:
            raise SystemExit(
                "[ERROR] Neither nflreadpy nor nfl_data_py is available.\n"
                "Install one of them:\n"
                "  pip install nflreadpy  (or)\n"
                "  pip install nfl_data_py\n"
                f"Original error: {e}"
            )

def fetch_with_nfl_data_py(nfl):
    import pandas as pd
    from datetime import datetime

    year = datetime.now().year
    years = list(range(year-2, year+1))  # last 3 seasons incl. current
    frames = []

    for y in years:
        try:
            # fetch one season at a time so a missing file doesn't kill the whole import
            df_y = nfl.import_weekly_data([y], downcast=False)
            if isinstance(df_y, pd.DataFrame) and not df_y.empty:
                frames.append(df_y)
                print(f"[OK] weekly {y}: {len(df_y)} rows")
            else:
                print(f"[WARN] weekly {y}: empty")
        except Exception as e:
            print(f"[WARN] weekly {y} unavailable ({e}); skipping")

    if not frames:
        raise SystemExit("[ERROR] No weekly data available from nfl_data_py (all years missing).")

    return pd.concat(frames, ignore_index=True, sort=False)


def coerce_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def normalize_and_write(df):
    # Map common column variants → canonical names
    ren = {
        "player_name": "player",
        "player_display_name": "player",
        "full_name": "player",
        "recent_team": "team",
        "team": "team",
        "position": "position",
        "pos": "position",
        "season": "season",
        "season_year": "season",
        "week": "week",
        "week_number": "week",
        "fantasy_points_ppr": "ppr_points",
        "ppr": "ppr_points",
        "ppr_points": "ppr_points",
    }
    for k, v in ren.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # Compute PPR if not present
    if "ppr_points" not in df.columns:
        candidates = [
            "receptions","receiving_yards","receiving_tds",
            "rushing_yards","rushing_tds",
            "passing_yards","passing_tds","interceptions",
            "fumbles_lost","fumbles"
        ]
        coerce_numeric(df, candidates)
        rec   = df.get("receptions", 0)
        r_yds = df.get("receiving_yards", 0)
        r_td  = df.get("receiving_tds", 0)
        ru_yds= df.get("rushing_yards", 0)
        ru_td = df.get("rushing_tds", 0)
        p_yds = df.get("passing_yards", 0)
        p_td  = df.get("passing_tds", 0)
        ints  = df.get("interceptions", 0)
        fuml  = df.get("fumbles_lost", df.get("fumbles", 0))
        df["ppr_points"] = (
            rec*1
            + r_yds/10.0 + r_td*6
            + ru_yds/10.0 + ru_td*6
            + p_yds/25.0 + p_td*4
            - ints*2 - fuml*2
        )

    # Ensure required columns
    for req in ["player","team","position","season","week","ppr_points"]:
        if req not in df.columns:
            df[req] = None

    keep = ["player","team","position","season","week","ppr_points"]
    out = df[keep].copy()

    # Hygiene + types
    out["player"] = out["player"].astype(str)
    out["team"] = out["team"].astype(str)
    out["position"] = out["position"].astype(str)
    out["season"] = pd.to_numeric(out["season"], errors="coerce").fillna(0).astype(int)
    out["week"] = pd.to_numeric(out["week"], errors="coerce").fillna(0).astype(int)
    out["ppr_points"] = pd.to_numeric(out["ppr_points"], errors="coerce").fillna(0.0)

    out.to_csv(OUT, index=False)
    print(f"[OK] Wrote {OUT} with {len(out)} rows")

def main():
    which, mod = try_imports()
    if which == "nflreadpy":
        df = fetch_with_nflreadpy(mod)
        if df is None or getattr(df, "empty", True):
            which, mod = ("nfl_data_py", __import__("nfl_data_py"))
    if which == "nfl_data_py":
        df = fetch_with_nfl_data_py(mod)

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise SystemExit("[ERROR] Could not fetch weekly player data from nflverse")
    normalize_and_write(df)

if __name__ == "__main__":
    main()
