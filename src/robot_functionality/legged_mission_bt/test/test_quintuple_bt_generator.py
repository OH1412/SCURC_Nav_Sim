#!/usr/bin/env python3

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from quintuple_bt_generator import (  # noqa: E402
    arm_point_id_for_step,
    build_bt_xml,
    build_waypoints_yaml,
    collect_waypoint_ids,
    nav_wp_id,
)


def test_nav_wp_id():
    assert nav_wp_id(0, 0) == 'nav_p0_wp0'
    assert nav_wp_id(5, 3) == 'nav_p5_wp3'


def test_arm_point_id_mapping():
    assert arm_point_id_for_step(2, 4) == 4
    assert arm_point_id_for_step(3, 0) == 8
    assert arm_point_id_for_step(3, 7) == 15


def test_build_bt_xml_pick_and_place():
    sequence = [
        {'path': 0, 'wp': 0, 'state': 1, 'target_id': -1},
        {'path': 1, 'wp': 1, 'state': 2, 'target_id': 4},
        {'path': 2, 'wp': 2, 'state': 3, 'target_id': 0},
    ]
    xml = build_bt_xml(sequence, arm_timeout=30.0)
    assert '<Nav2PoseNode wp_id="nav_p0_wp0" limit_yaw="false"/>' in xml
    assert '<ArmPickNode arm_point_id="4" timeout="30.0"/>' in xml
    assert '<ArmPlaceNode arm_point_id="8" timeout="30.0"/>' in xml


def test_collect_waypoint_ids_includes_grid_and_sequence():
    sequence = [{'path': 5, 'wp': 1, 'state': 1, 'target_id': -1}]
    ids = collect_waypoint_ids(sequence, path_count=6, wp_count=4)
    assert ids[0] == 'nav_p0_wp0'
    assert 'nav_p5_wp1' in ids
    assert len(ids) == 24
