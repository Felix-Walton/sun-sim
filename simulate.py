# simulate.py  (only the few changed lines are marked ### CHANGED ###)
import argparse
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Tuple

PVGIS_VERSION = "v5_3"                         # need ≥5.3 for SARAH-3
BASE_URL      = f"https://re.jrc.ec.europa.eu/api/{PVGIS_VERSION}/"

PVGIS_URL  = BASE_URL + "PVcalc"
SERIES_URL = BASE_URL + "seriescalc"
HOURLY_URL = SERIES_URL

DEFAULT_RAD_DB = "PVGIS-SARAH3"                # ends 2023  :contentReference[oaicite:0]{index=0}

# ──────────────────────────────────────────────────────────────────────
def estimate_generation(lat: float, lon: float, kwp: float,
                        raddatabase: str = DEFAULT_RAD_DB) -> float:
    """Daily-average kWh from PVGIS totals."""
    params = {"lat": lat, "lon": lon,
              "peakpower": kwp, "loss": 14,
              "raddatabase": raddatabase,
              "outputformat": "json", "browser": 0}
    r = requests.get(PVGIS_URL, params=params, timeout=20)
    r.raise_for_status()
    annual_kwh = r.json()["outputs"]["totals"]["fixed"]["E_y"]
    return annual_kwh / 365


def hourly_generation_series(
    lat: float,
    lon: float,
    kwp: float,
    tilt: int = 35,
    azim: int = 0,
    year: Optional[int] = None,
    raddatabase: str = DEFAULT_RAD_DB,
) -> pd.Series:
    """
    Return *hourly* PV energy (kWh) for one calendar year.
    """
    params = {"lat": lat, "lon": lon,
              "surface_tilt": tilt, "surface_azimuth": azim,
              "raddatabase": raddatabase,
              "pvcalculation": 1, "peakpower": kwp, "loss": 14,
              "pvtechchoice": "crystSi", "mountingplace": "building",
              "outputformat": "json", "browser": 0}
    if year is None:
        year = 2023            #
    params["startyear"] = params["endyear"] = year

    r = requests.get(HOURLY_URL, params=params, timeout=35)
    r.raise_for_status()
    src = r.json()

    # ---- parse the hourly table ------------------------------------------------
    df = pd.DataFrame(src["outputs"]["hourly"])
    # YYYYMMDD:HHMM  → pandas datetime (UTC)
    df["time"] = pd.to_datetime(df["time"],
                                format="%Y%m%d:%H%M",  # <-- key line ### CHANGED ###
                                utc=True)              # PVGIS gives UTC stamps  :contentReference[oaicite:1]{index=1}
    df.set_index("time", inplace=True)

    # power [W] every 10 min → energy [kWh] and sum per ISO hour
    power_w = df["P"].astype(float)
    dt_h = (df.index[1] - df.index[0]).total_seconds() / 3600   # 0.166… for SARAH
    energy_each = power_w * dt_h / 1000.0                      # kWh per sample
    hourly_kwh = energy_each.resample("h").sum()               # 60-min buckets
    hourly_kwh.name = "pv_kwh"
    return hourly_kwh

def mock_price_series(index: pd.DatetimeIndex) -> pd.Series:
    """
    Cheap overnight (12 p), expensive evening peak (30 p),
    gentle mid-day valley (15 p).
    """
    hours = index.hour
    base = np.where((hours >= 16) & (hours < 20), 0.30,
            np.where((hours >= 0)  & (hours < 6), 0.12, 0.15))
    return pd.Series(base, index=index, name="price_£pkWh")

def geocode(postcode: str) -> Tuple[float, float]:
    r = requests.get(f"https://api.postcodes.io/postcodes/{postcode}", timeout=10)
    r.raise_for_status()
    res = r.json()["result"]
    return res["latitude"], res["longitude"]


# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Estimate solar generation for a UK site")
    p.add_argument("--kwp", type=float, default=4.0,
                   help="Array size in kWp")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--postcode", type=str,
                   help="UK postcode, e.g. EC2A3AY")
    g.add_argument("--latlon", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="Latitude and longitude")

    p.add_argument("--hourly", action="store_true",
                   help="Print the first 24 h of hourly kWh")
    args = p.parse_args()

    lat, lon = (geocode(args.postcode) if args.postcode
                else tuple(map(float, args.latlon)))

    if args.hourly:
        s = hourly_generation_series(lat, lon, args.kwp)
        print(s.head(24))
    else:
        daily = estimate_generation(lat, lon, args.kwp)
        print(f"Estimated average daily generation: {daily:.1f} kWh")
