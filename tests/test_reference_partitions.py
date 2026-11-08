import pytest

from src.live.tile_grid import partition_bounds


def test_partition_covers_negative_tile_coordinates_without_gaps():
    bounds=(-36,-4,1,25)
    parts=partition_bounds(bounds)
    expected={(x,y) for x in range(-36,2) for y in range(-4,26)}
    covered={(x,y) for a,b,c,d in parts for x in range(a,c+1) for y in range(b,d+1)}
    assert covered==expected
    assert all((c-a+1)<=16 and (d-b+1)<=16 for a,b,c,d in parts)
    assert len(parts)>1
    assert sum((c-a+1)*(d-b+1) for a,b,c,d in parts)>len(covered)


def test_small_map_keeps_exact_bounds():
    assert partition_bounds((-2,4,2,7))==[(-2,4,2,7)]


@pytest.mark.parametrize('bounds,side,overlap',[( (0,0,1,1),1,1),((1,0,0,1),16,1),((0,0,1,1),16,-1)])
def test_rejects_invalid_partition(bounds,side,overlap):
    with pytest.raises(ValueError): partition_bounds(bounds,side,overlap)
