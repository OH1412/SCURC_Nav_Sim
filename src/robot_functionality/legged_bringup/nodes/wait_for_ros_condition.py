#!/usr/bin/env python3
"""Wait for ROS conditions then exit 0 (success) or 1 (timeout). Used by launch event chains."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_log_client import log_event


class WaitForRosCondition(Node):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__('wait_for_ros_condition')
        self._args = args
        self._done = False
        self._deadline = time.monotonic() + args.timeout
        self._checks: list[str] = []

        if not args.skip_stand_up:
            self._checks.append(f'站立完成({args.stand_up_done_topic})')
            self.create_subscription(
                self._import_bool(),
                args.stand_up_done_topic,
                self._on_stand_up_done,
                10,
            )

        if args.reloc_ready_topic:
            self._checks.append(f'重定位就绪({args.reloc_ready_topic})')
            self.create_subscription(
                self._import_bool(),
                args.reloc_ready_topic,
                self._on_reloc_ready,
                10,
            )

        if args.topic:
            msg_type = self._import_msg_type(args.msg_type)
            self._checks.append(f'话题({args.topic})')
            self.create_subscription(msg_type, args.topic, self._on_topic, qos_profile_sensor_data)

        if args.lifecycle_node:
            self._checks.append(f'Nav2生命周期激活({args.lifecycle_node})')
            self._lifecycle_ready = False
            from lifecycle_msgs.srv import GetState

            self._get_state_type = GetState
            self._lifecycle_client = self.create_client(
                GetState, f'{args.lifecycle_node}/get_state'
            )

        if args.action_name:
            self._checks.append(f'导航动作就绪({args.action_name})')
            self._action_ready = False
            from rclpy.action import ActionClient

            action_type = self._import_action_type(args.action_type)
            self._action_client = ActionClient(self, action_type, args.action_name)

        if args.publisher_topic:
            self._checks.append(f'发布者就绪({args.publisher_topic})')
            self._publisher_ready = False

        if args.bt_config_ready_topic:
            self._checks.append(f'行为树配置就绪({args.bt_config_ready_topic})')
            self.create_subscription(
                self._import_bool(),
                args.bt_config_ready_topic,
                self._on_bt_config_ready,
                10,
            )

        self._stand_up_done = args.skip_stand_up
        self._reloc_ready = args.reloc_ready_topic is None
        self._topic_seen = args.topic is None
        self._bt_config_ready = args.bt_config_ready_topic is None

        self.get_logger().info(f'Waiting for: {", ".join(self._checks) or "(nothing)"}')
        self.create_timer(0.5, self._poll)

    @staticmethod
    def _import_bool():
        from std_msgs.msg import Bool

        return Bool

    @staticmethod
    def _import_msg_type(path: str):
        module_name, _, cls_name = path.partition('/msg/')
        if not cls_name:
            raise ValueError(f'Invalid msg type: {path}')
        import importlib

        module = importlib.import_module(f'{module_name}.msg')
        return getattr(module, cls_name)

    @staticmethod
    def _import_action_type(path: str):
        module_name, _, cls_name = path.partition('/action/')
        if not cls_name:
            raise ValueError(f'Invalid action type: {path}')
        import importlib

        module = importlib.import_module(f'{module_name}.action')
        return getattr(module, cls_name)

    def _on_stand_up_done(self, msg) -> None:
        if msg.data:
            self._stand_up_done = True

    def _on_reloc_ready(self, msg) -> None:
        if msg.data:
            self._reloc_ready = True

    def _on_bt_config_ready(self, msg) -> None:
        if msg.data:
            self._bt_config_ready = True

    def _on_topic(self, _msg) -> None:
        self._topic_seen = True

    def _poll(self) -> None:
        if self._done:
            return
        if time.monotonic() > self._deadline:
            self.get_logger().error('Timeout waiting for readiness conditions')
            self._finish(1)
            return

        if not self._stand_up_done or not self._reloc_ready or not self._topic_seen or not self._bt_config_ready:
            return

        if self._args.lifecycle_node and not self._check_lifecycle():
            return

        if self._args.action_name and not self._check_action():
            return

        if self._args.publisher_topic and not self._check_publisher():
            return

        self.get_logger().info('All readiness conditions satisfied')
        self._finish(0)

    def _check_lifecycle(self) -> bool:
        if getattr(self, '_lifecycle_ready', False):
            return True
        if not self._lifecycle_client.service_is_ready():
            return False
        if not hasattr(self, '_lifecycle_future') or self._lifecycle_future.done():
            req = self._get_state_type.Request()
            self._lifecycle_future = self._lifecycle_client.call_async(req)
            return False
        if not self._lifecycle_future.done():
            return False
        try:
            resp = self._lifecycle_future.result()
            from lifecycle_msgs.msg import State

            if resp.current_state.id == State.PRIMARY_STATE_ACTIVE:
                self._lifecycle_ready = True
                return True
        except Exception as exc:
            self.get_logger().warn(f'Lifecycle check failed: {exc}')
        self._lifecycle_future = None
        return False

    def _check_action(self) -> bool:
        if getattr(self, '_action_ready', False):
            return True
        if self._action_client.wait_for_server(timeout_sec=0.0):
            self._action_ready = True
            return True
        return False

    def _check_publisher(self) -> bool:
        if getattr(self, '_publisher_ready', False):
            return True
        pubs = self.get_publishers_info_by_topic(self._args.publisher_topic)
        if pubs:
            self._publisher_ready = True
            return True
        return False

    def _finish(self, code: int) -> None:
        if code == 0:
            log_event(
                self, 'wait_for_ros_condition', 'READINESS_GATE_PASSED',
                f'已满足条件: {"、".join(self._checks)}',
            )
        else:
            log_event(
                self, 'wait_for_ros_condition', 'READINESS_GATE_TIMEOUT',
                f'超时={self._args.timeout}秒 待满足条件: {"、".join(self._checks)}',
                level='ERROR',
            )
        self._done = True
        self._exit_code = code
        rclpy.shutdown()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Wait for ROS readiness conditions')
    parser.add_argument('--timeout', type=float, default=120.0)
    parser.add_argument('--stand-up-done-topic', default='/bringup/stand_up_done')
    parser.add_argument('--skip-stand-up', action='store_true')
    parser.add_argument('--reloc-ready-topic', default='')
    parser.add_argument('--topic', default='')
    parser.add_argument('--msg-type', default='sensor_msgs/msg/PointCloud2')
    parser.add_argument('--lifecycle-node', default='')
    parser.add_argument('--action-name', default='')
    parser.add_argument('--action-type', default='nav2_msgs/action/NavigateToPose')
    parser.add_argument('--publisher-topic', default='')
    parser.add_argument('--bt-config-ready-topic', default='')
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.reloc_ready_topic == '':
        args.reloc_ready_topic = None
    if args.bt_config_ready_topic == '':
        args.bt_config_ready_topic = None

    rclpy.init(args=argv)
    node = WaitForRosCondition(args)
    exit_code = 1
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        exit_code = 1
    finally:
        exit_code = getattr(node, '_exit_code', exit_code)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
