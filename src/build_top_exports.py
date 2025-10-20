def export_top32_dst(df):
    """
    Ensure D/ST file has 32 rows per week.
    Auto-detects missing 'week' column and fills with week=1 (or inferred range).
    """
    import pandas as pd

    if df is None or df.empty:
        print("[WARN] No D/ST data found — skipping.")
        return

    # --- Normalize columns ---
    df.columns = [c.lower().strip() for c in df.columns]
    if "week" not in df.columns:
        print("[FIX] Adding filler 'week' column (value = 1).")
        df["week"] = 1
    if "player" in df.columns and "team" not in df.columns:
        print("[FIX] Renaming 'player' → 'team' for D/ST consistency.")
        df = df.rename(columns={"player": "team"})

    # --- Add filler to ensure 32 teams per week ---
    nfl_teams = [
        "ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB",
        "HOU","IND","JAX","KC","LV","LAC","LAR","MIA","MIN","NE","NO","NYG","NYJ",
        "PHI","PIT","SF","SEA","TB","TEN","WAS"
    ]

    out_path = os.path.join("data", "processed", "top_dst_top32_weekly_2025.csv")
    out = []

    for week, g in df.groupby("week"):
        temp = g.copy()
        missing = [t for t in nfl_teams if t not in temp["team"].values]
        for team in missing:
            temp = pd.concat([temp, pd.DataFrame({"team":[team],"ppr_avg":[0],"week":[week]})])
        out.append(temp)

    final = pd.concat(out, ignore_index=True)
    final.to_csv(out_path, index=False)
    print(f"[OK] top_dst_top32_weekly_2025.csv (weeks={final['week'].nunique()})")