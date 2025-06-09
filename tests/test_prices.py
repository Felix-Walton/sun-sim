import datetime as dt
import json, pathlib
import pandas as pd
from octopus_prices import agile_prices

FIXTURE = pathlib.Path(__file__).with_suffix(".json")

def _load_fixture():
    return json.loads(FIXTURE.read_text())

def test_parse_fixture(monkeypatch):
    """Parse saved API JSON so CI never makes live calls."""
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: Dummy(_load_fixture()))
    date = dt.date(2024, 3, 26)
    s = agile_prices(date, region="C")
    assert len(s) == 48 and s.between(0, 1).all()

class Dummy:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p
