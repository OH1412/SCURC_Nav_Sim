import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
import time

rclpy.init()
node = Node('test_status_pub')
pub = node.create_publisher(Bool, '/dog_status/is_stepping', 10)

msg = Bool()
last_false_time = time.time()

print("开始测试：大部分时间 true，每 2 秒一次 false")

try:
    while rclpy.ok():
        current_time = time.time()
        
        # 如果距离上次发 false 已经超过了 2 秒
        if current_time - last_false_time >= 2.0:
            msg.data = True
            pub.publish(msg)
            print("==== 发送 FALSE ====")
            last_false_time = current_time
        else:
            msg.data = True
            pub.publish(msg)
            
        # 精准睡眠 0.1 秒
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    node.destroy_node()
    rclpy.shutdown()