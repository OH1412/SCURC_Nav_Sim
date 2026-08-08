#!/usr/bin/env python3
# ============================================================================
# 实时显示 /state_estimation 位置，按 ENTER 保存到 point.yaml
# ============================================================================
# 用法:
#   ros2 run legged_bringup save_current_point.py
#   ros2 run legged_bringup save_current_point.py --ros-args -p output_dir:=/path/to/output
#
# 交互:
#   - 实时刷新显示: x, y, yaw
#   - 按 ENTER → 保存当前位置到 point.yaml（覆盖写入）
#   - Ctrl+C → 自动保存后退出
# ============================================================================

import math
import os
import signal
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


def quat_to_yaw(ori) -> float:
    siny = 2.0 * (ori.w * ori.z + ori.x * ori.y)
    cosy = 1.0 - 2.0 * (ori.y * ori.y + ori.z * ori.z)
    return math.atan2(siny, cosy)


class PointSaver(Node):
    """订阅 /state_estimation，提供当前位置查询和 YAML 保存"""

    def __init__(self):
        super().__init__('point_saver')

        self.declare_parameter('output_dir', '')
        self.declare_parameter('output_file', 'point.yaml')

        self._current_odom: Odometry | None = None
        self._lock = threading.Lock()

        self._sub = self.create_subscription(
            Odometry, '/state_estimation', self._odom_cb, 10)

        # 输出路径
        out_dir = self.get_parameter('output_dir').value
        if not out_dir:
            out_dir = os.path.dirname(os.path.realpath(__file__))
        out_file = self.get_parameter('output_file').value
        self._output_path = os.path.join(out_dir, out_file)

    def _odom_cb(self, msg: Odometry):
        with self._lock:
            self._current_odom = msg

    def get_pose(self) -> dict | None:
        with self._lock:
            if self._current_odom is None:
                return None
            pos = self._current_odom.pose.pose.position
            ori = self._current_odom.pose.pose.orientation
        return {
            'x': pos.x, 'y': pos.y, 'z': pos.z,
            'yaw': quat_to_yaw(ori),
        }

    def save(self) -> bool:
        pose = self.get_pose()
        if pose is None:
            return False
        self._write_yaml(pose)
        return True

    def _write_yaml(self, pose: dict):
        import yaml
        data = {
            'point': {
                'x': round(pose['x'], 4),
                'y': round(pose['y'], 4),
                'z': round(pose['z'], 4),
                'yaw': round(pose['yaw'], 4),
            }
        }
        with open(self._output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


# ============================================================================
# 主循环 — 独立线程读 stdin，主线程刷新显示
# ============================================================================
def input_thread(node: PointSaver, stop_event: threading.Event):
    """阻塞读 stdin，收到换行即保存"""
    while not stop_event.is_set():
        try:
            line = sys.stdin.readline()
            if not line:  # EOF
                break
            if node.save():
                pose = node.get_pose()
                if pose:
                    sys.stdout.write(
                        f'\n✅ 已保存: x={pose["x"]:.4f}  y={pose["y"]:.4f}  '
                        f'yaw={pose["yaw"]:.4f} rad ({math.degrees(pose["yaw"]):.1f}°)\n'
                    )
                    sys.stdout.write(f'   文件: {node._output_path}\n')
                    sys.stdout.flush()
            else:
                sys.stdout.write('\n⚠️  尚未收到 /state_estimation 数据\n')
                sys.stdout.flush()
        except Exception:
            break


def main():
    rclpy.init(args=sys.argv)

    node = PointSaver()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    # ROS spin 线程
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # stdin 输入线程
    stop_event = threading.Event()
    in_thread = threading.Thread(target=input_thread, args=(node, stop_event), daemon=True)
    in_thread.start()

    # 退出时自动保存
    def on_exit(sig=None, frame=None):
        stop_event.set()
        if node.save():
            pose = node.get_pose()
            sys.stdout.write(
                f'\n💾 退出自动保存: x={pose["x"]:.4f}  y={pose["y"]:.4f}  '
                f'yaw={pose["yaw"]:.4f} rad\n'
            )
        sys.stdout.write('👋 再见\n')
        sys.stdout.flush()
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    # 主循环 — 刷新显示
    print('=' * 60)
    print('📍 实时位置监控')
    print(f'   保存目标: {node._output_path}')
    print('   按 ENTER → 保存当前位置')
    print('   Ctrl+C  → 自动保存后退出')
    print('=' * 60)

    last_print = 0.0
    while rclpy.ok():
        now = time.time()
        if now - last_print < 0.25:  # 4Hz 刷新
            time.sleep(0.05)
            continue
        last_print = now

        pose = node.get_pose()
        if pose:
            sys.stdout.write(
                f'\r📍 x={pose["x"]:.3f}  y={pose["y"]:.3f}  '
                f'yaw={pose["yaw"]:.3f} rad ({math.degrees(pose["yaw"]):.1f}°)  '
                f'[ENTER=保存 | Ctrl+C=退出]  '
            )
            sys.stdout.flush()
        else:
            sys.stdout.write(
                f'\r⏳ 等待 /state_estimation...'
            )
            sys.stdout.flush()

    on_exit()


if __name__ == '__main__':
    main()
