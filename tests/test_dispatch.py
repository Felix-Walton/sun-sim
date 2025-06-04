import numpy as np, pandas as pd
from simulate import hourly_generation_series, mock_price_series
from dispatch import greedy_dispatch, BatteryCfg

def test_dispatch_saves_money():
    idx = pd.date_range("2024-06-01", periods=24, freq="h", tz="UTC")
    pv   = pd.Series(np.linspace(0, 0.8, 24), idx)     # simple ramp
    price = mock_price_series(idx)
    res = greedy_dispatch(pv, price)
    assert res["pounds_saved"] >= 0

def test_soc_bounds():
    idx = pd.date_range("2024-06-02", periods=24, freq="h", tz="UTC")
    pv   = pd.Series(0.5, idx)        # constant sun
    price = mock_price_series(idx)
    cap = 2.0
    res = greedy_dispatch(pv, price,
                          cfg=BatteryCfg(capacity_kwh=cap))
    soc = res["df"].soc
    assert soc.min() >= 0
    assert soc.max() <= cap + 1e-6
