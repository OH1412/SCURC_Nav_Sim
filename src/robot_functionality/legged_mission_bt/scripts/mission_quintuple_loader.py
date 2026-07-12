#!/usr/bin/env python3
"""Subscribe /mission/plan_ready, convert mission_quintuple.yaml to BT artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from quintuple_bt_generator import (
    STATE_PICK,
    STATE_PLACE,
    STATE_TRANSIT,
    arm_point_id_for_step,
    build_waypoints_yaml,
    collect_waypoint_ids,
    generate_bt_artifacts,
    load_quintuple,
    nav_wp_id,
)


class MissionQuintupleLoader(Node):
    def __init__(self) -> None:
        super().__init__('mission_quintuple_loader')

        ws_root = Path(__file__).resolve().parents[4]
        default_quintuple = ws_root / 'src/legged_mission_planner_f_r/tmp/mission_quintuple.yaml'
        pkg_root = Path(__file__).resolve().parents[1]
        default_bt_xml = pkg_root / 'behavior_trees/mission_hardcoded.xml'

        self.declare_parameter('plan_ready_topic', '/mission/plan_ready')
        self.declare_parameter('bt_config_ready_topic', '/mission/bt_config_ready')
        self.declare_parameter('wait_for_trigger', False)
        self.declare_parameter('quintuple_yaml', str(default_quintuple))
        self.declare_parameter('bt_xml_output', str(default_bt_xml))
        self.declare_parameter('waypoints_yaml_output', '')
        self.declare_parameter('path_count', 6)
        self.declare_parameter('wp_count', 4)
        self.declare_parameter('arm_timeout', 30.0)
        self.declare_parameter('nav_frame_id', 'map')
        self.declare_parameter('send_p0_wp0', False)  # false=过滤掉 nav_p0_wp0

        self._plan_ready_topic = self.get_parameter('plan_ready_topic').value
        self._bt_config_ready_topic = self.get_parameter('bt_config_ready_topic').value
        self._wait_for_trigger = bool(self.get_parameter('wait_for_trigger').value)
        self._quintuple_yaml = Path(self.get_parameter('quintuple_yaml').value)
        self._bt_xml_output = Path(self.get_parameter('bt_xml_output').value)
        waypoints_yaml_output = str(self.get_parameter('waypoints_yaml_output').value).strip()
        self._waypoints_yaml_output = waypoints_yaml_output or None
        self._path_count = int(self.get_parameter('path_count').value)
        self._wp_count = int(self.get_parameter('wp_count').value)
        self._arm_timeout = float(self.get_parameter('arm_timeout').value)
        self._nav_frame_id = str(self.get_parameter('nav_frame_id').value)
        self._send_p0_wp0 = bool(self.get_parameter('send_p0_wp0').value)

        mission_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._ready_pub = self.create_publisher(Bool, self._bt_config_ready_topic, mission_qos)
        self._ready_timer = None

        if self._wait_for_trigger:
            self.create_subscription(
                Bool, self._plan_ready_topic, self._on_plan_ready, mission_qos,
            )
            self.get_logger().info(f'Waiting for plan ready on {self._plan_ready_topic}')
        else:
            self.get_logger().info('wait_for_trigger=false, converting immediately...')

        self.get_logger().info(f'Quintuple input: {self._quintuple_yaml}')
        self.get_logger().info(f'BT XML output: {self._bt_xml_output}')
        if self._waypoints_yaml_output:
            self.get_logger().info(f'Waypoints output: {self._waypoints_yaml_output}')
        self.get_logger().info(f'Will publish bt config ready on {self._bt_config_ready_topic}')

        if not self._wait_for_trigger:
            self._convert_and_publish()

    def _on_plan_ready(self, msg: Bool) -> None:
        if not msg.data:
            return
        self._convert_and_publish()

    def _convert_and_publish(self) -> None:
        try:
            summary = self._convert()
        except Exception as exc:
            self.get_logger().error(f'Failed to convert quintuple plan: {exc}')
            return

        self.get_logger().info(
            'Published bt config ready: '
            f'{summary["step_count"]} steps, '
            f'{summary["waypoint_count"]} nav waypoints -> '
            f'{summary["bt_xml_output"]}'
        )

        # 定时反复发送，确保 bt_install 无论何时订阅都能收到
        if self._ready_timer is None:
            self._ready_timer = self.create_timer(0.5, self._publish_ready)
        self._publish_ready()

    def _publish_ready(self) -> None:
        ready = Bool()
        ready.data = True
        self._ready_pub.publish(ready)

    def _convert(self) -> dict:
        if not self._quintuple_yaml.is_file():
            raise FileNotFoundError(f'Quintuple YAML not found: {self._quintuple_yaml}')

        data = load_quintuple(self._quintuple_yaml)
        sequence: list[dict] = list(data['sequence'])

        # ── Filter nav_p0_wp0 ──────────────────────────────────────────
        p0_wp0_count = sum(
            1 for s in sequence if int(s['path']) == 0 and int(s['wp']) == 0
        )
        if not self._send_p0_wp0:
            sequence = [
                s for s in sequence
                if not (int(s['path']) == 0 and int(s['wp']) == 0)
            ]
            if p0_wp0_count:
                self.get_logger().info(
                    f'send_p0_wp0=false: filtered {p0_wp0_count} nav_p0_wp0 step(s)'
                )
        else:
            self.get_logger().info(
                f'send_p0_wp0=true: keeping {p0_wp0_count} nav_p0_wp0 step(s)'
            )

        waypoint_ids = collect_waypoint_ids(
            sequence, path_count=self._path_count, wp_count=self._wp_count,
        )
        # Filter waypoint list to match sequence filtering
        if not self._send_p0_wp0:
            waypoint_ids = [w for w in waypoint_ids if w != 'nav_p0_wp0']

        # ── BT XML ─────────────────────────────────────────────────────
        bt_xml_text = self._build_bt_xml(sequence)
        self._bt_xml_output.parent.mkdir(parents=True, exist_ok=True)
        self._bt_xml_output.write_text(bt_xml_text, encoding='utf-8')

        # ── Waypoints YAML ─────────────────────────────────────────────
        waypoints_output: str | None = None
        if self._waypoints_yaml_output:
            # Fixed coordinates for intermediate waypoints after first pick
            waypoint_overrides = {
                'nav_p1_wp2': {'x': 2.1695, 'y': -1.7000, 'yaw': 0.0000},
                'nav_p1_wp3': {'x': 3.8315, 'y': -1.7000, 'yaw': 0.0000},
            }
            waypoints_text = build_waypoints_yaml(
                waypoint_ids,
                frame_id=self._nav_frame_id,
                quintuple_path=self._quintuple_yaml,
                waypoint_overrides=waypoint_overrides,
            )
            waypoints_yaml_path = Path(self._waypoints_yaml_output)
            waypoints_yaml_path.parent.mkdir(parents=True, exist_ok=True)
            waypoints_yaml_path.write_text(waypoints_text, encoding='utf-8')
            waypoints_output = str(waypoints_yaml_path)

        step_count = len(sequence)
        self.get_logger().info(
            f'Generated BT from {self._quintuple_yaml} '
            f'({data.get("planner_variant")}, {data.get("switch_mode")})'
        )
        return {
            'step_count': step_count,
            'waypoint_count': len(waypoint_ids),
            'bt_xml_output': str(self._bt_xml_output),
            'waypoints_yaml_output': waypoints_output,
            'switch_mode': data.get('switch_mode'),
            'planner_variant': data.get('planner_variant'),
        }

    # ── BT XML generation (reads motion_planner, not limit_yaw) ────────
    def _build_bt_xml(self, sequence: list[dict]) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!--',
            '  由 mission_quintuple_loader 根据 mission_quintuple.yaml 自动生成。',
        ]
        lines.append(f'  来源: {self._quintuple_yaml}')
        lines.extend([
            '  state=1: Nav2PoseNode',
            '  state=2: Nav2PoseNode + ArmPickNode (target_id 0~7 -> arm_point_id 0~7)',
            '  state=3: Nav2PoseNode + ArmPlaceNode (target_id 0~7 -> arm_point_id 8~15)',
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
            motion_planner = int(step.get('motion_planner', 1))
            zone = 'straight' if motion_planner == 3 else 'edge'
            label = {STATE_TRANSIT: 'transit', STATE_PICK: 'pick',
                     STATE_PLACE: 'place'}.get(state, f'state{state}')

            lines.append(
                f'      <!-- step {index}: path={path} wp={wp} state={state} ({label})'
                f' target_id={target_id} motion_planner={motion_planner} zone={zone}'
            )
            if state in (STATE_PICK, STATE_PLACE):
                arm_id = arm_point_id_for_step(state, target_id)
                lines[-1] += f' arm_point_id={arm_id} -->'
            else:
                lines[-1] += ' -->'
            lines.append(
                f'      <Nav2PoseNode wp_id="{wp_id}" motion_planner="{motion_planner}"/>'
            )

            if state == STATE_PICK:
                arm_id = arm_point_id_for_step(state, target_id)
                lines.append(
                    f'      <ArmPickNode arm_point_id="{arm_id}"'
                    f' timeout="{self._arm_timeout:.1f}"/>'
                )
            elif state == STATE_PLACE:
                arm_id = arm_point_id_for_step(state, target_id)
                lines.append(
                    f'      <ArmPlaceNode arm_point_id="{arm_id}"'
                    f' timeout="{self._arm_timeout:.1f}"/>'
                )
            elif state != STATE_TRANSIT:
                raise ValueError(
                    f'Unsupported state {state} at sequence index {index}'
                )
            lines.append('')

            # ── Fixed: after the first step, always insert two intermediate transit waypoints ──
            if index == 1:
                lines.append(
                    '      <!-- Fixed intermediate waypoints after first pick (nav_p1_wp2, nav_p1_wp3) -->'
                )
                lines.append(
                    '      <Nav2PoseNode wp_id="nav_p1_wp2" motion_planner="1"/>'
                )
                lines.append('')
                lines.append(
                    '      <Nav2PoseNode wp_id="nav_p1_wp3" motion_planner="1"/>'
                )
                lines.append('')

        lines.extend([
            '    </Sequence>',
            '  </BehaviorTree>',
            '</root>',
            '',
        ])
        return '\n'.join(lines)


def _run_once(args: argparse.Namespace) -> None:
    summary = generate_bt_artifacts(
        args.quintuple_yaml,
        args.bt_xml_output,
        args.waypoints_yaml_output,
        path_count=args.path_count,
        wp_count=args.wp_count,
        arm_timeout=args.arm_timeout,
    )
    print(
        f'Generated {summary["step_count"]} steps, '
        f'{summary["waypoint_count"]} waypoints'
    )
    print(f'  BT XML: {summary["bt_xml_output"]}')
    if summary['waypoints_yaml_output']:
        print(f'  Nav YAML: {summary["waypoints_yaml_output"]}')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Mission quintuple -> BT converter node')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Convert once from CLI and exit (no ROS spin)',
    )
    parser.add_argument('--quintuple-yaml')
    parser.add_argument('--bt-xml-output')
    parser.add_argument('--waypoints-yaml-output')
    parser.add_argument('--path-count', type=int, default=6)
    parser.add_argument('--wp-count', type=int, default=4)
    parser.add_argument('--arm-timeout', type=float, default=30.0)
    args, ros_args = parser.parse_known_args(argv)

    if args.once:
        ws_root = Path(__file__).resolve().parents[4]
        pkg_root = Path(__file__).resolve().parents[1]
        args.quintuple_yaml = args.quintuple_yaml or str(
            ws_root / 'src/legged_mission_planner_f_r/tmp/mission_quintuple.yaml'
        )
        args.bt_xml_output = args.bt_xml_output or str(
            pkg_root / 'behavior_trees/mission_hardcoded.xml'
        )
        _run_once(args)
        return

    rclpy.init(args=ros_args)
    node = MissionQuintupleLoader()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
