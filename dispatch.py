# dispatch.py
from dataclasses import dataclass
import pandas as pd

@dataclass
class BatteryCfg:
    capacity_kwh: float = 5.0   # usable capacity
    power_kw:    float = 3.0    # max charge/discharge
    round_trip_eff: float = 0.92

def greedy_dispatch(pv: pd.Series,
                    price: pd.Series,
                    cfg: BatteryCfg = BatteryCfg()) -> dict:
    """
    One-pass greedy scheduler:
      • store any PV that doesn't fit house-load (assumed zero here)
      • discharge whenever the tariff > median daily price
    Returns a dict with:
      - df  : DataFrame (pv, price, batt_flow, soc, grid_export)
      - £naive, £smart, £saved
    """
    if not pv.index.equals(price.index):
        raise ValueError("PV and price indices must align exactly")

    # threshold = mid-price of the day
    median_price = price.median()
    discharge_threshold = median_price / cfg.round_trip_eff

    soc = 0.0
    soc_trace   = []
    batt_flow   = []           # + charge, – discharge
    grid_export = []

    
    for pv_kwh, p in zip(pv, price):
        # 1) store surplus PV
        charge = min(pv_kwh, cfg.power_kw, cfg.capacity_kwh - soc)
        soc += charge
        pv_surplus = pv_kwh - charge

        # 2) only discharge if price is high enough to cover losses
        discharge = 0.0
        if p > discharge_threshold and soc > 0:
            discharge = min(cfg.power_kw, soc)
            soc -= discharge / cfg.round_trip_eff

        # 3) clamp so SoC never goes below 0 or above capacity
        soc = min(max(soc, 0.0), cfg.capacity_kwh)

        batt_flow.append(charge - discharge)
        soc_trace.append(soc)
        grid_export.append(pv_surplus + discharge)

    df = pd.DataFrame(
        {"pv": pv, "price": price,
         "battery_flow": batt_flow,
         "soc": soc_trace,
         "grid_export": grid_export},
        index=pv.index
    )

    cost_naive = (pv * price).sum()
    cost_smart = (df.grid_export.clip(lower=0) * price).sum()
    raw_saved = cost_naive - cost_smart
    pounds_saved = max(raw_saved, 0.0)   # don’t ever show a negative saving
    return {
        "df": df,
        "cost_naive": cost_naive,
        "cost_smart": cost_smart,
        "pounds_saved": pounds_saved,
    }
