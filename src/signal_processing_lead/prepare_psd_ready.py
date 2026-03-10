from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ANALYSIS_READY_PATH = PROCESSED_DIR / "turdata_analysis_ready.csv"
GAP_SUMMARY_PATH = PROCESSED_DIR / "turdata_gap_summary.csv"
PSD_READY_PATH = PROCESSED_DIR / "turdata_psd_ready.csv"

# Interpolate only short gaps up to this many consecutive hours
SAFE_GAP_LIMIT = 4


def interpolate_short_gaps(group: pd.DataFrame, gap_limit: int = SAFE_GAP_LIMIT) -> pd.DataFrame:
    """
    Interpolate only short internal gaps.
    Does not extrapolate at the start or end.
    Drops rows with invalid timestamps before interpolation.
    """
    g = group.sort_values("dt_beg_utc").copy()

    # Remove rows with invalid timestamps because time interpolation requires
    # a datetime index with no NaNs
    g = g.dropna(subset=["dt_beg_utc"]).copy()

    # Keep original value traceability
    g["value_original"] = g["value"]
    g["was_missing_before"] = g["value"].isna()

    # Remove duplicate timestamps inside each sensor group if any exist
    g = g.drop_duplicates(subset=["dt_beg_utc"], keep="first")

    # Time-based interpolation on datetime index
    g = g.set_index("dt_beg_utc")
    g["value"] = g["value"].interpolate(
        method="time",
        limit=gap_limit,
        limit_area="inside"
    )
    g = g.reset_index()

    g["is_still_missing"] = g["value"].isna()
    g["was_interpolated"] = g["was_missing_before"] & (~g["is_still_missing"])

    return g


def build_psd_ready() -> pd.DataFrame:
    analysis = pd.read_csv(ANALYSIS_READY_PATH, low_memory=False)
    gap_summary = pd.read_csv(GAP_SUMMARY_PATH, low_memory=False)

    analysis["dt_beg_utc"] = pd.to_datetime(analysis["dt_beg_utc"], errors="coerce", utc=True)
    analysis["dt_end_utc"] = pd.to_datetime(analysis["dt_end_utc"], errors="coerce", utc=True)

    # Conservative repair for hourly intervals
    mask_beg_missing = analysis["dt_beg_utc"].isna() & analysis["dt_end_utc"].notna()
    analysis.loc[mask_beg_missing, "dt_beg_utc"] = (
        analysis.loc[mask_beg_missing, "dt_end_utc"] - pd.Timedelta(hours=1)
    )

    mask_end_missing = analysis["dt_end_utc"].isna() & analysis["dt_beg_utc"].notna()
    analysis.loc[mask_end_missing, "dt_end_utc"] = (
        analysis.loc[mask_end_missing, "dt_beg_utc"] + pd.Timedelta(hours=1)
    )

    analysis = analysis.dropna(subset=["dt_beg_utc", "dt_end_utc"]).copy()

    for col in ["pollutant", "sensor_id"]:
        analysis[col] = analysis[col].astype(str).str.strip()
        gap_summary[col] = gap_summary[col].astype(str).str.strip()

    # Keep only sensors that are safe or conditional for short-gap interpolation
    approved = gap_summary.loc[
        gap_summary["interp_recommendation"].isin(
            ["safe_short_gap_interp", "conditional_short_gap_interp"]
        ),
        ["pollutant", "sensor_id", "interp_recommendation"]
    ].drop_duplicates()

    df = analysis.merge(approved, on=["pollutant", "sensor_id"], how="inner")

    result_parts = []
    grouped = df.groupby(["pollutant", "sensor_id"], sort=True)

    for (pollutant, sensor_id), group in grouped:
        interp_group = interpolate_short_gaps(group, gap_limit=SAFE_GAP_LIMIT)
        result_parts.append(interp_group)

    psd_ready = pd.concat(result_parts, ignore_index=True)

    # Helpful final flags
    psd_ready["is_still_missing"] = psd_ready["value"].isna()

    # Final duplicate check across the full dataset
    dup_mask = psd_ready.duplicated(
        subset=["pollutant", "sensor_id", "dt_beg_utc"],
        keep="first"
    )
    print("Duplicate rows found before final cleanup:", int(dup_mask.sum()))

    psd_ready = psd_ready.drop_duplicates(
        subset=["pollutant", "sensor_id", "dt_beg_utc"],
        keep="first"
    ).copy()

    return psd_ready.sort_values(
        ["pollutant", "sensor_id", "dt_beg_utc"]
    ).reset_index(drop=True)


if __name__ == "__main__":
    psd_ready = build_psd_ready()
    psd_ready.to_csv(PSD_READY_PATH, index=False)

    print("Saved:")
    print(f" - {PSD_READY_PATH}")
    print()
    print(f"PSD-ready shape: {psd_ready.shape}")
    print()
    print("Interpolation summary:")
    summary = (
        psd_ready.groupby(["pollutant", "sensor_id"])
        .agg(
            rows=("value", "size"),
            interpolated_points=("was_interpolated", "sum"),
            still_missing=("is_still_missing", "sum"),
        )
        .reset_index()
    )
    print(summary.head(15).to_string(index=False))