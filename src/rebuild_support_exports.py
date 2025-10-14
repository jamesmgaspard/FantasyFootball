# src/rebuild_support_exports.py
import os
import pandas as pd
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(BASE, "data", "processed")

# ---- Controls (can also be overridden via env vars) --------------------------
CURRENT_SEASON = int(os.getenv("FF_CURRENT_SEASON", datetime.now().year))
MAX_WEEKS_CURRENT = int(os.getenv("FF_MAX_WEEKS_CURRENT", "6"))  # cap to first N weeks
ALLOWED_POS = set(x.strip().upper() for x in os.getenv("FF_ALLOWED_POS", "QB,RB,WR,TE,K").split(","))
# -----------------------------------------------------------------------------

CANDIDATES = [
    os.path.join(DATA, "players_weekly.csv"),        # nflverse (preferred)
    os.path.join(DATA, "players_weekly_espn.csv"),   # ESPN fallback (new)
    os.path.join(DATA, "player_weekly.csv"),         # legacy names (if present)
    os.path.join(DATA, "espn_player_weekly.csv"),
    os.path.join(DATA, "weekly_stats.csv"),
]


OUT_TOP_BY_POS = os.path.join(DATA, "top_by_position.csv")
OUT_DST = os.path.join(DATA, "top_dst_2021_2025.csv")

def first_existing(paths):
    for p in paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None

def coerce_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def compute_ppr(df):
    # Use an existing PPR column if present
    for col in ["ppr", "ppr_points", "fantasy_points_ppr"]:
        if col in df.columns:
            return df.rename(columns={col: "ppr_points"})
    # Compute PPR from common columns
    df = coerce_numeric(df, [
        "receptions","receiving_yards","receiving_tds",
        "rushing_yards","rushing_tds",
        "passing_yards","passing_tds","interceptions",
        "fumbles_lost","fumbles"
    ])
    df["ppr_points"] = (
        df.get("receptions",0)*1
        + df.get("receiving_yards",0)/10 + df.get("receiving_tds",0)*6
        + df.get("rushing_yards",0)/10  + df.get("rushing_tds",0)*6
        + df.get("passing_yards",0)/25  + df.get("passing_tds",0)*4
        - df.get("interceptions",0)*2 - df.get("fumbles_lost", df.get("fumbles",0))*2
    )
    return df

def build_top_by_position(player_csv):
    df = pd.read_csv(player_csv)

    # Normalize column names
    rename = {
        "player_display_name":"player",
        "player_name":"player",
        "full_name":"player",
        "recent_team":"team",
        "team_abbr":"team",
        "team":"team",
        "pos":"position",
        "season_year":"season",
        "week_number":"week",
    }
    for k,v in rename.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k:v})

    # Required columns
    for col in ["player","team","position"]:
        if col not in df.columns:
            raise SystemExit(f"[ERROR] Missing '{col}' in {player_csv}. Columns: {list(df.columns)}")

    if "season" not in df.columns:
        df["season"] = datetime.now().year
    if "week" not in df.columns:
        df["week"] = 0

    df = compute_ppr(df)
    df = coerce_numeric(df, ["ppr_points","season","week"])

    # Keep only fantasy-relevant positions (e.g., QB/RB/WR/TE/K)
    if "position" in df.columns:
        df["position"] = df["position"].astype(str).str.upper()
        before = len(df)
        df = df[df["position"].isin(ALLOWED_POS)]
        after = len(df)
        print(f"[INFO] Filtered positions to {sorted(ALLOWED_POS)} ({before}->{after} rows)")

    # Warn if the configured current season isn’t present
    present_seasons = sorted(set(pd.to_numeric(df["season"], errors="coerce").dropna().astype(int)))
    if CURRENT_SEASON not in present_seasons:
        print(f"[WARN] No rows found for season {CURRENT_SEASON} in weekly data. Present: {present_seasons}")

    # Cap the current season to first N weeks (e.g., 2025 weeks 1..6)
    if MAX_WEEKS_CURRENT > 0:
        df = df[~((df["season"] == CURRENT_SEASON) & (df["week"] > MAX_WEEKS_CURRENT))]

    # Aggregate to player-season level
    grp = (df.groupby(["player","team","position","season"], as_index=False)
             .agg(ppr_avg=("ppr_points","mean"),
                  ppr_points=("ppr_points","sum"),
                  weeks=("week","nunique")))

    # Rank by position within season
    grp["rank_in_pos"] = grp.groupby(["season","position"])["ppr_avg"]\
                            .rank(ascending=False, method="dense").astype(int)

    out_cols = ["player","team","position","season","ppr_avg","rank_in_pos"]
    grp[out_cols].sort_values(["season","position","ppr_avg"],
                              ascending=[True, True, False])\
                 .to_csv(OUT_TOP_BY_POS, index=False)
    print(f"[OK] Wrote {OUT_TOP_BY_POS} with {len(grp)} rows "
          f"(capped {CURRENT_SEASON} to week ≤ {MAX_WEEKS_CURRENT})")

def build_dst_stub():
    # Leave as-is; just ensure file exists
    if os.path.exists(OUT_DST) and os.path.getsize(OUT_DST) > 0:
        print(f"[SKIP] D/ST exists: {OUT_DST}")
        return
    pd.DataFrame(columns=["team","position","season","ppr_avg","points_allowed"])\
      .to_csv(OUT_DST, index=False)
    print(f"[OK] Wrote placeholder {OUT_DST}")

def main():
    src = first_existing(CANDIDATES)
    if not src:
        raise SystemExit(
            "[ERROR] No player-level weekly CSV found in data/processed.\n"
            "Expected one of: players_weekly.csv, player_weekly.csv, espn_player_weekly.csv, weekly_stats.csv.\n"
            "Run: python src/fetch_nflverse.py, then rerun."
        )
    print(f"[INFO] Using player source: {src}")
    build_top_by_position(src)
    build_dst_stub()

if __name__ == "__main__":
    main()
