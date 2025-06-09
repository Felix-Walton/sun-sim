# octopus_prices.py
"""
Fetch half-hourly Agile Octopus import prices (incl. VAT) for a given date.

We default to product *AGILE-24-10-01* (current UK Agile).
Prices are region-specific; each region has a single-letter code (A‥P).
If you don’t know the code, pass `postcode`, we’ll look it up via
https://api.postcodes.io and map the DNO to the letter.
"""

from __future__ import annotations
import datetime as dt
from typing import Optional, Dict

import pandas as pd
import requests

PRODUCT_CODE = "AGILE-24-10-01"
# Distributor → region-letter mapping (Ofgem DNO id ➜ Agile suffix)
_DNO_TO_REGION: Dict[int, str] = {
    10: "A", 11: "B", 12: "C", 13: "D", 14: "E", 15: "F",
    16: "G", 17: "H", 18: "J", 19: "K", 20: "L", 21: "M",
    22: "N", 23: "P",
}

def _postcode_to_region(postcode: str) -> str:
    r = requests.get(f"https://api.postcodes.io/postcodes/{postcode}", timeout=10)
    r.raise_for_status()
    dno = r.json()["result"]["codes"]["nuts"]  # e.g. "UKI31"
    dno_num = int(dno[-2:])                    # last two digits
    return _DNO_TO_REGION.get(dno_num, "C")    # fallback London

def agile_prices(
    date: dt.date,
    region: Optional[str] = None,
    postcode: Optional[str] = None,
) -> pd.Series:
    """
    Return a 48-point Series of £/kWh (VAT-inc) for *date* in UTC.
    If the Octopus API returns fewer than 48 points, we fill the gaps by
    carrying the most recent known price forward (and backward if needed).
    """
    if region is None:
        if postcode is None:
            raise ValueError("Need either region letter or postcode")
        region = _postcode_to_region(postcode)

    tariff_code = f"E-1R-{PRODUCT_CODE}-{region}"
    period_from = dt.datetime.combine(date, dt.time.min, tzinfo=dt.timezone.utc)
    period_to   = period_from + dt.timedelta(days=1, minutes=-30)

    url = (
        f"https://api.octopus.energy/v1/products/{PRODUCT_CODE}"
        f"/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    )
    params = {
        "period_from": period_from.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "period_to":   period_to.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    raw = r.json()["results"]

    # Build Series, order earliest→latest
    prices = {
        pd.to_datetime(item["valid_from"], utc=True): item["value_inc_vat"] / 100
        for item in raw
    }
    s = pd.Series(prices).sort_index()
    s.name = "agile_£pkwh"

    # ▷ build the “ideal” 48-slot index: midnight UTC → midnight UTC next day
    start = pd.Timestamp(date.year, date.month, date.day, tz="UTC")
    full_index = pd.date_range(start, periods=48, freq="30min", tz="UTC")
    
    # ▷ reindex onto the full 48 slots, then fill any gaps
    s_full = s.reindex(full_index)
    s_full = s_full.ffill().bfill()

    return s_full

