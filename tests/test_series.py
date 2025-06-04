import pandas as pd
from simulate import hourly_generation_series

def test_hourly_length_and_bounds():
    ser = hourly_generation_series(51.52, -0.09, kwp=4, year=2023)
    assert len(ser) == 8760                      # 365 × 24
    # total annual yield should be realistic
    assert 2000 < ser.sum() < 5000              # kWh for 4 kWp UK array
    # no negative energies
    assert (ser >= 0).all()

def test_year_parameter_applied():
    # Make sure choosing 2022 returns a DatetimeIndex from 2022
    ser22 = hourly_generation_series(51.52, -0.09, 4, year=2022)
    assert ser22.index.min().year == 2022