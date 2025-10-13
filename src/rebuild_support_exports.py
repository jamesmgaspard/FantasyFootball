import os, sys, warnings
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(BASE, "data", "processed")
SRC  = os.path.join(BASE, "src")

DEFAULT_SEASON = 2025  # adjust if needed

src_file = os.path.join(DATA, "espn_master.csv")
if not os.path.exists(src_file):
    print(f"[ERROR] Missing {src_file}. Aborting.")
    sys.exit(1)

print(f"[INFO] Loading: {src_file}")
df = pd.read_csv(src_file)

# Expected columns (from your log):
# ['team_id','team_name','wins','losses','ties','games_played','win_pct',
#  'table','week','home_team','away_team','home_score','away_score','total_points']

# Normalize to columns our exports will use
if "team_name" in df.columns and "team" not in df.columns:
    df["team"] = df["team_name"]

if "week" not in df.columns:
    df["week"] = pd.NA

if "season" not in df.columns:
    df["season"] = DEFAULT_SEASON
    print(f"[INFO] Added default 'season'={DEFAULT_SEASON}")

# -------------------------------
# Export 1: top_dst_2021_2025.csv
# -------------------------------
# We don't have turnovers/sacks etc., so use a lightweight proxy:
# fewer points allowed across games -> better "defense score".
# We'll compute points_allowed per team-week, then season aggregate.

# Build team-week points allowed from perspective of each team present in rows
def team_points_allowed(row):
    # If row lists both teams & scores, infer PA for each side
    # Fallback to total_points if we can't infer (rare in this file)
    ht, at = row.get("home_team"), row.get("away_team")
    hs, as_ = row.get("home_score"), row.get("away_score")
    if pd.notna(ht) and pd.notna(at) and pd.notna(hs) and pd.notna(as_):
        # Represent two rows: one for home (PA = away_score) and one for away (PA = home_score)
        return pd.DataFrame({
            "team": [ht, at],
            "season": [row["season"], row["season"]],
            "week": [row["week"], row["week"]],
            "points_allowed": [as_, hs],
        })
    # Fallback single-row interpretation
    return pd.DataFrame({
        "team": [row.get("team", "Unknown")],
        "season": [row["season"]],
        "week": [row["week"]],
        "points_allowed": [row.get("total_points", 0)]
    })

rows = []
for _, r in df.iterrows():
    rows.append(team_points_allowed(r))
dst_weekly = pd.concat(rows, ignore_index=True)

# Aggregate by team+season
dst_agg = dst_weekly.groupby(["team","season"], dropna=False, as_index=False).agg(
    games=("week","count"),
    points_allowed_total=("points_allowed","sum"),
    points_allowed_avg=("points_allowed","mean"),
)

# Create a "dst_score" where lower PA => higher score
# Invert avg PA with a simple transform (safe if avg is zero)
dst_agg["dst_score"] = dst_agg["points_allowed_avg"].max() - dst_agg["points_allowed_avg"]

# Keep columns that look like the original downstream expectations
# Use dst_score as a stand-in for ppr metrics so visuals sort sensibly if referenced
dst_export = dst_agg.rename(columns={
    "dst_score": "ppr_avg"   # placeholder metric
})
dst_export["position"] = "D/ST"

dst_keep = ["team","season","position","ppr_avg","points_allowed_avg","games"]
dst_keep = [c for c in dst_keep if c in dst_export.columns]
dst_out = os.path.join(DATA, "top_dst_2021_2025.csv")

# Sort keys and matching ascending flags
sort_by = [c for c in ["season","ppr_avg","points_allowed_avg"] if c in dst_keep]
asc = [True] + [False]*(len(sort_by)-1) if sort_by else []
dst_export[dst_keep].sort_values(by=sort_by, ascending=asc, ignore_index=True).to_csv(dst_out, index=False)
print(f"[OK] Wrote: {dst_out} (rows={len(dst_export)})")

# --------------------------------
# Export 2: top_by_position.csv
# --------------------------------
# We don't have player/position. Emit a minimal, valid table so Power BI links succeed.
# We'll synthesize a "position" of "TEAM" and carry team-season with a neutral score.

team_top = dst_agg.copy()
team_top["position"] = "TEAM"
team_top["player"] = team_top["team"]  # placeholder to satisfy visuals that expect a 'player'-like label
team_top["ppr_avg"] = team_top["points_allowed_avg"] * 0  # neutral zero
team_top["rank_in_pos"] = team_top.groupby(["position","season"])["points_allowed_avg"].rank(ascending=True, method="first")

top_keep = [c for c in ["player","team","position","season","ppr_avg","rank_in_pos"] if c in team_top.columns]
top_out = os.path.join(DATA, "top_by_position.csv")
sort_by = [c for c in ["position","season","rank_in_pos"] if c in top_keep]
asc = [True, True, True][:len(sort_by)]
team_top[top_keep].sort_values(by=sort_by, ascending=asc, ignore_index=True).to_csv(top_out, index=False)
print(f"[OK] Wrote: {top_out} (rows={len(team_top)})")

print("[DONE] Exports complete.")
