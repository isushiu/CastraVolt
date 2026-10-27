import pytest
from fastapi import HTTPException


def test_state_boundaries_and_unsupported_locations():
    from castravolt.locations import resolve_state
    assert resolve_state(3.1579,101.7116)=='W.P. KUALA LUMPUR'
    assert resolve_state(3.0738,101.5183)=='SELANGOR'
    for point in [(2.9264,101.6964),(5.4141,100.3288),(1.3521,103.8198),(0,0)]:
        with pytest.raises(HTTPException) as error: resolve_state(*point)
        assert error.value.status_code==422


def test_geometry_holes_and_boundary_ambiguity():
    from castravolt.locations import contains_polygon
    polygon=[[[0,0],[10,0],[10,10],[0,10],[0,0]],[[4,4],[6,4],[6,6],[4,6],[4,4]]]
    assert contains_polygon(2,2,polygon)
    assert not contains_polygon(5,5,polygon)
    assert not contains_polygon(20,2,polygon)
    assert not contains_polygon(0,5,polygon)
