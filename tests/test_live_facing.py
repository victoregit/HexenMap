import cv2,math,numpy as np,pytest
from src.live.facing import player_facing


def pointer_frame(angle,arrow_angle=90):
    frame=np.full((220,220,3),(65,85,95),np.uint8)
    yy,xx=np.indices(frame.shape[:2]);dx=xx-110;dy=yy-110
    theta=np.degrees(np.arctan2(dx,-dy))%360
    sector=(np.abs((theta-angle+180)%360-180)<=45)&(dx*dx+dy*dy<64**2)
    frame[sector]=np.rint(frame[sector]*.78+255*.22).astype(np.uint8)
    base=np.array([[0,-11],[9,7],[0,3],[-9,7]],float)
    a=math.radians(arrow_angle);rotation=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    cv2.fillPoly(frame,[np.rint(base@rotation.T+[110,110]).astype(np.int32)],(255,255,0))
    return frame


@pytest.mark.parametrize('angle',[0,45,90,135,180,225,270,315])
def test_view_cone_heading_is_independent_of_the_cyan_arrow(angle):
    heading,confidence=player_facing(pointer_frame(angle,(angle+180)%360),(110,110,76))
    assert heading is not None and confidence>=.7
    assert abs((heading-angle+180)%360-180)<8


def test_non_directional_or_missing_player_pointer_is_not_a_heading():
    frame=np.zeros((220,220,3),np.uint8)
    assert player_facing(frame,(110,110,76))==(None,0.)
    cv2.circle(frame,(110,110),7,(255,255,0),-1)
    assert player_facing(frame,(110,110,76))==(None,0.)


def test_temporal_facing_rejects_a_single_reversed_reading_but_confirms_a_real_turn():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    assert abs(tracker.update(pointer_frame(0),circle,100)[0])<8
    assert abs(tracker.update(pointer_frame(180),circle,100.05)[0])<8
    assert abs(tracker.update(pointer_frame(0),circle,100.10)[0])<8
    tracker.update(pointer_frame(90),circle,100.15)
    heading,confidence=tracker.update(pointer_frame(90),circle,100.20)
    assert abs(heading-90)<8 and confidence>=.7


def test_heading_crosses_north_by_short_arc_and_never_survives_a_missing_pointer():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    before,_=tracker.update(pointer_frame(350),circle,100)
    after,_=tracker.update(pointer_frame(10),circle,100.05)
    assert abs((after-before+180)%360-180)<20
    assert tracker.update(np.zeros((220,220,3),np.uint8),circle,100.1)==(None,0.)
    assert tracker.heading is None


def test_short_ambiguity_bridge_is_bounded_and_reset_discards_it():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    tracker.update(pointer_frame(0),circle,100)
    ambiguous=np.zeros((220,220,3),np.uint8);cv2.circle(ambiguous,(110,110),7,(255,255,0),-1)
    assert tracker.update(ambiguous,circle,100.1)[0] is not None
    assert tracker.update(ambiguous,circle,100.19)==(None,0.)
    tracker.reset();assert tracker.update(ambiguous,circle,100.2)==(None,0.)


def test_arrow_without_view_sector_is_never_used_as_view_direction():
    frame=np.full((220,220,3),70,np.uint8)
    cv2.fillPoly(frame,[np.array([[110,99],[119,117],[110,113],[101,117]])],(255,255,0))
    assert player_facing(frame,(110,110,76))==(None,0.)


def test_rotating_only_the_arrow_does_not_rotate_compass_reference():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    for n,arrow in enumerate((0,90,180,270,45)):
        heading,confidence=tracker.update(pointer_frame(40,arrow),circle,100+n*.05)
        assert abs((heading-40+180)%360-180)<8 and confidence>=.7


def test_stationary_arrow_and_rotating_view_sector_update_view_direction():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    tracker.update(pointer_frame(0,90),circle,100)
    for n in range(1,8):heading,confidence=tracker.update(pointer_frame(90,90),circle,100+n*.05)
    assert abs(heading-90)<8 and confidence>=.7


def test_background_is_reprojected_with_the_map_and_discarded_on_discontinuity():
    from src.live.facing import FacingTracker
    tracker=FacingTracker();circle=(110,110,76)
    identity=np.array([[1.,0,0],[0,1.,0]])
    tracker.update(pointer_frame(0),circle,100,identity)
    tracker.update(pointer_frame(90),circle,100.05,identity)
    moved=np.array([[1.,0,3],[0,1.,-2]])
    heading,confidence=tracker.update(pointer_frame(90),circle,100.10,moved)
    assert heading is not None and abs((heading-90+180)%360-180)<8 and confidence>=.7
    tracker.reset()
    assert tracker.background is None and tracker.background_matrix is None
    assert tracker.heading is None


@pytest.mark.parametrize('brightness',[225,240,248])
@pytest.mark.parametrize('angle',[0,75,180,285])
def test_weak_white_view_sector_on_snow(brightness,angle):
    frame=pointer_frame(angle)
    terrain=np.all(frame==[65,85,95],axis=2)
    cone=(frame[:,:,0]!=255)&~terrain
    frame[terrain]=brightness
    frame[cone]=round(brightness*.82+255*.18)
    heading,confidence=player_facing(frame,(110,110,76))
    assert heading is not None and confidence>=.7
    assert abs((heading-angle+180)%360-180)<8


def test_white_terrain_without_visible_cone_cannot_supply_heading():
    frame=pointer_frame(90)
    frame[frame[:,:,0]!=255]=255
    assert player_facing(frame,(110,110,76))==(None,0.)
