"""Convert mission_quintuple.yaml into mission_hardcoded BT XML + nav waypoints YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

STATE_TRANSIT = 1
STATE_PICK = 2
STATE_PLACE = 3

PLACE_ARM_ID_OFFSET = 8


def arm_point_id_for_step(state: int, target_id: int) -> int:
    """Map quintuple target_id to arm_points.yaml id.

    state=2 (pick):  target_id 0~7  -> arm_point_id 0~7
    state=3 (place): target_id 0~7  -> arm_point_id 8~15
    """
    if state == STATE_PICK:
        return target_id
    if state == STATE_PLACE:
        return target_id + PLACE_ARM_ID_OFFSET
    raise ValueError(f'arm_point_id mapping not defined for state {state}')


def nav_wp_id(path: int, wp: int) -> str:
    """Stable nav waypoint id: path P, waypoint W -> nav_pP_wpW."""
    return f'nav_p{path}_wp{wp}'


def state_label(state: int) -> str:
    return {STATE_TRANSIT: 'transit', STATE_PICK: 'pick', STATE_PLACE: 'place'}.get(state, f'state{state}')


def load_quintuple(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f'Invalid quintuple YAML root in {path}')
    sequence = data.get('sequence')
    if not isinstance(sequence, list) or not sequence:
        raise ValueError(f'quintuple YAML missing non-empty sequence: {path}')
    return data


def collect_waypoint_ids(
    sequence: Sequence[Mapping[str, Any]],
    *,
    path_count: int,
    wp_count: int,
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add(path: int, wp: int) -> None:
        wp_id = nav_wp_id(path, wp)
        if wp_id not in seen:
            seen.add(wp_id)
            ordered.append(wp_id)

    for path in range(path_count):
        for wp in range(wp_count):
            add(path, wp)

    for step in sequence:
        add(int(step['path']), int(step['wp']))

    return ordered


def build_waypoints_yaml(
    waypoint_ids: Sequence[str],
    *,
    frame_id: str = 'map',
    default_x: float = 0.0,
    default_y: float = 0.0,
    default_yaw: float = 0.0,
    quintuple_path: str | Path | None = None,
    waypoint_overrides: dict[str, dict[str, float]] | None = None,
) -> str:
    """Generate waypoints YAML string.

    Args:
        waypoint_ids: ordered list of wp_ids (e.g. ['nav_p1_wp1', 'nav_p1_wp2', ...])
        waypoint_overrides: dict of wp_id -> {x, y, yaw} for specific coordinates.
    """
    overrides = waypoint_overrides or {}
    lines = [
        '# ============================================================================',
        '# 任务硬编码配置 — 导航航点（机器人 base_link 目标位姿，map 系）',
        '# ============================================================================',
        '# 由 mission_quintuple_loader 根据 mission_quintuple.yaml 自动生成，坐标请手动标定。',
    ]
    if quintuple_path is not None:
        lines.append(f'# 来源: {quintuple_path}')
    lines.extend([
        '# 航点命名: path P + wp W -> nav_pP_wpW',
        '# ============================================================================',
        '',
        'nav:',
    ])

    for wp_id in waypoint_ids:
        ov = overrides.get(wp_id, {})
        x = ov.get('x', default_x)
        y = ov.get('y', default_y)
        yaw = ov.get('yaw', default_yaw)
        lines.extend([
            f'  "{wp_id}":',
            f'    frame_id: "{frame_id}"',
            f'    x: {x:.4f}',
            f'    y: {y:.4f}',
            f'    yaw: {yaw:.4f}',
            '',
        ])
    return '\n'.join(lines).rstrip() + '\n'


def build_bt_xml(
    sequence: Sequence[Mapping[str, Any]],
    *,
    arm_timeout: float = 30.0,
    quintuple_path: str | Path | None = None,
) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!--',
        '  由 mission_quintuple_loader 根据 mission_quintuple.yaml 自动生成。',
    ]
    if quintuple_path is not None:
        lines.append(f'  来源: {quintuple_path}')
    lines.extend([
        '  state=1: Nav2PoseNode',
        '  state=2: Nav2PoseNode + ArmPickNode (target_id 0~7 -> arm_point_id 0~7)',
        '  state=3: Nav2PoseNode + ArmPlaceNode (target_id 0~7 -> arm_point_id 8~15)',
        '  motion_planner: 0=corridor multi-phase, 1=edge front-tangent, 2=edge rear-tangent',
        '-->',
        '<root BTCPP_format="4">',
        '  <BehaviorTree ID="MissionHardcoded">',
        '    <Sequence name="HardcodedMission">',
        '',
    ])

    for index, step in enumerate(sequence, start=1):
        path = int(step['path'])
        wp = int(step['wp'])
        state = int(step['state'])
        target_id = int(step.get('target_id', -1))
        wp_id = nav_wp_id(path, wp)
        label = state_label(state)

        motion_planner = int(step.get('motion_planner', 1))
        zone = 'middle' if motion_planner == 0 else 'edge'

        lines.append(
            f'      <!-- step {index}: path={path} wp={wp} state={state} ({label})'
            f' target_id={target_id} motion_planner={motion_planner} zone={zone}'
        )
        if state in (STATE_PICK, STATE_PLACE):
            arm_id = arm_point_id_for_step(state, target_id)
            lines[-1] += f' arm_point_id={arm_id} -->'
        else:
            lines[-1] += ' -->'
        lines.append(f'      <Nav2PoseNode wp_id="{wp_id}" motion_planner="{motion_planner}"/>')

        if state == STATE_PICK:
            arm_id = arm_point_id_for_step(state, target_id)
            lines.append(f'      <ArmPickNode arm_point_id="{arm_id}" timeout="{arm_timeout:.1f}"/>')
        elif state == STATE_PLACE:
            arm_id = arm_point_id_for_step(state, target_id)
            lines.append(f'      <ArmPlaceNode arm_point_id="{arm_id}" timeout="{arm_timeout:.1f}"/>')
        elif state != STATE_TRANSIT:
            raise ValueError(f'Unsupported state {state} at sequence index {index}')
        lines.append('')

    lines.extend([
        '    </Sequence>',
        '  </BehaviorTree>',
        '</root>',
        '',
    ])
    return '\n'.join(lines)


def generate_bt_artifacts(
    quintuple_path: str | Path,
    bt_xml_output: str | Path,
    waypoints_yaml_output: str | Path | None = None,
    *,
    path_count: int = 6,
    wp_count: int = 4,
    arm_timeout: float = 30.0,
    frame_id: str = 'map',
    waypoint_overrides: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    quintuple_path = Path(quintuple_path)
    data = load_quintuple(quintuple_path)
    sequence = data['sequence']

    waypoint_ids = collect_waypoint_ids(sequence, path_count=path_count, wp_count=wp_count)
    bt_xml_text = build_bt_xml(
        sequence,
        arm_timeout=arm_timeout,
        quintuple_path=quintuple_path,
    )

    bt_xml_output = Path(bt_xml_output)
    bt_xml_output.parent.mkdir(parents=True, exist_ok=True)
    bt_xml_output.write_text(bt_xml_text, encoding='utf-8')

    waypoints_output: str | None = None
    if waypoints_yaml_output:
        waypoints_text = build_waypoints_yaml(
            waypoint_ids,
            frame_id=frame_id,
            quintuple_path=quintuple_path,
            waypoint_overrides=waypoint_overrides,
        )
        waypoints_yaml_output = Path(waypoints_yaml_output)
        waypoints_yaml_output.parent.mkdir(parents=True, exist_ok=True)
        waypoints_yaml_output.write_text(waypoints_text, encoding='utf-8')
        waypoints_output = str(waypoints_yaml_output)

    step_count = len(sequence)

    return {
        'step_count': step_count,
        'waypoint_count': len(waypoint_ids),
        'bt_xml_output': str(bt_xml_output),
        'waypoints_yaml_output': waypoints_output,
        'switch_mode': data.get('switch_mode'),
        'planner_variant': data.get('planner_variant'),
    }
