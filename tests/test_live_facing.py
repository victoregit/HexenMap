import cv2,math,numpy as np,pytest
from src.live.facing import player_facing


@pytest.mark.parametrize('angle',[0,45,90,135,180,225,270,315])
def test_native_notched_pointer_facing_at_known_angles(angle):
    frame=np.zeros((220,220,3),np.uint8);base=np.array([[0,-11],[9,7],[0,3],[-9,7]],float)
    a=math.radians(angle);rotation=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    points=np.rint(base@rotation.T+[110,110]).astype(np.int32);cv2.fillPoly(frame,[points],(255,255,0))
    heading,confidence=player_facing(frame,(110,110,76))
    assert heading is not None and confidence>=.7
    assert abs((heading-angle+180)%360-180)<8


def test_non_directional_or_missing_player_pointer_is_not_a_heading():
    frame=np.zeros((220,220,3),np.uint8)
    assert player_facing(frame,(110,110,76))==(None,0.)
    cv2.circle(frame,(110,110),7,(255,255,0),-1)
    assert player_facing(frame,(110,110,76))==(None,0.)


def pointer_frame(angle):
    frame=np.zeros((220,220,3),np.uint8);base=np.array([[0,-11],[9,7],[0,3],[-9,7]],float)
    a=math.radians(angle);rotation=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    cv2.fillPoly(frame,[np.rint(base@rotation.T+[110,110]).astype(np.int32)],(255,255,0));return frame


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
