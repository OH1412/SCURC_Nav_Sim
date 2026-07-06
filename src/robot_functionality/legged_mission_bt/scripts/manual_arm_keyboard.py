#!/usr/bin/env python3
"""终端交互：Enter 确认到位 → 输入 arm_point_id → 回复 BT。"""

from __future__ import annotations

import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from legged_mission_bt.msg import ArmWaypoint, ManualArmInput, ManualArmPrompt

PICK_MIN, PICK_MAX = 0, 7
PLACE_MIN, PLACE_MAX = 8, 15

PROMPT_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)
INPUT_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


class ManualArmKeyboard(Node):

    def __init__(self) -> None:
        super().__init__('manual_arm_keyboard')

        self.declare_parameter('manual_arm_prompt_topic', '/mission_bt/manual_arm_prompt')
        self.declare_parameter('manual_arm_input_topic', '/mission_bt/manual_arm_input')

        prompt_topic = self.get_parameter('manual_arm_prompt_topic').value
        input_topic = self.get_parameter('manual_arm_input_topic').value

        self._input_pub = self.create_publisher(ManualArmInput, input_topic, INPUT_QOS)
        self.create_subscription(ManualArmPrompt, prompt_topic, self._on_prompt, PROMPT_QOS)
        self.create_subscription(ArmWaypoint, '/mission_bt/arm_waypoint', self._on_arm_waypoint, INPUT_QOS)

        self._lock = threading.Lock()
        self._pending_prompt: ManualArmPrompt | None = None
        self._last_banner_step = 0
        self._waiting_arm = False

        self._worker = threading.Thread(target=self._stdin_loop, daemon=True)
        self._worker.start()

        print('\n[manual_arm_keyboard] 就绪 — 请在本终端操作')
        print('  等待 BT 启动（约 25s）后会出现「步骤 N/6」横幅')
        print('  也可看 arm_manual_test 终端是否有: waiting manual confirm\n')

    def _on_prompt(self, msg: ManualArmPrompt) -> None:
        with self._lock:
            self._pending_prompt = msg

        if self._waiting_arm and msg.step_index <= self._last_banner_step:
            return
        if msg.step_index == self._last_banner_step:
            return
        self._last_banner_step = msg.step_index
        self._waiting_arm = False

        action = '抓取' if msg.action == ManualArmPrompt.ACTION_PICK else '放置'
        id_range = (
            f'{PICK_MIN}~{PICK_MAX}' if msg.action == ManualArmPrompt.ACTION_PICK
            else f'{PLACE_MIN}~{PLACE_MAX}')
        print(
            f'\n{"=" * 56}\n'
            f'  步骤 {msg.step_index}/6: {action}\n'
            f'  {msg.hint}\n'
            f'  有效点位: {id_range}\n'
            f'  → 遥控到位后按 Enter\n'
            f'{"=" * 56}',
            flush=True)

    def _on_arm_waypoint(self, msg: ArmWaypoint) -> None:
        print(
            f'📍 物体在 base_link 下坐标: '
            f'x={msg.x:.1f} mm  y={msg.y:.1f} mm  z={msg.z:.1f} mm  yaw={msg.yaw:.3f} rad',
            flush=True)

    def _stdin_loop(self) -> None:
        if not sys.stdin.isatty():
            print('[manual_arm_keyboard] 警告: stdin 不是 TTY，Enter 输入可能不可用', flush=True)

        while rclpy.ok():
            try:
                line = sys.stdin.readline()
            except Exception:
                break

            if line is None:
                break
            if line == '':
                time.sleep(0.2)
                continue

            with self._lock:
                msg = self._pending_prompt

            if msg is None:
                print(
                    '[manual_arm_keyboard] BT 尚未发出步骤（请等 arm_manual_test 里 '
                    '出现 waiting manual confirm）',
                    flush=True)
                continue

            action = '抓取' if msg.action == ManualArmPrompt.ACTION_PICK else '放置'
            id_min = PICK_MIN if msg.action == ManualArmPrompt.ACTION_PICK else PLACE_MIN
            id_max = PICK_MAX if msg.action == ManualArmPrompt.ACTION_PICK else PLACE_MAX

            while rclpy.ok():
                try:
                    raw = input(f'请输入{action}点位 ({id_min}~{id_max}): ').strip()
                except EOFError:
                    return
                if not raw:
                    print('点位不能为空，请重新输入', flush=True)
                    continue
                try:
                    point_id = int(raw)
                except ValueError:
                    print(f'无效输入 "{raw}"，请输入整数', flush=True)
                    continue
                if not (id_min <= point_id <= id_max):
                    print(
                        f'点位 {point_id} 不在 {action} 范围 {id_min}~{id_max}，请重新输入',
                        flush=True)
                    continue

                out = ManualArmInput()
                out.arm_point_id = point_id
                self._input_pub.publish(out)
                with self._lock:
                    self._pending_prompt = None
                self._waiting_arm = True
                print(
                    f'→ 已提交 arm_point_id={point_id}，等待机械臂{action}完成...\n'
                    f'  （请看 arm_manual_test 终端：received manual input / arm_pose_request）\n',
                    flush=True)
                break


def main() -> None:
    rclpy.init()
    node = ManualArmKeyboard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
