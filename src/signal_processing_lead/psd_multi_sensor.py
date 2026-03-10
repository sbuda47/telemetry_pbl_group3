from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter, welch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"

TARGET_POLLUTANT = "NO2"
TARGET_SENSORS = ["S5", "S10", "S12", "S14"]

# Hourly data -> 1 sample per hour
FS = 1.0

# Savitzky-Golay settings
SAVGOL_WINDOW = 11
SAVGOL_POLYORDER = 2

# Welch settings
NPERSEG = 256
NOVERLAP = 128


def load_signal(df: pd.DataFrame, pollutant: str, sensor: str) -> pd.DataFrame:
    signal_df = df[
        (df["pollutant"] == pollutant) &
        (df["sensor_id"] == sensor)
    ].copy()

    signal_df = signal_df.sort_values("dt_beg_utc").reset_index(drop=True)
    return signal_df


def assign_segments(signal_df: pd.DataFrame) -> pd.DataFrame:
    g = signal_df.copy()
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


def plot_sensor_psd(ax, filtered_df: pd.DataFrame, sensor: str):
    usable_segments = 0

    for segment_id, seg in filtered_df.groupby("segment_id"):
        s = seg.sort_values("dt_beg_utc").copy()
        s = s.dropna(subset=["value_sg"]).copy()

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
        ax.semilogy(freqs_cpd, pxx, label=f"Seg {segment_id}")
        usable_segments += 1

    ax.set_title(f"{TARGET_POLLUTANT} - {sensor}")
    ax.set_xlabel("Frequency (cycles/day)")
    ax.set_ylabel("PSD")
    ax.grid(True, alpha=0.3)

    if usable_segments > 0:
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No usable segment",
                ha="center", va="center", transform=ax.transAxes)


if __name__ == "__main__":
    df = pd.read_csv(PSD_READY_PATH, low_memory=False)

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["dt_beg_utc", "value"]).copy()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    axes = axes.flatten()

    for ax, sensor in zip(axes, TARGET_SENSORS):
        signal_df = load_signal(df, TARGET_POLLUTANT, sensor)

        if signal_df.empty:
            ax.text(0.5, 0.5, f"No data for {sensor}",
                    ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{TARGET_POLLUTANT} - {sensor}")
            continue

        signal_df = assign_segments(signal_df)
        filtered_df = apply_savgol_per_segment(signal_df)
        plot_sensor_psd(ax, filtered_df, sensor)

    plt.suptitle(f"Welch PSD comparison across sensors ({TARGET_POLLUTANT}, Savitzky-Golay filtered)")
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    out_path = FIGURES_DIR / f"psd_multi_sensor_{TARGET_POLLUTANT}.png"
    plt.savefig(out_path, dpi=300)
    plt.show()

    print(f"Saved figure: {out_path}")