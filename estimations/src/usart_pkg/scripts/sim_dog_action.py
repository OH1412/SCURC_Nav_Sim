import rclpy
from rclpy.node import Node

# 导入你的自定义消息类型
from usart_pkg.msg import Action

class DogActionSimulator(Node):
    def __init__(self):
        super().__init__('dog_action_simulator')
        # 创建发布者，对应你 C++ 节点中订阅的话题
        self.publisher_ = self.create_publisher(Action, '/dog_step_cmd', 10)
        
        # 每 2 秒发送一次指令
        self.timer = self.create_timer(2.0, self.timer_callback)
        
        # 定义一个测试序列，包含: (动作常数, 速度常数, 描述文本)
        self.test_sequence = [
            (Action.ACTION_STAND, Action.SPEED_LOW, "站立 (低速)"),
            (Action.ACTION_FORWARD, Action.SPEED_MEDIUM, "前进 (中速)"),
            (Action.ACTION_BACKWARD, Action.SPEED_MEDIUM, "后退 (中速)"),
            (Action.ACTION_TURN_LEFT, Action.SPEED_HIGH, "左转 (高速)"),
            (Action.ACTION_TURN_RIGHT, Action.SPEED_HIGH, "右转 (高速)"),
        ]
        self.step_index = 0

    def timer_callback(self):
        # 实例化消息对象
        msg = Action()
        
        # 获取当前轮到的测试指令
        current_action, current_speed, description = self.test_sequence[self.step_index]
        
        # 赋值给消息字段
        msg.action_id = current_action
        msg.speed_level = current_speed
        
        # 发布消息
        self.publisher_.publish(msg)
        
        # 打印日志方便在终端观察
        self.get_logger().info(
            f'发布指令: {description} --> 发送数据 [action_id: {msg.action_id}, speed_level: {msg.speed_level}]'
        )
        
        # 索引递增，实现循环测试
        self.step_index = (self.step_index + 1) % len(self.test_sequence)

def main(args=None):
    rclpy.init(args=args)
    node = DogActionSimulator()
    
    try:
        node.get_logger().info('动作模拟器已启动，按 Ctrl+C 退出...') # 这里改成了 node.get_logger()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()