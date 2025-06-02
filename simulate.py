# simulate.py
import argparse
import requests

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"

def estimate_generation(lat: float, lon: float, kwp: float) -> float:
    """
    Return the annual kWh yield for a fixed-tilt array,
    then convert to an average daily figure.
    """
    params = {
        "lat": lat, "lon": lon,
        "peakpower": kwp,
        "loss": 14,
        "outputformat": "json",
        "browser": 0,
    }
    r = requests.get(PVGIS_URL, params=params, timeout=20)
    r.raise_for_status()
    annual_kwh = r.json()["outputs"]["totals"]["fixed"]["E_y"]
    return annual_kwh / 365

def geocode(postcode: str) -> tuple[float, float]:
    r = requests.get(f"https://api.postcodes.io/postcodes/{postcode}", timeout=10)
    r.raise_for_status()
    result = r.json()["result"]
    return result["latitude"], result["longitude"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Estimate average daily solar generation for a UK site"
    )
    parser.add_argument("--kwp", type=float, default=4.0,
                        help="Array size in kW_peak")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--postcode", type=str,
                       help="UK postcode, e.g. EC2A3AY")
    group.add_argument("--latlon", nargs=2, type=float, metavar=("LAT", "LON"),
                       help="Latitude and longitude")

    args = parser.parse_args()

    if args.postcode:
        lat, lon = geocode(args.postcode)
    else:
        lat, lon = args.latlon

    daily = estimate_generation(lat, lon, args.kwp)
    print(f"Estimated average daily generation: {daily:.1f} kWh")
