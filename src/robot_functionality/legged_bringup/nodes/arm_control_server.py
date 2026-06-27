#!/usr/bin/env python3
# ============================================================================
# 机械臂控制 Action Server
# ============================================================================
# 接收 map 坐标系下的目标坐标，通过 tf2 变换到 base_link 坐标系，
# 然后将 base_link 坐标发送给机械臂执行抓取任务。
#
# 用法:
#   1) 通过 launch 文件启动 (推荐)
#   2) 直接运行:
#      ros2 run legged_bringup arm_control_server.py
#
# Action 接口:
#   behavior_ext_plugins/action/ArmControl
#     goal:  target_pose (PoseStamped, map 坐标系)
#     result: success, base_link_pose (PoseStamped, base_link 坐标系), message
#     feedback: status (string)
#
# 行为树集成:
#   在 navigate_waypoints_with_task.xml 中使用 <ArmControl .../> 节点，
#   该节点自动调用本 Action Server。
# ============================================================================

import math
import sys

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import PoseStamped, Point, Quaternion
from std_msgs.msg import Float64MultiArray

# 导入自定义 Action 类型
# behavior_ext_plugins 包会生成 Python 接口
from behavior_ext_plugins.action import ArmControl

from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_pose


class ArmControlServer(Node):
    """机械臂控制 Action Server — map→base_link 坐标变换 + 抓取任务"""

    def __init__(self):
        super().__init__('arm_control_server')

        # ================================================================
        # 参数声明
        # ================================================================
        self.declare_parameter('arm_timeout', 30.0)        # 机械臂超时 (秒)
        self.declare_parameter('base_link_frame', 'base_link')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('enable_serial_publish', True)
        self.declare_parameter('arm_command_topic', '/arm_command')
        self.declare_parameter('arm_target_topic', '/arm_target')

        self.arm_timeout = self.get_parameter('arm_timeout').value
        self.base_link_frame = self.get_parameter('base_link_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.enable_serial_publish = self.get_parameter('enable_serial_publish').value
        self.arm_command_topic = self.get_parameter('arm_command_topic').value
        self.arm_target_topic = self.get_parameter('arm_target_topic').value

        # ================================================================
        # tf2 初始化 — 用于 map → base_link 坐标变换
        # ================================================================
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ================================================================
        # 机械臂指令发布者 — 发送 base_link 坐标到串口驱动
        #   /arm_target:   geometry_msgs/Point (协议标准话题)
        #   /arm_command:  Float64MultiArray [兼容话题, 格式: x,y,z,yaw,action]
        # ================================================================
        if self.enable_serial_publish:
            self.arm_target_pub = self.create_publisher(
                Point, self.arm_target_topic, 10)
            self.arm_cmd_pub = self.create_publisher(
                Float64MultiArray, self.arm_command_topic, 10)
            self.get_logger().info(
                f'Arm targets will be published to: {self.arm_target_topic} (Point) '
                f'and {self.arm_command_topic} (Float64MultiArray)')
        else:
            self.arm_target_pub = None
            self.arm_cmd_pub = None

        # ================================================================
        # Action Server
        # ================================================================
        self._action_server = ActionServer(
            self,
            ArmControl,
            'arm_control',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=ReentrantCallbackGroup(),
        )

        self.get_logger().info('ArmControlServer started. Waiting for arm control goals...')

    # ------------------------------------------------------------------
    # Action 回调
    # ------------------------------------------------------------------

    def goal_callback(self, goal_request):
        """目标到达时的回调 — 验证目标合法性"""
        target = goal_request.target_pose

        if target.header.frame_id and target.header.frame_id != self.map_frame:
            self.get_logger().warn(
                f'Goal frame_id is "{target.header.frame_id}", '
                f'expected "{self.map_frame}". Will still attempt transform.')

        self.get_logger().info(
            f'Received arm control goal: '
            f'map_frame target=(x={target.pose.position.x:.3f}, '
            f'y={target.pose.position.y:.3f}, z={target.pose.position.z:.3f})')

        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """取消回调"""
        self.get_logger().warn('Arm control goal cancelled.')
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        """执行机械臂控制任务的主逻辑"""
        target_pose = goal_handle.request.target_pose

        # 确保 frame_id 正确
        if not target_pose.header.frame_id:
            target_pose.header.frame_id = self.map_frame

        # 发布反馈
        self._publish_feedback(goal_handle, 'Transforming map → base_link...')

        # ---------------------------------------------------------------
        # Step 1: 坐标变换 — map → base_link
        # ---------------------------------------------------------------
        try:
            # lookup_transform(target_frame, source_frame, time, timeout)
            # 我们要把 map 坐标变到 base_link，所以查 base_link→map 的 TF
            when = rclpy.time.Time()  # 最新 TF
            transform = self.tf_buffer.lookup_transform(
                self.base_link_frame,    # target_frame
                self.map_frame,          # source_frame
                when,
                timeout=rclpy.duration.Duration(seconds=1.0),
            )

            # 将 map 坐标变换到 base_link 坐标
            base_link_pose = do_transform_pose(target_pose.pose, transform)
            base_link_stamped = PoseStamped()
            base_link_stamped.header.frame_id = self.base_link_frame
            base_link_stamped.header.stamp = self.get_clock().now().to_msg()
            base_link_stamped.pose = base_link_pose

            self.get_logger().info(
                f'Transform OK: map({target_pose.pose.position.x:.3f}, '
                f'{target_pose.pose.position.y:.3f}, '
                f'{target_pose.pose.position.z:.3f}) '
                f'→ base_link({base_link_pose.position.x:.3f}, '
                f'{base_link_pose.position.y:.3f}, '
                f'{base_link_pose.position.z:.3f})')

            # -----------------------------------------------------------
            # Step 1.5: base_link → arm_base 坐标变换 (绕 Z 轴 180°)
            #   机械臂基座与机器人 base_link 之间存在绕 Z 轴 180° 的安装偏差:
            #     arm_x = -base_link_x
            #     arm_y = -base_link_y
            #     arm_z =  base_link_z
            # -----------------------------------------------------------
            arm_pose = base_link_pose
            arm_pose.position.x = -base_link_pose.position.x
            arm_pose.position.y = -base_link_pose.position.y
            # z 保持不变

            self.get_logger().info(
                f'Arm transform: base_link({base_link_pose.position.x:.3f}, '
                f'{base_link_pose.position.y:.3f}, '
                f'{base_link_pose.position.z:.3f}) '
                f'→ arm_base({arm_pose.position.x:.3f}, '
                f'{arm_pose.position.y:.3f}, '
                f'{arm_pose.position.z:.3f}) [Z-180°]')

        except TransformException as e:
            self.get_logger().error(f'TF transform failed: {e}')
            goal_handle.abort()
            result = ArmControl.Result()
            result.success = False
            result.base_link_pose = PoseStamped()
            result.message = f'TF transform failed: {e}'
            return result

        # ---------------------------------------------------------------
        # Step 2: 发送机械臂指令 (通过串口话题)
        # ---------------------------------------------------------------
        self._publish_feedback(goal_handle, 'Sending arm command...')

        arm_result_msg = ''
        arm_success = True

        if self.enable_serial_publish and self.arm_cmd_pub is not None:
            try:
                # 将 arm_base 坐标打包为 Float64MultiArray (兼容格式)
                # 格式: [x, y, z, yaw, arm_action]
                yaw = self._quat_to_yaw(base_link_pose.orientation)
                arm_action = 1  # 默认抓取
                msg = Float64MultiArray()
                msg.data = [
                    float(arm_pose.position.x),
                    float(arm_pose.position.y),
                    float(arm_pose.position.z),
                    float(yaw),
                    float(arm_action),
                ]

                self.arm_cmd_pub.publish(msg)
                self.get_logger().info(
                    f'Arm command sent to {self.arm_command_topic}: '
                    f'[x={msg.data[0]:.3f}, y={msg.data[1]:.3f}, '
                    f'z={msg.data[2]:.3f}, yaw={msg.data[3]:.3f}, '
                    f'action={int(msg.data[4])}]')

                # 同时发布 Point 消息到 /arm_target (协议标准话题, 单位: mm)
                if self.arm_target_pub is not None:
                    target_point = Point()
                    # 协议规定 /arm_target 的 Point 值单位为 mm，需要从米转换
                    target_point.x = float(arm_pose.position.x * 1000.0)
                    target_point.y = float(arm_pose.position.y * 1000.0)
                    target_point.z = float(arm_pose.position.z * 1000.0)
                    self.arm_target_pub.publish(target_point)
                    self.get_logger().info(
                        f'Arm target sent to {self.arm_target_topic}: '
                        f'(x={target_point.x:.1f}, y={target_point.y:.1f}, '
                        f'z={target_point.z:.1f}) mm')

                arm_result_msg = 'Arm command published successfully.'
                arm_success = True

            except Exception as e:
                self.get_logger().error(f'Failed to publish arm command: {e}')
                arm_result_msg = f'Failed to publish arm command: {e}'
                arm_success = False
        else:
            # 串口发布已禁用 — 仅做坐标变换演示
            self.get_logger().info(
                'Serial publish disabled. Transform-only mode.')
            arm_result_msg = 'Transform completed (arm command not sent).'
            arm_success = True

        # ---------------------------------------------------------------
        # Step 3: 等待机械臂完成 (占位 — 通过 topic 或其他机制)
        # ---------------------------------------------------------------
        self._publish_feedback(goal_handle, 'Waiting for arm completion...')

        # TODO: 订阅机械臂状态反馈 topic 并等待完成信号
        # 当前版本直接返回成功（后续可扩展为订阅 /arm_status 等待完成）
        # wait_until_complete(base_link_stamped, self.arm_timeout)

        # ---------------------------------------------------------------
        # Step 4: 返回结果
        # ---------------------------------------------------------------
        goal_handle.succeed()

        result = ArmControl.Result()
        result.success = arm_success
        result.base_link_pose = base_link_stamped
        result.message = arm_result_msg

        self.get_logger().info(
            f'Arm control task completed: success={arm_success}, '
            f'message="{arm_result_msg}"')

        return result

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _publish_feedback(self, goal_handle, status: str):
        """发布 action feedback"""
        feedback = ArmControl.Feedback()
        feedback.status = status
        goal_handle.publish_feedback(feedback)
        self.get_logger().debug(f'Feedback: {status}')

    @staticmethod
    def _quat_to_yaw(q: Quaternion) -> float:
        """四元数 → 偏航角 (rad)"""
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)


def main(args=None):
    rclpy.init(args=args)

    node = ArmControlServer()

    # 使用 MultiThreadedExecutor 以支持异步 action 和 tf2 回调同时运行
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
