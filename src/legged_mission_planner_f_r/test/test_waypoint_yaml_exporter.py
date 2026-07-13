from pathlib import Path

import yaml

from legged_mission_planner_fr.ui_assets import correct_legacy_norm_y, field_image_size, legacy_norm_y_correction_factor
from legged_mission_planner_fr.waypoint_yaml_exporter import (
    WaypointUI,
    build_mission_plan_hardcoded_yaml,
    build_ui_points_yaml,
    collect_waypoint_ids,
    export_waypoint_yamls,
    load_ui_points,
)


def _sample_paths() -> dict[int, list[WaypointUI]]:
    return {
        2: [
            WaypointUI(2, 1, 0.537000, 0.518000, state=2, target_id=4, motion_planner=1),
            WaypointUI(2, 2, 0.540000, 0.450000, state=2, target_id=0, motion_planner=2),
        ],
        3: [
            WaypointUI(3, 1, 0.600000, 0.520000, state=3, target_id=1, motion_planner=1),
        ],
    }


def test_waypoint_id_naming():
    paths = _sample_paths()
    assert collect_waypoint_ids(paths) == ['2-1', '2-2', '3-1']


def test_build_ui_points_yaml_structure():
    data = build_ui_points_yaml(_sample_paths())
    assert data['format_version'] == 1
    assert data['planner_variant'] == 'front_back'
    assert data['coordinate_system'] == 'normalized_field_image'
    assert data['normalization'] == 'image_pixels'
    assert data['field_image_size'] == list(field_image_size())
    assert data['paths'][2][0]['id'] == '2-1'
    assert data['paths'][2][0]['norm_x'] == 0.537
    assert data['paths'][2][0]['state'] == 2
    assert data['paths'][2][0]['target_id'] == 4
    assert data['paths'][2][0]['motion_planner'] == 1
    assert data['paths'][2][1]['state'] == 2
    assert data['paths'][2][1]['target_id'] == 0
    assert data['paths'][2][1]['motion_planner'] == 2
    assert data['paths'][3][0]['id'] == '3-1'
    assert data['paths'][3][0]['state'] == 3
    assert data['paths'][3][0]['target_id'] == 1
    assert data['paths'][3][0]['motion_planner'] == 1


def test_build_mission_plan_hardcoded_yaml():
    data = build_mission_plan_hardcoded_yaml(_sample_paths())
    # 验证 format 元数据
    assert data['format_version'] == 1
    assert data['planner_variant'] == 'front_back'
    # 验证 nav 段仍存在
    assert set(data['nav'].keys()) == {'2-1', '2-2', '3-1'}
    for entry in data['nav'].values():
        assert entry['frame_id'] == 'map'
        assert entry['x'] is None
        assert entry['y'] is None
        assert entry['yaw'] is None
    # 验证 sequence 五元组
    seq = data['sequence']
    assert len(seq) == 3
    assert seq[0] == {'path': 2, 'wp': 1, 'state': 2, 'target_id': 4, 'motion_planner': 1}
    assert seq[1] == {'path': 2, 'wp': 2, 'state': 2, 'target_id': 0, 'motion_planner': 2}
    assert seq[2] == {'path': 3, 'wp': 1, 'state': 3, 'target_id': 1, 'motion_planner': 1}


def test_export_and_load_roundtrip(tmp_path: Path):
    ui_out = tmp_path / 'ui_points.yaml'
    bt_out = tmp_path / 'mission_plan_hardcoded.yaml'
    paths = _sample_paths()

    export_waypoint_yamls(paths, ui_out, bt_out)
    assert ui_out.exists()
    assert bt_out.exists()

    loaded = load_ui_points(ui_out)
    assert collect_waypoint_ids(loaded) == collect_waypoint_ids(paths)

    # 验证 roundtrip 保留 state 和 target_id
    orig_wp = paths[2][0]  # WaypointUI(2, 1, ..., state=2, target_id=4)
    loaded_wp = loaded[2][0]
    assert loaded_wp.state == orig_wp.state
    assert loaded_wp.target_id == orig_wp.target_id
    assert loaded_wp.motion_planner == orig_wp.motion_planner

    bt_data = yaml.safe_load(bt_out.read_text(encoding='utf-8'))
    ui_data = yaml.safe_load(ui_out.read_text(encoding='utf-8'))
    ui_ids = [wp['id'] for path_wps in ui_data['paths'].values() for wp in path_wps]
    assert set(bt_data['nav'].keys()) == set(ui_ids)
    # 验证 mission_plan_hardcoded 包含 sequence
    assert 'sequence' in bt_data
    assert len(bt_data['sequence']) == 3


def test_load_ui_points_backward_compat():
    """旧格式 YAML（无 state/target_id/motion_planner）加载后使用默认值。"""
    loaded = load_ui_points_from_dict({
        'paths': {
            2: [{'id': '2-1', 'norm_x': 0.5, 'norm_y': 0.6}],
        }
    })
    wp = loaded[2][0]
    assert wp.state == 0
    assert wp.target_id == -1
    assert wp.motion_planner == 0


def test_load_ui_points_legacy_limit_yaw():
    """旧 limit_yaw 字段加载时按规则派生 motion_planner。"""
    loaded = load_ui_points_from_dict({
        'paths': {
            2: [
                {
                    'id': '2-1',
                    'norm_x': 0.5,
                    'norm_y': 0.6,
                    'state': 2,
                    'target_id': 4,
                    'limit_yaw': False,
                },
            ],
        }
    })
    assert loaded[2][0].motion_planner == 2


def test_load_ui_points_legacy_norm_y_correction():
    factor = legacy_norm_y_correction_factor()
    assert 0.7 < factor < 0.75
    loaded = load_ui_points_from_dict({
        'format_version': 1,
        'paths': {
            2: [{'id': '2-1', 'norm_x': 0.5, 'norm_y': 1.0}],
        },
    })
    assert loaded[2][0].norm_y == correct_legacy_norm_y(1.0)


def test_load_ui_points_image_pixels_skips_correction():
    loaded = load_ui_points_from_dict({
        'format_version': 1,
        'normalization': 'image_pixels',
        'paths': {
            2: [{'id': '2-1', 'norm_x': 0.5, 'norm_y': 0.6}],
        },
    })
    assert loaded[2][0].norm_y == 0.6


def test_load_ui_points_preserves_order():
    loaded = load_ui_points_from_dict({
        'paths': {
            2: [
                {'id': '2-2', 'norm_x': 0.1, 'norm_y': 0.2, 'state': 1, 'target_id': -1},
                {'id': '2-1', 'norm_x': 0.3, 'norm_y': 0.4, 'state': 2, 'target_id': 3},
            ],
        }
    })
    assert [wp.waypoint_id for wp in loaded[2]] == ['2-1', '2-2']


def load_ui_points_from_dict(data: dict) -> dict[int, list[WaypointUI]]:
    import tempfile

    path = Path(tempfile.mkstemp(suffix='.yaml')[1])
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    try:
        return load_ui_points(path)
    finally:
        path.unlink(missing_ok=True)
