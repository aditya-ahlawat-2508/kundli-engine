from hypothesis import given, settings
from hypothesis import strategies as st

from kundli.config import EngineConfig
from kundli.ephemeris import planet_positions

# JD range ~1700..2300 CE
jds = st.floats(min_value=2341972.5, max_value=2561000.5)


@settings(max_examples=60, deadline=None)
@given(jds, st.sampled_from(["mean", "true"]))
def test_longitudes_in_range_and_nodes_opposite(jd, node):
    pos = {p.name: p for p in planet_positions(jd, EngineConfig(node_type=node))}
    for p in pos.values():
        assert 0 <= p.sidereal_lon < 360 and 0 <= p.tropical_lon < 360
    assert abs(((pos["Rahu"].sidereal_lon - pos["Ketu"].sidereal_lon) % 360) - 180) < 1e-9
