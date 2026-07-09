from legged_mission_planner_fr.field_model import FALLBACK_BOX_ID
from legged_mission_planner_fr.path_planner import MissionPathPlanner
from legged_mission_planner_fr.quintuple_exporter import build_quintuple_plan
from legged_mission_planner_fr.state_definitions import MissionState
from legged_mission_planner_fr.waypoint_config import WaypointConfig


def _wp_config() -> WaypointConfig:
    config = WaypointConfig.load_default()
    assert config is not None
    return config


def _planner() -> MissionPathPlanner:
    return MissionPathPlanner(waypoint_config=_wp_config())


def _pick_order(sequence):
    return [
        step.target_box
        for step in sequence
        if step.target_box is not None and step.state == MissionState.PICK
    ]


def _pick_paths(sequence):
    return [
        step.path
        for step in sequence
        if step.target_box is not None and step.state == MissionState.PICK
    ]


def _has_step(sequence, path, wp, state=None):
    for step in sequence:
        if step.path == path and step.wp == wp:
            if state is None or int(step.state) == state:
                return True
    return False


def test_fallback_pick_no_duplicate_transit_at_wp1():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    path1_wp1 = [s for s in seq if s.path == 1 and s.wp == 1]
    assert len(path1_wp1) == 1
    assert path1_wp1[0].state == MissionState.PICK
    assert path1_wp1[0].target_box == FALLBACK_BOX_ID


def test_fallback_always_first():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    first_pick = next(s for s in seq if s.state == MissionState.PICK and s.target_box == FALLBACK_BOX_ID)
    assert first_pick.path == 1 and first_pick.wp == 1
    assert first_pick.target_box == FALLBACK_BOX_ID


def test_fallback_place_path():
    planner = _planner()
    box_types = [0, 1, 2, 3, 2, 1, 0, 3]
    seq = planner.plan(box_types, [0, 1, 2, 3])
    fallback_place = next(
        s for s in seq
        if s.target_box == FALLBACK_BOX_ID and s.state == MissionState.PLACE
    )
    assert fallback_place.path == 4
    assert fallback_place.wp == 3


def test_upper_before_lower():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    picks = _pick_order(seq)
    upper = [b for b in picks if b in (0, 1, 2, 3)]
    lower = [b for b in picks if b in (5, 6, 7)]
    assert upper and lower
    assert max(picks.index(b) for b in upper) < min(picks.index(b) for b in lower)


def test_cross_path_no_wp3_align():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    align_steps = [s for s in seq if s.wp == 3 and s.state == MissionState.TRANSIT and 'align' in s.note]
    assert not align_steps
    switch_steps = [s for s in seq if 'switch to path' in s.note]
    assert not switch_steps


def test_quiz_reorder():
    planner = _planner()
    base = _pick_order(planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3]))
    quiz = _pick_order(
        planner.plan(
            [0, 1, 2, 3, 0, 1, 2, 3],
            [0, 1, 2, 3],
            include_quiz_state=True,
            quiz_type=2,
        )
    )
    assert base != quiz
    upper_quiz = [b for b in quiz if b in (0, 1, 2, 3)]
    assert 2 in upper_quiz
    assert upper_quiz.index(2) == min(upper_quiz.index(b) for b in upper_quiz if b in (2, 6) or b == 2)


def test_quiz_still_upper_before_lower():
    planner = _planner()
    seq = planner.plan(
        [0, 1, 2, 3, 0, 1, 2, 3],
        [0, 1, 2, 3],
        quiz_type=2,
    )
    picks = _pick_order(seq)
    upper = [b for b in picks if b in (0, 1, 2, 3)]
    lower = [b for b in picks if b in (5, 6, 7)]
    assert max(picks.index(b) for b in upper) < min(picks.index(b) for b in lower)


def test_zone_reverse():
    planner = _planner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    seq = planner.plan(box_types, [3, 2, 1, 0])
    fallback_place = next(
        s for s in seq
        if s.target_box == FALLBACK_BOX_ID and s.state == MissionState.PLACE
    )
    assert fallback_place.path == 5


def test_quiz_start_state():
    planner = _planner()
    seq = planner.plan(
        [0, 1, 2, 3, 0, 1, 2, 3],
        [0, 1, 2, 3],
        include_quiz_state=True,
        quiz_type=1,
    )
    assert seq[0].state == MissionState.QUIZ_RECOGNITION


def test_base_start_state():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    assert seq[0].state == MissionState.TRANSIT


def test_uses_ui_points_waypoints():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    fallback_place = next(
        s for s in seq
        if s.target_box == FALLBACK_BOX_ID and s.state == MissionState.PLACE
    )
    assert fallback_place.path == 2
    assert fallback_place.wp == 2
    box0_place = next(
        s for s in seq
        if s.target_box == 0 and s.state == MissionState.PLACE
    )
    assert box0_place.wp == 2


def test_path1_still_transits():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    fallback_transits = [
        s for s in seq
        if s.path == 1 and s.state == MissionState.TRANSIT and s.wp in (2, 3)
    ]
    assert len(fallback_transits) == 2


def test_same_path_skips_intermediate():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    pick_box1 = next(s for s in seq if s.target_box == 1 and s.state == MissionState.PICK)
    place_box1 = next(s for s in seq if s.target_box == 1 and s.state == MissionState.PLACE)
    assert pick_box1.wp == 2
    assert place_box1.wp == 3
    between = [
        s for s in seq
        if seq.index(pick_box1) < seq.index(s) < seq.index(place_box1)
        and s.path == 3
    ]
    assert between == []


def test_nearest_path_over_unplaced_type():
    planner = _planner()
    # fallback type 2 -> zone 2 (path 4); placed_types={2} after fallback
    # box2 on path4 (type2 already placed, dist=0) vs box1 on path3 (type1 unplaced, dist=1)
    box_types = [0, 1, 2, 3, 2, 1, 0, 3]
    zone_types = [0, 1, 2, 3]
    seq = planner.plan(box_types, zone_types)
    upper_picks = [
        s.target_box for s in seq
        if s.state == MissionState.PICK and s.target_box in (0, 1, 2, 3)
    ]
    assert upper_picks[0] == 2


def test_quintuple_export():
    wp_config = _wp_config()
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    plan = build_quintuple_plan(seq, waypoint_config=wp_config)
    assert plan['switch_mode'] == 'fast_mode'
    first = plan['sequence'][0]
    assert set(first.keys()) == {'path', 'wp', 'state', 'target_id', 'motion_planner'}
    assert all(s['state'] in (int(MissionState.PICK), int(MissionState.PLACE)) for s in plan['sequence'])
    fallback_pick = next(
        s for s in plan['sequence']
        if s['state'] == int(MissionState.PICK) and s['path'] == 1 and s['wp'] == 1
    )
    assert fallback_pick['motion_planner'] == 1
    other_pick = next(
        s for s in plan['sequence']
        if s['state'] == int(MissionState.PICK) and not (s['path'] == 1 and s['wp'] == 1)
    )
    assert other_pick['motion_planner'] == 2
    place_step = next(s for s in plan['sequence'] if s['state'] == int(MissionState.PLACE))
    assert place_step['motion_planner'] == 1
    pick_step = next(s for s in plan['sequence'] if s['state'] == int(MissionState.PICK))
    assert pick_step['target_id'] >= 0
