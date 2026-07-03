from legged_mission_planner.path_planner import MissionPathPlanner


def _task_order(planner, box_types, zone_types, strategy, quiz_type=None):
    allowed = planner.field.strategy_paths(strategy)
    tasks = planner._assign_tasks(box_types, zone_types, allowed, strategy, quiz_type)
    ordered = planner._order_tasks(tasks, allowed, strategy, quiz_type)
    return [t.box_id for t in ordered]


def _pick_order(sequence):
    return [
        step.target_box
        for step in sequence
        if step.target_box is not None and int(step.state) in (2, 3)
    ]


def _path_sequence(planner, box_types, zone_types, strategy, quiz_type=None):
    allowed = planner.field.strategy_paths(strategy)
    tasks = planner._assign_tasks(box_types, zone_types, allowed, strategy, quiz_type)
    by_path = planner._group_tasks_by_path(tasks)
    return planner._schedule_safe_edges_paths(by_path, quiz_type)


def _pick_paths(sequence):
    return [
        step.path
        for step in sequence
        if step.target_box is not None and int(step.state) in (2, 3)
    ]


def test_quiz_none_matches_baseline():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    base = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only')
    again = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only', quiz_type=None)
    assert _pick_order(base) == _pick_order(again)


def test_middle_paths_quiz_reorders_paths():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    base = _task_order(planner, box_types, zone_types, 'middle_paths')
    quiz = _task_order(planner, box_types, zone_types, 'middle_paths', quiz_type=2)
    assert base != quiz
    assert quiz[:2] == [6, 2]


def test_safe_edges_quiz_prioritizes_path_with_quiz_boxes():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    base = _task_order(planner, box_types, zone_types, 'safe_edges')
    quiz = _task_order(planner, box_types, zone_types, 'safe_edges', quiz_type=3)
    assert base != quiz
    assert _path_sequence(planner, box_types, zone_types, 'safe_edges', quiz_type=3) == [5, 1, 4, 3, 2]
    assert quiz.index(3) < quiz.index(0)
    assert quiz.index(7) < quiz.index(5)
    seq = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only', quiz_type=3)
    assert _pick_paths(seq) == [5, 5, 1, 1, 4, 4, 3, 3]


def test_safe_edges_quiz_uses_cleared_side_for_pickups():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    seq = planner.plan(box_types, [0, 1, 2, 3], 'safe_edges', 'wp4_only', quiz_type=3)
    assert _pick_paths(seq) == [5, 5, 1, 1, 4, 4, 3, 3]


def test_safe_edges_dynamic_after_path1_prefers_path2():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    paths = _path_sequence(planner, box_types, zone_types, 'safe_edges')
    order = _pick_order(planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only'))
    assert paths == [1, 2, 3, 4, 5]
    assert paths.index(2) < paths.index(4)
    assert order.index(7) > order.index(6)
    assert order == [4, 0, 5, 1, 6, 2, 7, 3]


def test_safe_edges_first_edge_scoring():
    planner = MissionPathPlanner()
    zone_types = [0, 1, 2, 3]
    default = [0, 1, 2, 3, 0, 1, 2, 3]
    assert _path_sequence(planner, default, zone_types, 'safe_edges')[0] == 1
    assert _path_sequence(planner, default, zone_types, 'safe_edges', quiz_type=3)[0] == 5


def test_same_path_picks_wp2_before_wp3():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    picks = _pick_order(planner.plan(box_types, [0, 1, 2, 3], 'safe_edges', 'wp4_only'))
    assert picks.index(4) < picks.index(0)


def test_safe_edges_quiz_outer_column_boxes_share_boundary_path():
    """Col3 boundary boxes (e.g. 3 and 7) both pick on path 5 when quiz replans."""
    planner = MissionPathPlanner()
    box_types = [3, 1, 2, 0, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    seq = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only', quiz_type=3, include_quiz_state=True)
    picks = _pick_order(seq)
    assert picks[:2] == [7, 0]
    box3_pick = next(s for s in seq if s.target_box == 3 and int(s.state) in (2, 3))
    assert box3_pick.path == 5
    box0_pick = next(s for s in seq if s.target_box == 0 and int(s.state) in (2, 3))
    assert box0_pick.path == 1
    assert _pick_paths(seq) == [5, 1, 5, 1, 4, 4, 3, 3]


def test_quiz_plan_starts_with_state_zero():
    planner = MissionPathPlanner()
    box_types = [0, 1, 2, 3, 0, 1, 2, 3]
    zone_types = [0, 1, 2, 3]
    base = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only')
    quiz = planner.plan(box_types, zone_types, 'safe_edges', 'wp4_only', include_quiz_state=True, quiz_type=3)
    assert int(base[0].state) == 1
    assert int(quiz[0].state) == 0
    assert int(quiz[1].path) == 5
