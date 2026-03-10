from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MASTER_PATH = PROCESSED_DIR / "turdata_master_tidy.csv"
QC_PATH = PROCESSED_DIR / "turdata_qc_summary.csv"

SENSOR_SELECTION_PATH = PROCESSED_DIR / "turdata_sensor_selection.csv"
ANALYSIS_READY_PATH = PROCESSED_DIR / "turdata_analysis_ready.csv"

PRIMARY_MAX_MISSING = 5.0
ACCEPTABLE_MAX_MISSING = 10.0


def classify_sensor(row):
    pollutant = row["pollutant"]
    sensor_id = row["sensor_id"]
    missing_pct = row["missing_pct"]

    # Explicit dataset-based exclusion
    if pollutant == "NO2" and sensor_id == "S9":
        return pd.Series({
            "selection_status": "exclude",
            "selection_reason": "Known drift issue from dataset readme"
        })

    # Missing-data rule
    if missing_pct <= PRIMARY_MAX_MISSING:
        return pd.Series({
            "selection_status": "primary",
            "selection_reason": "Missing percentage <= 5%"
        })
    elif missing_pct <= ACCEPTABLE_MAX_MISSING:
        return pd.Series({
            "selection_status": "acceptable",
            "selection_reason": "Missing percentage > 5% and <= 10%"
        })
    else:
        return pd.Series({
            "selection_status": "exclude",
            "selection_reason": "Missing percentage > 10%"
        })


def build_sensor_selection():
    qc = pd.read_csv(QC_PATH)
    decisions = qc.apply(classify_sensor, axis=1)
    selection = pd.concat([qc, decisions], axis=1)
    return selection.sort_values(["pollutant", "sensor_id"]).reset_index(drop=True)


def build_analysis_ready(selection_df):
    master = pd.read_csv(
        MASTER_PATH,
        parse_dates=["dt_beg_utc", "dt_end_utc"]
    )

    approved = selection_df.loc[
        selection_df["selection_status"].isin(["primary", "acceptable"]),
        ["pollutant", "sensor_id"]
    ].drop_duplicates()

    analysis_ready = master.merge(
        approved,
        on=["pollutant", "sensor_id"],
        how="inner"
    )

    # Remove rows explicitly flagged invalid
    analysis_ready = analysis_ready.loc[
        ~analysis_ready["is_invalid_known_issue"].fillna(False)
    ].copy()

    return analysis_ready.sort_values(
        ["pollutant", "sensor_id", "dt_beg_utc"]
    ).reset_index(drop=True)


if __name__ == "__main__":
    selection = build_sensor_selection()
    analysis_ready = build_analysis_ready(selection)

    selection.to_csv(SENSOR_SELECTION_PATH, index=False)
    analysis_ready.to_csv(ANALYSIS_READY_PATH, index=False)

    print("Saved:")
    print(f" - {SENSOR_SELECTION_PATH}")
    print(f" - {ANALYSIS_READY_PATH}")
    print()
    print("Selection summary:")
    print(
        selection.groupby(["pollutant", "selection_status"])
        .size()
        .rename("count")
        .reset_index()
        .to_string(index=False)
    )
    print()
    print(f"Analysis-ready shape: {analysis_ready.shape}")