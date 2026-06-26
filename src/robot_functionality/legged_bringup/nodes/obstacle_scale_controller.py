#!/usr/bin/env python3
"""
Obstacle-aware ObstacleFootprint.scale controller.

Monitors the local costmap and dynamically adjusts ObstacleFootprint.scale:
  - Footprint overlaps LETHAL obstacle → scale = 1.0 (push through)
  - Footprint clear                       → scale = 50.0 (normal avoidance)

Hysteresis: requires N consecutive clear readings before restoring normal scale,
preventing rapid oscillation.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue


# Costmap internal values (unsigned char):
#   FREE=0  LETHAL=254  INSCRIBED=253  NO_INFO=255
# The published OccupancyGrid copies raw unsigned char into int8 array,
# so values >= 128 wrap to negative. Convert back before comparing.
#   LETHAL (254u) → int8 -2
#   INSCRIBED (253u) → int8 -3
# Threshold: treat anything >= INSCRIBED (253u) as "fatal"
FATAL_THRESHOLD = 253  # unsigned char value

# Normal and push-through scale values
NORMAL_SCALE = 50.0
PUSH_THROUGH_SCALE = 1.0


def _make_param(name: str, value: float) -> Parameter:
    pv = ParameterValue(type=3, double_value=float(value))
    return Parameter(name=name, value=pv)


class ObstacleScaleController(Node):
    def __init__(self):
        super().__init__('obstacle_scale_controller')

        # Parameters
        self.declare_parameter('target_node', 'controller_server')
        self.declare_parameter('costmap_topic', '/local_costmap/costmap')
        self.declare_parameter('hysteresis_count', 5)
        self.declare_parameter('check_hz', 10.0)
        self.declare_parameter('normal_scale', 50.0)
        self.declare_parameter('push_through_scale', 0.01)

        self.target_node: str = self.get_parameter('target_node').value
        self.costmap_topic: str = self.get_parameter('costmap_topic').value
        self.hysteresis_count: int = self.get_parameter('hysteresis_count').value
        self.normal_scale: float = self.get_parameter('normal_scale').value
        self.push_through_scale: float = self.get_parameter('push_through_scale').value

        # State
        self.current_scale = self.normal_scale      # what is currently active
        self.clear_counter = 0                       # consecutive clear readings
        self.param_client = None

        # Footprint bounding box (meters from robot center)
        # From nav2_params.yaml: [[0.297,0.192],[0.297,-0.192],[-0.445,-0.192],[-0.445,0.192]]
        self.footprint_x_min = -0.445
        self.footprint_x_max = 0.297
        self.footprint_y_min = -0.192
        self.footprint_y_max = 0.192

        # SetParameters client
        srv_name = f'/{self.target_node}/set_parameters'
        self.param_client = self.create_client(SetParameters, srv_name)

        # Subscribe to local costmap
        self.costmap_sub = self.create_subscription(
            OccupancyGrid, self.costmap_topic, self.costmap_callback, 10)

        self.get_logger().info(
            '============================================================\n'
            f'  ObstacleScaleController\n'
            f'  Footprint: x=[{self.footprint_x_min}, {self.footprint_x_max}]\n'
            f'              y=[{self.footprint_y_min}, {self.footprint_y_max}]\n'
            f'  Normal scale: {self.normal_scale}\n'
            f'  Push-through scale: {self.push_through_scale}\n'
            f'  Hysteresis: {self.hysteresis_count} clean reads\n'
            f'  Target node: /{self.target_node}\n'
            '============================================================'
        )

    def costmap_callback(self, msg: OccupancyGrid):
        """Check if lethal obstacles overlap the robot's footprint."""
        resolution = msg.info.resolution
        width = msg.info.width
        height = msg.info.height

        # Local costmap is rolling-window centered on robot (odom frame).
        # Robot position in grid coords:
        robot_cx = width / 2.0
        robot_cy = height / 2.0

        # Footprint bounding box in grid cells
        x_min_cell = int(robot_cx + self.footprint_x_min / resolution)
        x_max_cell = int(robot_cx + self.footprint_x_max / resolution)
        y_min_cell = int(robot_cy + self.footprint_y_min / resolution)
        y_max_cell = int(robot_cy + self.footprint_y_max / resolution)

        # Clamp to grid bounds
        x_min_cell = max(0, x_min_cell)
        x_max_cell = min(width - 1, x_max_cell)
        y_min_cell = max(0, y_min_cell)
        y_max_cell = min(height - 1, y_max_cell)

        # Scan footprint area for lethal obstacles
        # OccupancyGrid data is int8; internal unsigned char 254/253 wraps
        # to -2/-3. Convert back to 0-255 range before comparing.
        lethal_found = False
        data = msg.data
        for y in range(y_min_cell, y_max_cell + 1):
            for x in range(x_min_cell, x_max_cell + 1):
                idx = y * width + x
                if idx < len(data):
                    cost_signed = data[idx]
                    # Convert int8 → unsigned char (0-255)
                    cost = cost_signed if cost_signed >= 0 else cost_signed + 256
                    if cost >= FATAL_THRESHOLD:
                        lethal_found = True
                        break
            if lethal_found:
                break

        if lethal_found:
            self.clear_counter = 0
            if self.current_scale != self.push_through_scale:
                self.get_logger().info(
                    f'⚠ LETHAL in footprint → setting scale to {self.push_through_scale}')
                self._set_scale(self.push_through_scale)
        else:
            self.clear_counter += 1
            if self.clear_counter >= self.hysteresis_count and \
               self.current_scale != self.normal_scale:
                self.get_logger().info(
                    f'✓ Footprint clear ({self.hysteresis_count}x) → restoring scale to {self.normal_scale}')
                self._set_scale(self.normal_scale)

    def _set_scale(self, scale: float):
        """Push FollowPath.ObstacleFootprint.scale to controller_server."""
        if not self.param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error('set_parameters service not available')
            return

        param = _make_param('FollowPath.ObstacleFootprint.scale', scale)
        req = SetParameters.Request(parameters=[param])
        try:
            future = self.param_client.call_async(req)
            future.add_done_callback(self._set_param_callback)
            self.current_scale = scale
        except Exception as e:
            self.get_logger().error(f'set_parameters call failed: {e}')

    def _set_param_callback(self, future):
        try:
            result = future.result()
            for res in result.results:
                if not res.successful:
                    self.get_logger().warning(f'Param set failed: {res.reason}')
        except Exception as e:
            self.get_logger().error(f'Async param set error: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleScaleController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
