Student 3 Handoff Note
=====================

Pollutants exported:
NO2, O3, PM10, PM2_5

Selected sensors:
S5, S10, S12, S14

Files exported:
- One CSV per pollutant / sensor / continuous segment in: D:\Telemetry_PBL_Group3\data\processed\selected_segments

Inventory file:
- segment_inventory_all_pollutants.csv

Recommended modulation input:
- value_sg  (Savitzky-Golay filtered signal)

Reference raw column:
- value_raw

Sampling frequency:
- 1.0 sample per hour

Recommendation rule:
- recommended_for_modulation = yes if num_samples >= 64 and remaining_missing == 0
- priority = high for segment 2
- priority = medium for segment 1
- priority = low for segment 3

Recommended default demo files:
- Use the rows marked recommended_for_modulation = yes
- Prefer priority = high first
- Segment 2 is the main default demo segment where available



# Student 3 Handoff: Modulation-Ready Environmental Telemetry Segments

## Purpose

This folder contains the **modulation-ready signal exports** prepared by **Student 2 (Signal Processing Lead)** for **Student 3 (Modulation Lead)**.

These files are part of the TELE523 end-to-end telemetry pipeline:

**Real dataset → Preprocessing → Modulation → Channel → Demodulation → Digital telemetry → Feature extraction → Monitoring output**. :contentReference[oaicite:1]{index=1}

The exported segments are intended to be used directly as **input signals for modulation experiments** such as:
- AM
- FM
- ASK
- FSK
- PSK

---

## Pollutants included

The original TURDATA raw air-quality package includes the following pollutant files:  
- `NO2_RAW_LCSs_TURDATA.xlsx`
- `O3_RAW_LCSs_TURDATA.xlsx`
- `PM10_RAW_LCSs_TURDATA.xlsx`
- `PM2_5_RAW_LCSs_TURDATA.xlsx` :contentReference[oaicite:2]{index=2}

This handoff export includes modulation-ready segments for:
- **NO2**
- **O3**
- **PM10**
- **PM2_5**

---

## Files in this folder

This folder contains three types of outputs:

### 1. Segment inventory
- `segment_inventory_all_pollutants.csv`

This is the main reference table for Student 3. It lists:
- pollutant
- sensor ID
- segment ID
- start time
- end time
- number of samples
- duration
- remaining missing values
- sampling frequency
- recommended modulation input
- recommendation status
- priority level

### 2. One CSV per pollutant / sensor / segment
Examples:
- `NO2_S10_segment_2.csv`
- `O3_S12_segment_2.csv`
- `PM10_S5_segment_1.csv`
- `PM2_5_S10_segment_3.csv`

Each file contains one **continuous, processed telemetry signal segment**.

### 3. This README
- `README_handoff_student3.md`

This explains what the files contain and how to use them.

---

## What was done to these signals before export

The exported files were not taken directly from the raw dataset. They were prepared through the signal-processing workflow assigned to Student 2, which includes preprocessing, filtering, PSD, and segment selection. :contentReference[oaicite:3]{index=3}

### Processing steps already completed

#### 1. Raw dataset loading and restructuring
The pollutant files were loaded and converted into a clean time-series processing format.

#### 2. Timestamp handling
The signals were aligned using the dataset timestamps and treated as **hourly sampled data**.

#### 3. Sensor quality control
Signals were screened using missing-data thresholds and known quality issues.

#### 4. Gap-aware cleaning
Short internal gaps were handled conservatively. Long broken periods were not blindly joined.

#### 5. Segment selection
Continuous signal blocks were identified and separated into **segments** wherever large time gaps occurred.

#### 6. Filtering
Savitzky–Golay filtering was chosen as the main smoothing method because it gave the best balance between:
- noise reduction
- retention of original signal structure
- better suitability for later PSD and feature extraction

#### 7. Export formatting
Each continuous usable segment was exported into its own CSV file for direct use by Student 3.

---

## Columns inside each exported segment CSV

Each segment file contains:

- `dt_beg_utc`  
  Segment sample start timestamp

- `dt_end_utc`  
  Segment sample end timestamp

- `pollutant`  
  One of `NO2`, `O3`, `PM10`, `PM2_5`

- `sensor_id`  
  Sensor identifier, e.g. `S10`

- `segment_id`  
  Continuous segment number within that pollutant/sensor

- `value_raw`  
  Cleaned raw signal value after preprocessing

- `value_sg`  
  **Savitzky–Golay filtered signal value**  
  This is the **default signal to use for modulation**

---

## Default modulation input for Student 3

Use:

```text
value_sg
