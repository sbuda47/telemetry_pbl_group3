from pathlib import Path
import pandas as pd
from scipy.signal import savgol_filter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORT_DIR = PROCESSED_DIR / "selected_segments"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"
INVENTORY_PATH = EXPORT_DIR / "segment_inventory_all_pollutants.csv"
HANDOFF_NOTE_PATH = EXPORT_DIR / "README_handoff_student3.txt"

TARGET_POLLUTANTS = ["NO2", "O3", "PM10", "PM2_5"]
TARGET_SENSORS = ["S5", "S10", "S12", "S14"]

FS = 1.0  # samples per hour
SAVGOL_WINDOW = 11
SAVGOL_POLYORDER = 2
MIN_SAMPLES = 64


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

        s["value_raw"] = s["value"]

        if len(s) < SAVGOL_WINDOW:
            s["value_sg"] = s["value_raw"]
        else:
            temp_signal = s["value_raw"].interpolate(limit_direction="both")
            s["value_sg"] = savgol_filter(
                temp_signal,
                window_length=SAVGOL_WINDOW,
                polyorder=SAVGOL_POLYORDER,
                mode="interp"
            )

        result_parts.append(s)

    return pd.concat(result_parts, ignore_index=True)


def recommend_segment(num_samples: int, remaining_missing: int, segment_id: int) -> tuple[str, str]:
    if num_samples >= MIN_SAMPLES and remaining_missing == 0:
        if segment_id == 2:
            return "yes", "high"
        if segment_id == 1:
            return "yes", "medium"
        return "yes", "low"
    return "no", "low"


if __name__ == "__main__":
    df = pd.read_csv(PSD_READY_PATH, low_memory=False)

    df["dt_beg_utc"] = pd.to_datetime(df["dt_beg_utc"], errors="coerce", utc=True)
    df["dt_end_utc"] = pd.to_datetime(df["dt_end_utc"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for col in ["pollutant", "sensor_id"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["dt_beg_utc", "value"]).copy()

    inventory_rows = []
    exported_files = []

    for pollutant in TARGET_POLLUTANTS:
        pollutant_df = df[
            (df["pollutant"] == pollutant) &
            (df["sensor_id"].isin(TARGET_SENSORS))
        ].copy()

        if pollutant_df.empty:
            continue

        pollutant_df = assign_segments(pollutant_df)
        pollutant_df = apply_savgol_per_segment(pollutant_df)

        for (sensor_id, segment_id), seg in pollutant_df.groupby(["sensor_id", "segment_id"]):
            s = seg.sort_values("dt_beg_utc").copy()

            num_samples = len(s)
            remaining_missing = int(s["value_sg"].isna().sum())
            start_time = s["dt_beg_utc"].min()
            end_time = s["dt_beg_utc"].max()
            duration_hours = (end_time - start_time).total_seconds() / 3600.0

            recommended, priority = recommend_segment(num_samples, remaining_missing, int(segment_id))

            inventory_rows.append({
                "pollutant": pollutant,
                "sensor_id": sensor_id,
                "segment_id": int(segment_id),
                "start_time_utc": start_time,
                "end_time_utc": end_time,
                "num_samples": num_samples,
                "duration_hours": duration_hours,
                "remaining_missing": remaining_missing,
                "sampling_frequency_samples_per_hour": FS,
                "default_modulation_input": "value_sg",
                "recommended_for_modulation": recommended,
                "priority": priority,
            })

            export_cols = [
                "dt_beg_utc",
                "dt_end_utc",
                "pollutant",
                "sensor_id",
                "segment_id",
                "value_raw",
                "value_sg",
            ]

            export_df = s[export_cols].copy()

            out_name = f"{pollutant}_{sensor_id}_segment_{int(segment_id)}.csv"
            export_df.to_csv(EXPORT_DIR / out_name, index=False)
            exported_files.append(out_name)

    inventory_df = pd.DataFrame(inventory_rows).sort_values(
        ["pollutant", "sensor_id", "segment_id"]
    ).reset_index(drop=True)

    inventory_df.to_csv(INVENTORY_PATH, index=False)

    handoff_note = f"""Student 3 Handoff Note
=====================

Pollutants exported:
{", ".join(TARGET_POLLUTANTS)}

Selected sensors:
{", ".join(TARGET_SENSORS)}

Files exported:
- One CSV per pollutant / sensor / continuous segment in: {EXPORT_DIR}

Inventory file:
- {INVENTORY_PATH.name}

Recommended modulation input:
- value_sg  (Savitzky-Golay filtered signal)

Reference raw column:
- value_raw

Sampling frequency:
- {FS} sample per hour

Recommendation rule:
- recommended_for_modulation = yes if num_samples >= {MIN_SAMPLES} and remaining_missing == 0
- priority = high for segment 2
- priority = medium for segment 1
- priority = low for segment 3

Recommended default demo files:
- Use the rows marked recommended_for_modulation = yes
- Prefer priority = high first
- Segment 2 is the main default demo segment where available
"""

    HANDOFF_NOTE_PATH.write_text(handoff_note, encoding="utf-8")

    print(f"Saved inventory: {INVENTORY_PATH}")
    print(f"Saved handoff note: {HANDOFF_NOTE_PATH}")
    print()
    print("Exported files:")
    for name in sorted(exported_files):
        print(f" - {name}")
    print()
    print(inventory_df.to_string(index=False))