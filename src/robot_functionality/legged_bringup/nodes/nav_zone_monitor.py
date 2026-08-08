#!/usr/bin/env python3
"""External monitor: commanded nav zone vs controller_server critic scales.

Use this when you doubt edge→middle really happened.

Truth table (store params on /controller_server):
  middle  : MaintainYawCritic.scale ≈ 5000, RotateToPathCritic.scale ≈ 0
  edge    : MaintainYawCritic.scale ≈ 0,    RotateToPathCritic.scale ≈ 96
  straight: MaintainYawCritic.scale ≈ 0,    RotateToPathCritic.scale ≈ 0,
            and usually max_vel_theta ≈ 0

Important BT semantics (Nav2PoseNode):
  mp=0 / mp=3 : startup zone is already middle/straight — NO edge→middle hop
  mp=1 / mp=2 : startup edge, then edge→middle when dist < middle_zone_distance

Examples:
  ros2 run legged_bringup nav_zone_monitor.py
  # or without install:
  python3 .../nodes/nav_zone_monitor.py
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import rclpy
from rcl_interfaces.srv import GetParameters
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import String


LATCHED_QOS = QoSProfile(
    depth=1,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
)

KEY_MAINTAIN = 'FollowPath.dwb_yaw_constraint::MaintainYawCritic.scale'
KEY_ROTATE = 'FollowPath.dwb_yaw_constraint::RotateToPathCritic.scale'
KEY_PATH_ALIGN = 'FollowPath.PathAlign.scale'


def infer_zone(maintain: float | None, rotate: float | None) -> str:
    if maintain is None or rotate is None:
        return 'unknown'
    if maintain >= 100.0 and rotate < 1.0:
        return 'middle'
    if rotate >= 10.0 and maintain < 1.0:
        return 'edge'
    if maintain < 1.0 and rotate < 1.0:
        return 'straight_or_idle'
    return f'ambiguous(m={maintain:.1f},r={rotate:.1f})'


class NavZoneMonitor(Node):
    def __init__(self) -> None:
        super().__init__('nav_zone_monitor')

        self.declare_parameter('nav_zone_topic', '/mission_bt/nav_zone')
        self.declare_parameter('target_node', 'controller_server')
        self.declare_parameter('poll_hz', 2.0)
        self.declare_parameter('log_dir', str(Path.home() / 'nav_zone_logs'))

        topic = str(self.get_parameter('nav_zone_topic').value)
        target = str(self.get_parameter('target_node').value)
        poll_hz = float(self.get_parameter('poll_hz').value)
        log_dir = Path(str(self.get_parameter('log_dir').value))
        log_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_path = log_dir / f'nav_zone_monitor_{stamp}.csv'
        self.csv_file = self.csv_path.open('w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(
            self.csv_file,
            fieldnames=[
                'wall_time',
                'cmd_zone',
                'inferred_zone',
                'match',
                'maintain_yaw_scale',
                'rotate_to_path_scale',
                'path_align_scale',
                'transition',
            ],
        )
        self.csv_writer.writeheader()
        self.csv_file.flush()

        self.cmd_zone = 'NONE'
        self.prev_cmd_zone = 'NONE'
        self.prev_inferred = 'unknown'
        self._poll_busy = False

        self._get_cli = self.create_client(
            GetParameters, f'/{target}/get_parameters')
        self.create_subscription(String, topic, self._on_zone, LATCHED_QOS)
        period = 1.0 / max(poll_hz, 0.2)
        self.create_timer(period, self._poll_params)

        self.get_logger().info(
            '============================================================\n'
            '  NavZoneMonitor\n'
            f'  cmd topic : {topic} (TRANSIENT_LOCAL)\n'
            f'  poll      : /{target} keys MaintainYaw / RotateToPath\n'
            f'  csv       : {self.csv_path}\n'
            '  Tip: mp=0 starts as MIDDLE (no edge→middle).\n'
            '       mp=1/2 start EDGE, then EDGE→MIDDLE near goal.\n'
            '============================================================'
        )

    def _on_zone(self, msg: String) -> None:
        new_zone = msg.data.strip() or 'EMPTY'
        if new_zone == self.cmd_zone:
            return
        old = self.cmd_zone
        self.cmd_zone = new_zone
        banner = f'***** CMD ZONE: {old} → {new_zone} *****'
        self.get_logger().warn(banner)
        # Immediate param probe after command.
        self._poll_params(force_transition=f'cmd:{old}->{new_zone}')

    def _poll_params(self, force_transition: str | None = None) -> None:
        if self._poll_busy:
            return
        if not self._get_cli.service_is_ready():
            return

        self._poll_busy = True
        req = GetParameters.Request(
            names=[KEY_MAINTAIN, KEY_ROTATE, KEY_PATH_ALIGN])
        fut = self._get_cli.call_async(req)

        def _done(f, transition=force_transition):
            self._poll_busy = False
            try:
                resp = f.result()
            except Exception as e:
                self.get_logger().warning(f'get_parameters failed: {e}')
                return
            if not resp.values or len(resp.values) < 2:
                return

            maintain = float(resp.values[0].double_value)
            rotate = float(resp.values[1].double_value)
            path_align = (
                float(resp.values[2].double_value)
                if len(resp.values) > 2 else float('nan')
            )
            inferred = infer_zone(maintain, rotate)
            match = (
                'YES'
                if (
                    (self.cmd_zone == 'middle' and inferred == 'middle')
                    or (self.cmd_zone == 'edge' and inferred == 'edge')
                    or (self.cmd_zone == 'straight' and inferred.startswith('straight'))
                )
                else 'NO'
            )

            trans = transition or ''
            if inferred != self.prev_inferred:
                trans = (
                    f'inferred:{self.prev_inferred}->{inferred}'
                    if not trans
                    else f'{trans}|inferred:{self.prev_inferred}->{inferred}'
                )
                self.get_logger().warn(
                    f'***** PARAM ZONE: {self.prev_inferred} → {inferred} '
                    f'(MaintainYaw={maintain:.1f}, RotateToPath={rotate:.1f}) *****'
                )
                self.prev_inferred = inferred

            # Loud mismatch: topic says middle but critics still look like edge.
            if self.cmd_zone == 'middle' and inferred == 'edge':
                self.get_logger().error(
                    'MISMATCH: cmd=middle but store looks like EDGE '
                    f'(MaintainYaw={maintain:.1f}, RotateToPath={rotate:.1f}). '
                    'Params may not be applied to critic memory.'
                )
            if self.cmd_zone == 'edge' and inferred == 'middle':
                self.get_logger().error(
                    'MISMATCH: cmd=edge but store looks like MIDDLE '
                    f'(MaintainYaw={maintain:.1f}, RotateToPath={rotate:.1f})'
                )

            row = {
                'wall_time': datetime.now().isoformat(timespec='milliseconds'),
                'cmd_zone': self.cmd_zone,
                'inferred_zone': inferred,
                'match': match,
                'maintain_yaw_scale': f'{maintain:.3f}',
                'rotate_to_path_scale': f'{rotate:.3f}',
                'path_align_scale': f'{path_align:.3f}',
                'transition': trans,
            }
            self.csv_writer.writerow(row)
            self.csv_file.flush()

            # Compact periodic line (only when something interesting / every poll ok)
            if trans or match == 'NO':
                self.get_logger().info(
                    f'cmd={self.cmd_zone:8s} inferred={inferred:16s} match={match} '
                    f'MaintainYaw={maintain:7.1f} RotateToPath={rotate:6.1f}'
                )

        fut.add_done_callback(_done)

    def destroy_node(self) -> bool:
        try:
            self.csv_file.close()
        except Exception:
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NavZoneMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(f'CSV saved: {node.csv_path}')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
