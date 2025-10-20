import io, sys, gzip, pandas as pd, requests

OUT = "data/processed/"
YEAR = 2025
ALLOWED_POS = {"QB","RB","WR","TE","K","DST"}

# Known-good public mirrors sometimes relocate; try a couple of common endpoints.
CANDIDATES = [
    # nflverse often mirrors via GitHub raw; this pattern keeps us unblocked.
    "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/data/player_stats/player_stats_2025.csv.gz",
    "https://github.com/nflverse/nflfastR-data/raw/master/data/player_stats/player_stats_2025.csv.gz"
]

def load_any():
    for url in CANDIDATES:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return pd.read_csv(io.BytesIO(r.content), compression="gzip")
        except Exception as e:
            print(f"[WARN] Fetch failed from {url}: {e}")
    return None

def ensure_templates():
    # Minimal headers so Power BI can be wired even offline
    import os
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(columns=["season","week","player","team","position","ppr_points","ppr_avg"]).to_csv(OUT+"players_weekly_2025.csv", index=False)
    pd.DataFrame(columns=["position","player","ppr_avg"]).to_csv(OUT+"top_by_position_2025.csv", index=False)
    pd.DataFrame(columns=["player","ppr_avg"]).to_csv(OUT+"top_dst_2025.csv", index=False)
    print("[OK] Wrote empty templates (offline mode).")

print(f"[INFO] Fetching {YEAR} data…")
df = load_any()

if df is None:
    ensure_templates()
    sys.exit(0)

# Normalize columns
df.columns = [c.lower() for c in df.columns]

# Best-effort mappings across nflverse schemas
name_col = "player_name" if "player_name" in df.columns else ("name" if "name" in df.columns else None)
pos_col  = "position" if "position" in df.columns else None
team_col = "recent_team" if "recent_team" in df.columns else ("team" if "team" in df.columns else None)
wk_col   = "week" if "week" in df.columns else None
gp_col   = "games" if "games" in df.columns else ("games_played" if "games_played" in df.columns else None)
ppr_col  = "fantasy_points_ppr" if "fantasy_points_ppr" in df.columns else None

if not all([name_col, pos_col, team_col, wk_col, ppr_col]):
    print("[WARN] Unexpected schema; writing templates and exiting.")
    ensure_templates()
    sys.exit(0)

df = df.rename(columns={name_col:"player", pos_col:"position", team_col:"team", wk_col:"week"})
df["season"] = YEAR

# Filter allowed fantasy positions (including DST)
df = df[df["position"].isin(ALLOWED_POS)].copy()

# Compute ppr_avg safely
if gp_col and gp_col in df.columns:
    gp = df[gp_col].clip(lower=1)
else:
    # fallback: treat one game per row if gp missing
    gp = 1
df["ppr_points"] = df[ppr_col]
df["ppr_avg"] = df["ppr_points"] / gp

# Persist detailed weekly
weekly_cols = ["season","week","player","team","position","ppr_points","ppr_avg"]
df[weekly_cols].to_csv(OUT+"players_weekly_2025.csv", index=False)

# Top by position (player-level)
top_by_pos = (df.groupby(["position","player"], as_index=False)["ppr_avg"].mean()
                .sort_values(["position","ppr_avg"], ascending=[True, False]))
top_by_pos.to_csv(OUT+"top_by_position_2025.csv", index=False)

# D/ST table
dst = df[df["position"]=="DST"].groupby(["player"], as_index=False)["ppr_avg"].mean().sort_values("ppr_avg", ascending=False)
dst.to_csv(OUT+"top_dst_2025.csv", index=False)

print(f"[OK] Wrote {OUT}players_weekly_2025.csv, top_by_position_2025.csv, top_dst_2025.csv")
