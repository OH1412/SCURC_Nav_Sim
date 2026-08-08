from legged_mission_planner_fr.field_model import PATH4_FIRST_BOX_ID, PATH4_LAST_BOX_ID
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


def test_path4_box6_pick_at_end():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    path4_wp1_picks = [
        s for s in seq
        if s.path == 4 and s.wp == 1 and s.state == MissionState.PICK
    ]
    assert len(path4_wp1_picks) == 1
    assert path4_wp1_picks[0].target_box == PATH4_LAST_BOX_ID
    pick_steps = [s for s in seq if s.state == MissionState.PICK]
    assert pick_steps[-1] == path4_wp1_picks[0]


def test_path4_box2_first():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    first_pick = next(s for s in seq if s.state == MissionState.PICK)
    assert first_pick.path == 4 and first_pick.wp == 2
    assert first_pick.target_box == PATH4_FIRST_BOX_ID


def test_path4_box6_place_path():
    planner = _planner()
    box_types = [0, 1, 2, 3, 2, 1, 0, 3]
    seq = planner.plan(box_types, [0, 1, 2, 3])
    box6_place = next(
        s for s in seq
        if s.target_box == PATH4_LAST_BOX_ID and s.state == MissionState.PLACE
    )
    assert box6_place.path == 2
    assert box6_place.wp == 3
    place_steps = [s for s in seq if s.state == MissionState.PLACE]
    assert place_steps[-1] == box6_place


def test_upper_before_lower():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    picks = _pick_order(seq)
    upper = [b for b in picks if b in (0, 1, 2, 3)]
    lower = [b for b in picks if b in (4, 5, 7)]
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
            quiz_type=1,
        )
    )
    assert base != quiz
    # box2 固定最先；quiz 排序仅作用于主任务 upper (0, 1, 3)
    main_upper_quiz = [b for b in quiz if b in (0, 1, 3)]
    assert 1 in main_upper_quiz
    assert main_upper_quiz.index(1) < main_upper_quiz.index(3)


def test_quiz_still_upper_before_lower():
    planner = _planner()
    seq = planner.plan(
        [0, 1, 2, 3, 0, 1, 2, 3],
        [0, 1, 2, 3],
        quiz_type=2,
    )
    picks = _pick_order(seq)
    upper = [b for b in picks if b in (0, 1, 2, 3)]
    lower = [b for b in picks if b in (4, 5, 7)]
    assert max(picks.index(b) for b in upper) < min(picks.index(b) for b in lower)


def test_zone_reverse():
    planner = _planner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    seq = planner.plan(box_types, [3, 2, 1, 0])
    box6_place = next(
        s for s in seq
        if s.target_box == PATH4_LAST_BOX_ID and s.state == MissionState.PLACE
    )
    assert box6_place.path == 3


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
    box6_place = next(
        s for s in seq
        if s.target_box == PATH4_LAST_BOX_ID and s.state == MissionState.PLACE
    )
    assert box6_place.path == 4
    assert box6_place.wp == 3
    box2_place = next(
        s for s in seq
        if s.target_box == PATH4_FIRST_BOX_ID and s.state == MissionState.PLACE
    )
    assert box2_place.path == 4
    assert box2_place.wp == 3
    box0_place = next(
        s for s in seq
        if s.target_box == 0 and s.state == MissionState.PLACE
    )
    assert box0_place.wp == 3


def test_path4_no_fallback_transit():
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    path4_transits = [
        s for s in seq
        if s.state == MissionState.TRANSIT and 'path4' in (s.note or '')
    ]
    assert not path4_transits


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


def test_nearest_path_after_box2_place():
    planner = _planner()
    # box2 type 2 -> zone 2 (path 4); main tasks start from path 4
    # box1 on path3 (dist=1) vs box0 on path2 (dist=2)
    box_types = [0, 1, 2, 3, 2, 1, 0, 3]
    zone_types = [0, 1, 2, 3]
    seq = planner.plan(box_types, zone_types)
    main_upper_picks = [
        s.target_box for s in seq
        if s.state == MissionState.PICK and s.target_box in (0, 1, 3)
    ]
    assert main_upper_picks[0] == 1


def test_quintuple_export():
    wp_config = _wp_config()
    planner = _planner()
    seq = planner.plan([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3])
    plan = build_quintuple_plan(seq, waypoint_config=wp_config)
    assert plan['switch_mode'] == 'fast_mode'
    exported = plan['sequence']
    first = exported[0]
    last = exported[-1]
    assert set(first.keys()) == {'path', 'wp', 'state', 'target_id', 'motion_planner'}
    assert all(s['state'] in (int(MissionState.PICK), int(MissionState.PLACE)) for s in exported)
    assert first['state'] == int(MissionState.PLACE)
    assert first['target_id'] == 2
    assert first['wp'] == 3
    assert last['state'] == int(MissionState.PLACE)
    assert last['target_id'] == 6
    assert last['wp'] == 3
    path4_picks = [
        s for s in exported
        if s['state'] == int(MissionState.PICK) and s['path'] == 4
    ]
    assert not path4_picks
    box4_pick = next(
        s for s in exported
        if s['state'] == int(MissionState.PICK) and s['path'] == 2 and s['wp'] == 1
    )
    assert box4_pick['motion_planner'] == 2
    other_pick = next(
        s for s in exported
        if s['state'] == int(MissionState.PICK)
    )
    assert other_pick['motion_planner'] == 2
    place_step = next(s for s in exported if s['state'] == int(MissionState.PLACE))
    assert place_step['motion_planner'] == 1
    pick_step = next(s for s in exported if s['state'] == int(MissionState.PICK))
    assert pick_step['target_id'] >= 0
