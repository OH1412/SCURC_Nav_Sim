#!/usr/bin/env python3
"""Subscribe /mission/plan_ready, convert mission_quintuple.yaml to BT artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from quintuple_bt_generator import generate_bt_artifacts


class MissionQuintupleLoader(Node):
    def __init__(self) -> None:
        super().__init__('mission_quintuple_loader')

        ws_root = Path(__file__).resolve().parents[4]
        default_quintuple = ws_root / 'src/legged_mission_planner_f_r/tmp/mission_quintuple.yaml'
        pkg_root = Path(__file__).resolve().parents[1]
        default_bt_xml = pkg_root / 'behavior_trees/mission_hardcoded.xml'

        self.declare_parameter('plan_ready_topic', '/mission/plan_ready')
        self.declare_parameter('bt_config_ready_topic', '/mission/bt_config_ready')
        self.declare_parameter('quintuple_yaml', str(default_quintuple))
        self.declare_parameter('bt_xml_output', str(default_bt_xml))
        self.declare_parameter('waypoints_yaml_output', '')
        self.declare_parameter('path_count', 6)
        self.declare_parameter('wp_count', 4)
        self.declare_parameter('arm_timeout', 30.0)
        self.declare_parameter('nav_frame_id', 'map')

        self._plan_ready_topic = self.get_parameter('plan_ready_topic').value
        self._bt_config_ready_topic = self.get_parameter('bt_config_ready_topic').value
        self._quintuple_yaml = Path(self.get_parameter('quintuple_yaml').value)
        self._bt_xml_output = Path(self.get_parameter('bt_xml_output').value)
        waypoints_yaml_output = str(self.get_parameter('waypoints_yaml_output').value).strip()
        self._waypoints_yaml_output = waypoints_yaml_output or None
        self._path_count = int(self.get_parameter('path_count').value)
        self._wp_count = int(self.get_parameter('wp_count').value)
        self._arm_timeout = float(self.get_parameter('arm_timeout').value)
        self._nav_frame_id = str(self.get_parameter('nav_frame_id').value)

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self._ready_pub = self.create_publisher(Bool, self._bt_config_ready_topic, qos)
        self.create_subscription(Bool, self._plan_ready_topic, self._on_plan_ready, qos)

        self.get_logger().info(f'Waiting for plan ready on {self._plan_ready_topic}')
        self.get_logger().info(f'Quintuple input: {self._quintuple_yaml}')
        self.get_logger().info(f'BT XML output: {self._bt_xml_output}')
        if self._waypoints_yaml_output:
            self.get_logger().info(f'Waypoints output: {self._waypoints_yaml_output}')
        self.get_logger().info(f'Will publish bt config ready on {self._bt_config_ready_topic}')

    def _on_plan_ready(self, msg: Bool) -> None:
        if not msg.data:
            return
        try:
            summary = self._convert()
        except Exception as exc:
            self.get_logger().error(f'Failed to convert quintuple plan: {exc}')
            return

        ready = Bool()
        ready.data = True
        self._ready_pub.publish(ready)
        self.get_logger().info(
            'Published bt config ready: '
            f'{summary["step_count"]} steps, '
            f'{summary["waypoint_count"]} nav waypoints -> '
            f'{summary["bt_xml_output"]}'
        )

    def _convert(self) -> dict:
        if not self._quintuple_yaml.is_file():
            raise FileNotFoundError(f'Quintuple YAML not found: {self._quintuple_yaml}')

        summary = generate_bt_artifacts(
            self._quintuple_yaml,
            self._bt_xml_output,
            self._waypoints_yaml_output,
            path_count=self._path_count,
            wp_count=self._wp_count,
            arm_timeout=self._arm_timeout,
            frame_id=self._nav_frame_id,
        )
        self.get_logger().info(
            f'Generated BT from {self._quintuple_yaml} '
            f'({summary.get("planner_variant")}, {summary.get("switch_mode")})'
        )
        return summary


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
