from legged_mission_planner_fr.waypoint_config import WaypointConfig


def test_waypoint_config_loads_fast_mode():
    config = WaypointConfig.load_default()
    assert config is not None
    assert config.max_wp(2) == 3
    assert config.max_wp(3) == 3
    assert config.max_wp(4) == 3
    assert config.max_wp(5) == 3


def test_pick_and_place_indexes():
    config = WaypointConfig.load_default()
    assert config.pick_for_box(0).path == 2
    assert config.pick_for_box(0).wp == 2
    assert config.pick_for_box(4).path == 2
    assert config.pick_for_box(4).wp == 1
    assert config.pick_for_box(1).path == 3
    assert config.pick_for_box(1).wp == 2
    assert config.place_for_zone(0).wp == 3
    assert config.place_for_zone(1).wp == 3


def test_box_and_zone_hotspots_from_ui_points():
    config = WaypointConfig.load_default()
    assert config is not None
    boxes = config.box_hotspots()
    zones = config.zone_hotspots()
    assert len(boxes) == 8
    assert len(zones) == 4
    assert boxes[0] == (config.pick_for_box(0).norm_x, config.pick_for_box(0).norm_y)
    assert zones[0] == (config.place_for_zone(0).norm_x, config.place_for_zone(0).norm_y)
