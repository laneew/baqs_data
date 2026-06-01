# -*- coding: utf-8 -*-
"""
Modified on Thurs May 14:00 2026

@author: DCSB

PN (Particle Number) processing script
Converts CSV size distribution data into NetCDF
INCLUDING QC FLAG VARIABLES
"""

import numpy as np
import pandas as pd
import netCDF4 as nc
import datetime
import glob
import os

# =========================
# SETTINGS
# =========================

data_dir = "z:/Processed Data/SMPS/Hourly average/ceda_32cpd/"

file_pattern = "*_hour_v1.1.csv"
version_number = "v1.1"

lat = 52.46
lon = -1.93

# =========================
# PROCESS FILES
# =========================

os.chdir(data_dir)

filenames = glob.glob(file_pattern)

for filename in filenames:

    print(f"Processing: {filename}")

    # -------------------------
    # LOAD DATA
    # -------------------------

    df = pd.read_csv(filename)

    # Parse datetime safely
    df["datetime"] = pd.to_datetime(
        df["date (UTC+0)"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
        utc=True
    )

    # Remove invalid datetimes
    df = df.dropna(subset=["datetime"])

    # Sort
    df = df.sort_values("datetime")

    # Set datetime index
    df.set_index("datetime", inplace=True)

    # -------------------------
    # IDENTIFY PN COLUMNS
    # -------------------------

    pn_columns = [
        col for col in df.columns
        if col.startswith("dN_dLogDp_")
    ]

    # -------------------------
    # IDENTIFY QC FLAG COLUMNS
    # -------------------------

    qc_columns = [
        col for col in df.columns
        if col.startswith("qc_flag")
    ]

    if len(pn_columns) == 0:
        print("No PN columns found, skipping file.")
        continue

    # -------------------------
    # EXTRACT SIZE BINS
    # -------------------------

    size_bins = np.array([
        float(col.replace("dN_dLogDp_", "").replace("_nm", ""))
        for col in pn_columns
    ], dtype=np.float32)

    # -------------------------
    # TIME RANGE
    # -------------------------

    start = df.index.min()
    end = df.index.max()

    timeline = pd.date_range(
        start=start,
        end=end,
        freq="1H",
        tz="UTC"
    )

    # Reindex to complete hourly timeline
    df = df.reindex(timeline)

    # -------------------------
    # ADD TIME COMPONENTS
    # -------------------------

    df["day_of_year"] = df.index.dayofyear
    df["year"] = df.index.year
    df["month"] = df.index.month
    df["day"] = df.index.day
    df["hour"] = df.index.hour

    # -------------------------
    # OUTPUT FILE NAME
    # -------------------------

    first_month = start.strftime("%Y%m")

    out_file = (
        f"BAQS_SMPS_PN_concentration_"
        f"{first_month}_Ratified_{version_number}.nc"
    )

    # -------------------------
    # CREATE NETCDF
    # -------------------------

    dataset = nc.Dataset(
        out_file,
        "w",
        format="NETCDF4_CLASSIC"
    )

    # =========================
    # GLOBAL ATTRIBUTES
    # =========================

    dataset.Conventions = "CF-1.8"

    dataset.title = (
        "Particle Number Size Distribution"
    )

    dataset.source = (
        "Birmingham Air Quality Supersite (BAQS)"
    )

    dataset.instrument_model = "SMPS3938"

    dataset.location = (
        "Edgbaston, Birmingham, UK"
    )

    dataset.history = (
        f"Created {datetime.datetime.utcnow()} UTC"
    )

    dataset.time_coverage_start = (
        start.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    dataset.time_coverage_end = (
        end.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    # =========================
    # DIMENSIONS
    # =========================

    dataset.createDimension("time", None)

    dataset.createDimension(
        "particle_diameter",
        len(size_bins)
    )

    dataset.createDimension("latitude", 1)

    dataset.createDimension("longitude", 1)

    # =========================
    # VARIABLES
    # =========================

    # -------------------------
    # TIME
    # -------------------------

    time_var = dataset.createVariable(
        "time",
        np.float64,
        ("time",)
    )

    time_var.units = (
        "seconds since 1970-01-01 00:00:00 UTC"
    )

    time_var.standard_name = "time"

    time_var.calendar = "standard"

    time_var.axis = "T"

    # -------------------------
    # COORDINATES
    # -------------------------

    lat_var = dataset.createVariable(
        "latitude",
        np.float32,
        ("latitude",)
    )

    lon_var = dataset.createVariable(
        "longitude",
        np.float32,
        ("longitude",)
    )

    lat_var.units = "degree_north"
    lon_var.units = "degree_east"

    lat_var.standard_name = "latitude"
    lon_var.standard_name = "longitude"

    # -------------------------
    # SIZE BINS
    # -------------------------

    diam_var = dataset.createVariable(
        "particle_diameter",
        np.float32,
        ("particle_diameter",)
    )

    diam_var.units = "nm"

    diam_var.long_name = (
        "Particle diameter"
    )

    # -------------------------
    # PN DISTRIBUTION
    # -------------------------

    pn_var = dataset.createVariable(
        "particle_number_concentration",
        np.float32,
        ("time", "particle_diameter"),
        fill_value=-1.00E+20,
        zlib=True
    )

    pn_var.units = "cm-3"

    pn_var.long_name = (
        "Particle number size distribution"
    )

    pn_var.coordinates = (
        "latitude longitude"
    )

    # =========================
    # QC FLAG VARIABLES
    # =========================

    qc_vars = {}

    for qc_col in qc_columns:

        qc_var = dataset.createVariable(
            qc_col,
            np.int8,
            ("time",),
            fill_value=-128,
            zlib=True
        )

        qc_var.units = "1"

        qc_var.long_name = (
            f"Data quality flag: {qc_col}"
        )

        qc_var.flag_values = np.array(
            [0, 1, 2, 3, 4, 5],
            dtype=np.int8
        )

        qc_var.flag_meanings = (
            "not_used "
            "good "
            "bad "
            "suspect "
            "local_unusual_activity "
            "strong_nucleation_event"
        )

        qc_vars[qc_col] = qc_var

    # -------------------------
    # TIME BREAKDOWN VARIABLES
    # -------------------------

    doy_var = dataset.createVariable(
        "day_of_year",
        np.int16,
        ("time",)
    )

    year_var = dataset.createVariable(
        "year",
        np.int16,
        ("time",)
    )

    month_var = dataset.createVariable(
        "month",
        np.int16,
        ("time",)
    )

    day_var = dataset.createVariable(
        "day",
        np.int16,
        ("time",)
    )

    hour_var = dataset.createVariable(
        "hour",
        np.int16,
        ("time",)
    )

    # =========================
    # WRITE DATA
    # =========================

    # -------------------------
    # TIME
    # -------------------------

    time_var[:] = nc.date2num(
        timeline.to_pydatetime(),
        units=time_var.units,
        calendar=time_var.calendar
    )

    # -------------------------
    # COORDINATES
    # -------------------------

    lat_var[:] = lat
    lon_var[:] = lon

    # -------------------------
    # SIZE BINS
    # -------------------------

    diam_var[:] = size_bins

    # -------------------------
    # PN DATA
    # -------------------------

    pn_data = (
        df[pn_columns]
        .astype(np.float32)
        .values
    )

    pn_var[:, :] = pn_data

    # -------------------------
    # QC FLAG DATA
    # -------------------------

    for qc_col in qc_columns:

        qc_data = (
            df[qc_col]
            .astype(str)
            .str.replace("b", "", regex=False)
            .replace("nan", np.nan)
            .astype(float)
            .fillna(-128)
            .astype(np.int8)
            .values
        )

        qc_vars[qc_col][:] = qc_data

    # -------------------------
    # TIME COMPONENTS
    # -------------------------

    doy_var[:] = (
        df["day_of_year"]
        .fillna(-999)
        .astype(np.int16)
        .values
    )

    year_var[:] = (
        df["year"]
        .fillna(-999)
        .astype(np.int16)
        .values
    )

    month_var[:] = (
        df["month"]
        .fillna(-999)
        .astype(np.int16)
        .values
    )

    day_var[:] = (
        df["day"]
        .fillna(-999)
        .astype(np.int16)
        .values
    )

    hour_var[:] = (
        df["hour"]
        .fillna(-999)
        .astype(np.int16)
        .values
    )

    # -------------------------
    # CLOSE FILE
    # -------------------------

    dataset.close()

    print(f"Saved: {out_file}")
    