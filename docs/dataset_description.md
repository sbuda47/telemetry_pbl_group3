# Dataset Description

## Project Dataset
This project uses the **TURDATA Prague Urban Air Quality Dataset** as the signal source for the environmental telemetry monitoring system.

The dataset contains real urban air quality measurements collected over time, making it suitable for simulating a practical telemetry pipeline rather than relying on synthetic signals. Since the objective of this project is to design and simulate an **end-to-end environmental telemetry system**, the dataset serves as the real-world equivalent of signals that would normally be acquired from distributed sensing nodes in an environmental monitoring network.

---

## Why This Dataset Was Chosen
The TURDATA dataset was selected because it provides:

- real environmental sensor measurements,
- time-varying pollutant data,
- multiple sensors,
- realistic data quality issues such as missing values and sensor inconsistencies,
- and sufficient structure for preprocessing, signal transmission modelling, digital telemetry, and monitoring.

This makes it highly relevant for telemetry engineering, where the concern is not only transmission of ideal signals, but also preservation of useful information from imperfect real measurements.

---

## Relevance to the TELE 523 Project
The project focuses on **environmental telemetry monitoring using urban air quality data**. The dataset supports the study of telemetry concepts using practical measurement signals such as:

- particulate matter (PM),
- nitrogen dioxide (NO2),
- ozone (O3),
- sulphur dioxide (SO2),
- threshold exceedance behaviour,
- and possible sensor drift.

These signal types are appropriate because they are continuous, meaningful in environmental monitoring, and affected by real operational conditions.

---

## Dataset Structure
From the preprocessing outputs currently generated in this repository, the cleaned master dataset is organized into a structured tabular form with columns such as:

- `dt_beg_utc` — measurement start timestamp,
- `dt_end_utc` — measurement end timestamp,
- `interval_hours` — sampling interval duration,
- `location` — measurement location,
- `measurement_program` — campaign or measurement context,
- `pollutant` — pollutant name,
- `unit` — measurement unit,
- `sensor_id` — sensor identifier,
- `r_...` / value column — recorded signal value and related metadata.

The preprocessing pipeline reshapes and standardizes the data into a long-format master table that is easier to use for signal analysis, telemetry simulation, and monitoring.

---

## Current Processed Outputs
The preprocessing stage currently produces the following key files:

### 1. `data/processed/turdata_master_tidy.csv`
This is the main cleaned dataset used as the foundation for downstream analysis. It contains the structured environmental measurements in a telemetry-ready tabular form.

### 2. `data/processed/turdata_qc_summary.csv`
This file provides a quality-control summary of the cleaned data, including information such as:

- total rows per sensor,
- missing rows,
- known invalid rows,
- minimum and maximum values,
- mean values,
- missing percentage,
- and invalid percentage.

This summary is important because it helps determine which sensor streams are suitable for interpolation, modulation experiments, and monitoring analysis.

---

## Observed Characteristics of the Dataset
Based on preprocessing outputs already generated in this project, the dataset exhibits several practical properties relevant to telemetry design:

- some sensors contain missing measurements,
- signal quality differs between sensors,
- some pollutant-sensor pairs are more reliable than others,
- and there are indications of non-ideal field conditions such as possible drift or irregularity.

These characteristics are useful because they make the project more realistic. In practice, telemetry systems must operate on imperfect data, not only clean textbook signals.

---

## Telemetry Significance of the Dataset
From a telemetry engineering perspective, this dataset is valuable because it supports the full chain of system development:

### Signal acquisition representation
The dataset acts as the source signal that would normally come from remote sensing hardware.

### Preprocessing and conditioning
The data require cleaning, gap analysis, and filtering before transmission-oriented analysis can be performed.

### Transmission modelling
Selected cleaned signals can be used as input to modulation, channel, and demodulation stages.

### Digital telemetry
Continuous-valued signals can be quantized, encoded, and checked for integrity.

### Monitoring and alerting
The recovered or processed signals can be used to detect threshold exceedances, drift behaviour, and other monitoring-relevant events.

---

## Engineering Challenges Introduced by the Dataset
The dataset introduces several realistic engineering challenges that are important for the project:

- handling missing data,
- selecting reliable sensors,
- dealing with inconsistent signal quality,
- preserving useful information through the telemetry chain,
- and ensuring that the final monitoring outputs remain meaningful after signal processing and transmission stages.

These challenges make the dataset suitable for a system-level telemetry project rather than a purely theoretical communication exercise.

---

## Role of the Dataset in the Group Workflow
The dataset is the common foundation for all team members:

- **Signal Processing Lead** uses it for cleaning, reshaping, gap analysis, and filtering.
- **Modulation Lead** uses selected conditioned signals as transmission inputs.
- **Digital Telemetry Lead** uses processed signal values for quantization and encoding.
- **Monitoring Lead** uses reconstructed or processed signals for feature extraction, threshold detection, and drift analysis.
- **System Architect** ensures that the dataset outputs from preprocessing are formatted consistently for all downstream modules.

---

## Summary
The TURDATA Prague Urban Air Quality Dataset is a suitable and realistic data source for this TELE 523 project because it enables the simulation of a complete environmental telemetry system using real sensor measurements. Its structure, variability, and imperfections make it well aligned with the engineering goals of preprocessing, transmission modelling, digital telemetry, monitoring, and full system integration.