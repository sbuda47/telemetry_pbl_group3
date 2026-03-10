from pathlib import Path
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter, welch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"
OUTPUT_PATH = RESULTS_DIR / "psd_summary_NO2.csv"

TARGET_POLLUTANT = "NO2"
TARGET_SENSORS = ["S5", "S10", "S12", "S14"]

FS = 1.0  # samples per hour
SAVGOL_WINDOW = 11
SAVGOL_POLYORDER = 2
NPERSEG = 256
NOVERLAP = 128


def assign_segments(signal_df: pd.DataFrame) -> pd.DataFrame:
    g = signal_df.copy().sort_values("dt_beg_utc").reset_index(drop=True)
    time_diff_hours = g["dt_beg_utc"].diff().dt.total_seconds().div(3600)
    g["segment_break"] = (time_diff_hours > 1) | (time_diff_hours.isna())
    g["segment_id"] = g["segment_break"].cumsum()
    return g


def apply_savgol_per_segment(signal_df: pd.DataFrame) -> pd.DataFrame:
    result_parts = []

    for _, seg in signal_df.groupby("segment_id"):
        s = seg.copy().sort_values("dt_beg_utc")

        if len(s) < SAVGOL_WINDOW:
            s["value_sg"] = s["value"]
        else:
            temp_signal = s["value"].interpolate(limit_direction="both")
            s["value_sg"] = savgol_filter(
                temp_signal,
                window_length=SAVGOL_WINDOW,
                polyorder=SAVGOL_POLYORDER,
                mode="interp"
            )

        result_parts.append(s)

    return pd.concat(result_parts, ignore_index=True)


def band_power(freqs, pxx, fmin, fmax):
    mask = (freqs >= fmin) & (freqs < fmax)
    if mask.sum() == 0:
        return np.nan
    return np.trapezoid(pxx[mask], freqs[mask])


if __name__ == "__main__":
    df = pd.read_csv(PSD_READY_PATH, low_memory=False)

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["dt_beg_utc", "value"]).copy()

    rows = []

    for sensor in TARGET_SENSORS:
        signal_df = df[
            (df["pollutant"] == TARGET_POLLUTANT) &
            (df["sensor_id"] == sensor)
        ].copy()

        if signal_df.empty:
            continue

        signal_df = assign_segments(signal_df)
        filtered_df = apply_savgol_per_segment(signal_df)

        for segment_id, seg in filtered_df.groupby("segment_id"):
            s = seg.sort_values("dt_beg_utc").dropna(subset=["value_sg"]).copy()

            if len(s) < 64:
                continue

            seg_nperseg = min(NPERSEG, len(s))
            seg_noverlap = seg_nperseg // 2

            x = s["value_sg"].to_numpy()

            freqs, pxx = welch(
                x,
                fs=FS,
                window="hann",
                nperseg=seg_nperseg,
                noverlap=seg_noverlap,
                detrend="constant",
                scaling="density"
            )

            freqs_cpd = freqs * 24

            total_power = np.trapezoid(pxx, freqs_cpd)
            low_power = band_power(freqs_cpd, pxx, 0, 1)
            mid_power = band_power(freqs_cpd, pxx, 1, 4)
            high_power = band_power(freqs_cpd, pxx, 4, 12)

            dom_idx = np.argmax(pxx)
            dominant_freq_cpd = freqs_cpd[dom_idx]

            rows.append({
                "pollutant": TARGET_POLLUTANT,
                "sensor_id": sensor,
                "segment_id": int(segment_id),
                "total_power": total_power,
                "low_power_0_1_cpd": low_power,
                "mid_power_1_4_cpd": mid_power,
                "high_power_4_12_cpd": high_power,
                "low_power_ratio": low_power / total_power if total_power > 0 else np.nan,
                "mid_power_ratio": mid_power / total_power if total_power > 0 else np.nan,
                "high_power_ratio": high_power / total_power if total_power > 0 else np.nan,
                "dominant_frequency_cpd": dominant_freq_cpd
            })

    summary_df = pd.DataFrame(rows).sort_values(["sensor_id", "segment_id"]).reset_index(drop=True)
    summary_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print()
    print(summary_df.to_string(index=False))