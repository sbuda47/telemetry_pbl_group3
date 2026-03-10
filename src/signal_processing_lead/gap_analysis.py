from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ANALYSIS_READY_PATH = PROCESSED_DIR / "turdata_analysis_ready.csv"
GAP_SUMMARY_PATH = PROCESSED_DIR / "turdata_gap_summary.csv"


def longest_true_run(series: pd.Series) -> int:
    max_run = 0
    current_run = 0

    for val in series.fillna(False):
        if bool(val):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0

    return max_run


def build_gap_summary(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    grouped = df.groupby(["pollutant", "sensor_id"], sort=True)

    for (pollutant, sensor_id), group in grouped:
        g = group.sort_values("dt_beg_utc").copy()

        time_diff_hours = g["dt_beg_utc"].diff().dt.total_seconds().div(3600)
        irregular_steps = time_diff_hours.dropna().ne(1).sum()

        missing_mask = g["value"].isna()
        longest_missing_run = longest_true_run(missing_mask)

        results.append({
            "pollutant": pollutant,
            "sensor_id": sensor_id,
            "rows": len(g),
            "missing_rows": int(missing_mask.sum()),
            "missing_pct": 100 * missing_mask.mean(),
            "longest_missing_run_hours": longest_missing_run,
            "irregular_time_steps": int(irregular_steps),
            "time_start": g["dt_beg_utc"].min(),
            "time_end": g["dt_beg_utc"].max(),
        })

    summary = pd.DataFrame(results)

    def recommend(row):
        if row["missing_pct"] <= 5 and row["longest_missing_run_hours"] <= 4:
            return "safe_short_gap_interp"
        elif row["missing_pct"] <= 10 and row["longest_missing_run_hours"] <= 6:
            return "conditional_short_gap_interp"
        else:
            return "avoid_interp_for_main_demo"

    summary["interp_recommendation"] = summary.apply(recommend, axis=1)

    return summary.sort_values(["pollutant", "sensor_id"]).reset_index(drop=True)


if __name__ == "__main__":
    df = pd.read_csv(
        ANALYSIS_READY_PATH,
        low_memory=False
    )

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["dt_end_utc"] = pd.to_datetime(df["dt_end_utc"], errors="coerce", utc=True)

    df = df.dropna(subset=["dt_beg_utc", "dt_end_utc"]).copy()

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    gap_summary = build_gap_summary(df)
    gap_summary.to_csv(GAP_SUMMARY_PATH, index=False)

    print("Saved:")
    print(f" - {GAP_SUMMARY_PATH}")
    print()
    print(gap_summary.head(12).to_string(index=False))