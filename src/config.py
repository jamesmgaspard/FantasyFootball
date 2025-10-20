import os
FF_CURRENT_SEASON = 2025
FF_ALLOWED_SEASONS = [2025]
FF_ALLOWED_POS = os.getenv("FF_ALLOWED_POS", "QB,RB,WR,TE,K").split(",")
FF_MAX_WEEKS_CURRENT = int(os.getenv("FF_MAX_WEEKS_CURRENT", "18"))
DATA_DIR = os.getenv("FF_DATA_DIR", "data/processed")
PLAYERS_WEEKLY_CSV = os.path.join(DATA_DIR, "players_weekly.csv")
TOP_BY_POSITION_CSV = os.path.join(DATA_DIR, "top_by_position.csv")
TOP_DST_CSV = os.path.join(DATA_DIR, "top_dst_2021_2025.csv")
STRICT_2025_ONLY = True
