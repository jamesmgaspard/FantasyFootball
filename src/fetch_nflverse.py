import nflreadpy as nfl
import pandas as pd

SEASONS = [2023, 2024, 2025]  # adjust if you want

# 1) Load weekly player-level stats (Polars DataFrame)
pl_df = nfl.load_player_stats(SEASONS, summary_level="week")  # weekly stats
# docs: https://nflreadpy.nflverse.com (Usage + API), functions list shows load_player_stats
# returns Polars -> convert to pandas to save CSV
off = pl_df.to_pandas()

# 2) Save the full table (big)
off.to_csv("data/processed/weekly_offense.csv", index=False)

# 3) Save a light model for Power BI (name/team/pos + PPR if present)
keep = [c for c in ("season","week","player_id","player_name","position","team","fantasy_points_ppr") if c in off.columns]
off.loc[:, keep].to_csv("data/processed/model_players_weekly.csv", index=False)

print("✅ nflverse done: wrote weekly_offense.csv and model_players_weekly.csv")
