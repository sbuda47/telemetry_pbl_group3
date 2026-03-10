from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"

TARGET_POLLUTANT = "NO2"
TARGET_SENSORS = ["S10", "S12", "S14", "S5"]

MOVING_AVG_WINDOW = 9
SAVGOL_WINDOW = 11
SAVGOL_POLYORDER = 2


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


def plot_filters(filtered_df: pd.DataFrame, pollutant: str, sensor: str):
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    ax1, ax2, ax3 = axes

    RAW_COLOR = "tab:blue"
    MA_COLOR = "tab:orange"
    SG_COLOR = "tab:green"

    first_segment = True

    for _, seg in filtered_df.groupby("segment_id"):
        ax1.plot(
            seg["dt_beg_utc"], seg["value"],
            color=RAW_COLOR,
            label="Raw signal" if first_segment else ""
        )

        ax2.plot(
            seg["dt_beg_utc"], seg["value"],
            color=RAW_COLOR,
            alpha=0.35,
            label="Raw signal" if first_segment else ""
        )
        ax2.plot(
            seg["dt_beg_utc"], seg["moving_average"],
            color=MA_COLOR,
            label="Moving average" if first_segment else ""
        )

        ax3.plot(
            seg["dt_beg_utc"], seg["value"],
            color=RAW_COLOR,
            alpha=0.35,
            label="Raw signal" if first_segment else ""
        )
        ax3.plot(
            seg["dt_beg_utc"], seg["savgol"],
            color=SG_COLOR,
            label="Savitzky-Golay" if first_segment else ""
        )

        first_segment = False

    ax1.set_title(f"Raw signal: {pollutant} - {sensor}")
    ax2.set_title("Moving average filtering")
    ax3.set_title("Savitzky-Golay filtering")

    ax1.set_ylabel(pollutant)
    ax2.set_ylabel(pollutant)
    ax3.set_ylabel(pollutant)
    ax3.set_xlabel("Time (UTC)")

    for ax in axes:
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    out_path = FIGURES_DIR / f"filter_compare_subplots_{pollutant}_{sensor}.png"
    plt.savefig(out_path, dpi=300)
    plt.close()

    print(f"Saved figure: {out_path}")


if __name__ == "__main__":
    df = pd.read_csv(PSD_READY_PATH, low_memory=False)

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["dt_beg_utc"]).copy()

    for sensor in TARGET_SENSORS:
        signal_df = load_signal(df, TARGET_POLLUTANT, sensor)

        if signal_df.empty:
            print(f"No data found for {TARGET_POLLUTANT} {sensor}")
            continue

        signal_df = assign_segments(signal_df)
        filtered_df = apply_filters_per_segment(signal_df)
        plot_filters(filtered_df, TARGET_POLLUTANT, sensor)