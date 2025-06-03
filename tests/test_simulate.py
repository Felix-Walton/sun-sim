from ..simulate import estimate_generation

def test_daily_yield_reasonable():
    # Rough sanity check for a typical UK roof
    kwh = estimate_generation(51.52, -0.09, kwp=4)
    assert 2.0 < kwh < 20.0      # 4 kWp should never be zero or >20 kWh/day