from pathlib import Path
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"
OUTPUT_PATH = RESULTS_DIR / "filter_metrics_comparison.csv"

TARGET_POLLUTANT = "NO2"
TARGET_SENSORS = ["S5", "S10", "S12", "S14"]

MOVING_AVG_WINDOW = 9
SAVGOL_WINDOW = 11
SAVGOL_POLYORDER = 2


def assign_segments(signal_df: pd.DataFrame) -> pd.DataFrame:
    g = signal_df.copy().sort_values("dt_beg_utc").reset_index(drop=True)
    time_diff_hours = g["dt_beg_utc"].diff().dt.total_seconds().div(3600)
    g["segment_break"] = (time_diff_hours > 1) | (time_diff_hours.isna())
    g["segment_id"] = g["segment_break"].cumsum()
    return g


def apply_filters_per_segment(signal_df: pd.DataFrame) -> pd.DataFrame:
    result_parts = []

    for _, seg in signal_df.groupby("segment_id"):
        s = seg.copy().sort_values("dt_beg_utc")

        s["moving_average"] = s["value"].rolling(
            window=MOVING_AVG_WINDOW,
            center=True,
            min_periods=1
        ).mean()

        if len(s) < SAVGOL_WINDOW:
            s["savgol"] = s["value"]
        else:
            temp_signal = s["value"].interpolate(limit_direction="both")
            s["savgol"] = savgol_filter(
                temp_signal,
                window_length=SAVGOL_WINDOW,
                polyorder=SAVGOL_POLYORDER,
                mode="interp"
            )

        result_parts.append(s)

    return pd.concat(result_parts, ignore_index=True)


def compute_metrics(raw: pd.Series, filt: pd.Series) -> dict:
    raw = pd.to_numeric(raw, errors="coerce")
    filt = pd.to_numeric(filt, errors="coerce")

    valid = raw.notna() & filt.notna()
    raw = raw[valid]
    filt = filt[valid]

    raw_var = raw.var()
    filt_var = filt.var()

    variance_reduction_pct = 100 * (raw_var - filt_var) / raw_var if raw_var > 0 else np.nan
    correlation_with_raw = raw.corr(filt)
    peak_retention_ratio = filt.max() / raw.max() if raw.max() != 0 else np.nan

    return {
        "raw_variance": raw_var,
        "filtered_variance": filt_var,
        "variance_reduction_pct": variance_reduction_pct,
        "correlation_with_raw": correlation_with_raw,
        "peak_retention_ratio": peak_retention_ratio,
    }


if __name__ == "__main__":
    df = pd.read_csv(PSD_READY_PATH, low_memory=False)

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["dt_beg_utc", "value"]).copy()

    results = []

    for sensor in TARGET_SENSORS:
        signal_df = df[
            (df["pollutant"] == TARGET_POLLUTANT) &
            (df["sensor_id"] == sensor)
        ].copy()

        if signal_df.empty:
            continue

        signal_df = assign_segments(signal_df)
        filtered_df = apply_filters_per_segment(signal_df)

        ma_metrics = compute_metrics(filtered_df["value"], filtered_df["moving_average"])
        sg_metrics = compute_metrics(filtered_df["value"], filtered_df["savgol"])

        ma_metrics.update({
            "pollutant": TARGET_POLLUTANT,
            "sensor_id": sensor,
            "filter_type": "moving_average"
        })

        sg_metrics.update({
            "pollutant": TARGET_POLLUTANT,
            "sensor_id": sensor,
            "filter_type": "savitzky_golay"
        })

        results.append(ma_metrics)
        results.append(sg_metrics)

    results_df = pd.DataFrame(results)
    results_df = results_df[
        [
            "pollutant",
            "sensor_id",
            "filter_type",
            "raw_variance",
            "filtered_variance",
            "variance_reduction_pct",
            "correlation_with_raw",
            "peak_retention_ratio",
        ]
    ].sort_values(["sensor_id", "filter_type"]).reset_index(drop=True)

    results_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print()
    print(results_df.to_string(index=False))