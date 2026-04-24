#!/usr/bin/env python3
"""Static TF broadcaster: publish a fixed transform from parent (odom) to child (base).

Reads parameters (defaults):
  - odom_frame_id (parent) default: "odom"
  - base_frame_id (child) default: "base"
  - translation: x,y,z (defaults 0.0)
  - rotation_rpy: roll,pitch,yaw (defaults 0.0)

The transform is by default identity (coincident frames).
"""
import math
import rclpy
import sys
try:
    import yaml
except Exception:
    yaml = None
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
import tf2_ros


def euler_to_quaternion(roll, pitch, yaw):
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return x, y, z, w


class StaticTFNode(Node):
    def __init__(self, initial_transforms=None):
        super().__init__('static_tf_broadcaster')

        # Try both publish.* and top-level names for compatibility
        self.declare_parameter('odom_frame_id', 'aft_mapped')
        self.declare_parameter('base_frame_id', 'base')
        self.declare_parameter('translation.x', 0.0)
        self.declare_parameter('translation.y', 0.0)
        self.declare_parameter('translation.z', 0.0)
        self.declare_parameter('rotation.roll', 0.0)
        self.declare_parameter('rotation.pitch', 0.0)
        self.declare_parameter('rotation.yaw', 0.0)
        # also accept publish.* style
        self.declare_parameter('publish.initial_frame_id', '')
        self.declare_parameter('publish.odom_frame_id', '')

        # Backwards-compatible single transform parameters
        odom = self.get_parameter('odom_frame_id').get_parameter_value().string_value
        base = self.get_parameter('base_frame_id').get_parameter_value().string_value

        pub_initial = self.get_parameter('publish.initial_frame_id').get_parameter_value().string_value
        pub_odom = self.get_parameter('publish.odom_frame_id').get_parameter_value().string_value
        if pub_initial:
            odom = pub_initial
        if pub_odom:
            base = pub_odom

        tx = float(self.get_parameter('translation.x').get_parameter_value().double_value)
        ty = float(self.get_parameter('translation.y').get_parameter_value().double_value)
        tz = float(self.get_parameter('translation.z').get_parameter_value().double_value)
        roll = float(self.get_parameter('rotation.roll').get_parameter_value().double_value)
        pitch = float(self.get_parameter('rotation.pitch').get_parameter_value().double_value)
        yaw = float(self.get_parameter('rotation.yaw').get_parameter_value().double_value)

        # New: support a parameter `transforms` as a list of dicts for multiple static transforms
        # Example element: {odom_frame_id: 'odom', base_frame_id: 'base', translation: {x:0,y:0,z:0}, rotation_rpy: [0,0,0]}
        self.declare_parameter('transforms', [])
        transforms_to_send = []

        try:
            pv = self.get_parameter('transforms').get_parameter_value()
            transforms_param = getattr(pv, '_value', None)
            self.get_logger().info(f'Raw transforms parameter value: {transforms_param} (type: {type(transforms_param)})')
        except Exception as e:
            transforms_param = []
            self.get_logger().warn(f'Could not read transforms parameter: {e}')

        # If not provided via ROS params, accept initial_transforms passed from main
        if (transforms_param is None or transforms_param == []) and initial_transforms:
            transforms_param = initial_transforms
            self.get_logger().info(f'Using transforms loaded from params-file: {transforms_param}')

        # Accept either a list of transform dicts or a dict mapping keys->transform dict
        if isinstance(transforms_param, dict):
            transforms_list = list(transforms_param.values())
        else:
            transforms_list = transforms_param or []

        for item in transforms_list:
            try:
                parent = item.get('odom_frame_id', item.get('parent', ''))
                child = item.get('base_frame_id', item.get('child', ''))
                if not parent or not child:
                    continue
                tx_i = float(item.get('translation', {}).get('x', 0.0))
                ty_i = float(item.get('translation', {}).get('y', 0.0))
                tz_i = float(item.get('translation', {}).get('z', 0.0))
                rpy = item.get('rotation_rpy', item.get('rotation', [0.0, 0.0, 0.0]))
                if isinstance(rpy, dict):
                    roll_i = float(rpy.get('roll', 0.0))
                    pitch_i = float(rpy.get('pitch', 0.0))
                    yaw_i = float(rpy.get('yaw', 0.0))
                else:
                    roll_i, pitch_i, yaw_i = (float(v) for v in rpy)

                qx, qy, qz, qw = euler_to_quaternion(roll_i, pitch_i, yaw_i)

                t_i = TransformStamped()
                t_i.header.stamp = self.get_clock().now().to_msg()
                t_i.header.frame_id = parent
                t_i.child_frame_id = child
                t_i.transform.translation.x = tx_i
                t_i.transform.translation.y = ty_i
                t_i.transform.translation.z = tz_i
                t_i.transform.rotation.x = qx
                t_i.transform.rotation.y = qy
                t_i.transform.rotation.z = qz
                t_i.transform.rotation.w = qw

                transforms_to_send.append(t_i)
                self.get_logger().info(f'Queued static transform {parent} -> {child} : trans=({tx_i},{ty_i},{tz_i}) rpy=({roll_i},{pitch_i},{yaw_i})')
            except Exception as e:
                self.get_logger().warn(f'Invalid transform entry in parameters: {e}')

        # If no list provided, fall back to the original single-transform behavior
        if not transforms_to_send:
            x, y, z, w = euler_to_quaternion(roll, pitch, yaw)

            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = odom
            t.child_frame_id = base
            t.transform.translation.x = tx
            t.transform.translation.y = ty
            t.transform.translation.z = tz
            t.transform.rotation.x = x
            t.transform.rotation.y = y
            t.transform.rotation.z = z
            t.transform.rotation.w = w

            transforms_to_send.append(t)
            self.get_logger().info(f'Publishing static transform {odom} -> {base} : trans=({tx},{ty},{tz}) rpy=({roll},{pitch},{yaw})')

        broadcaster = tf2_ros.StaticTransformBroadcaster(self)
        self.get_logger().info(f'Sending {len(transforms_to_send)} static transform(s)')
        for tt in transforms_to_send:
            try:
                self.get_logger().info(f"  queued: {tt.header.frame_id} -> {tt.child_frame_id}")
            except Exception:
                pass
        broadcaster.sendTransform(transforms_to_send)


def main(args=None):
    # Try to manually load transforms from a params file passed on the command line
    initial_transforms = None
    try:
        if yaml is not None:
            # find --params-file in sys.argv
            argv = sys.argv[1:]
            if '--params-file' in argv:
                idx = argv.index('--params-file')
                if idx + 1 < len(argv):
                    pf = argv[idx + 1]
                    try:
                        with open(pf, 'r') as fh:
                            data = yaml.safe_load(fh)
                        node_section = data.get('static_tf_broadcaster', {}) if isinstance(data, dict) else {}
                        ros_params = node_section.get('ros__parameters', {}) if isinstance(node_section, dict) else {}
                        transforms = ros_params.get('transforms', None)
                        if transforms is not None:
                            # if mapping, take values
                            if isinstance(transforms, dict):
                                initial_transforms = list(transforms.values())
                            else:
                                initial_transforms = transforms
                    except Exception as e:
                        print(f'Warning: failed to load params-file {pf}: {e}')
    except Exception as e:
        print(f'Warning: parameter-load exception: {e}')
    rclpy.init(args=args)
    node = StaticTFNode(initial_transforms=initial_transforms)
    try:
        # keep alive to ensure transform stays available
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
