"""Convert mission_quintuple.yaml into mission_hardcoded BT XML + nav waypoints YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

STATE_TRANSIT = 1
STATE_PICK = 2
STATE_PLACE = 3


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
) -> str:
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
        lines.extend([
            f'  "{wp_id}":',
            f'    frame_id: "{frame_id}"',
            f'    x: {default_x}',
            f'    y: {default_y}',
            f'    yaw: {default_yaw}',
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
        '  state=2: Nav2PoseNode + ArmPickNode',
        '  state=3: Nav2PoseNode + ArmPlaceNode',
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

        lines.append(
            f'      <!-- step {index}: path={path} wp={wp} state={state} ({label})'
            f' target_id={target_id} -->'
        )
        lines.append(f'      <Nav2PoseNode wp_id="{wp_id}"/>')

        if state == STATE_PICK:
            lines.append(f'      <ArmPickNode arm_point_id="{target_id}" timeout="{arm_timeout:.1f}"/>')
        elif state == STATE_PLACE:
            lines.append(f'      <ArmPlaceNode arm_point_id="{target_id}" timeout="{arm_timeout:.1f}"/>')
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
    waypoints_yaml_output: str | Path,
    *,
    path_count: int = 6,
    wp_count: int = 4,
    arm_timeout: float = 30.0,
    frame_id: str = 'map',
) -> dict[str, Any]:
    quintuple_path = Path(quintuple_path)
    data = load_quintuple(quintuple_path)
    sequence = data['sequence']

    waypoint_ids = collect_waypoint_ids(sequence, path_count=path_count, wp_count=wp_count)
    waypoints_text = build_waypoints_yaml(
        waypoint_ids,
        frame_id=frame_id,
        quintuple_path=quintuple_path,
    )
    bt_xml_text = build_bt_xml(
        sequence,
        arm_timeout=arm_timeout,
        quintuple_path=quintuple_path,
    )

    bt_xml_output = Path(bt_xml_output)
    waypoints_yaml_output = Path(waypoints_yaml_output)
    bt_xml_output.parent.mkdir(parents=True, exist_ok=True)
    waypoints_yaml_output.parent.mkdir(parents=True, exist_ok=True)
    bt_xml_output.write_text(bt_xml_text, encoding='utf-8')
    waypoints_yaml_output.write_text(waypoints_text, encoding='utf-8')

    return {
        'step_count': len(sequence),
        'waypoint_count': len(waypoint_ids),
        'bt_xml_output': str(bt_xml_output),
        'waypoints_yaml_output': str(waypoints_yaml_output),
        'switch_mode': data.get('switch_mode'),
        'planner_variant': data.get('planner_variant'),
    }
