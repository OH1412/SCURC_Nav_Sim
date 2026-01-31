#include "rclcpp/rclcpp.hpp"                    // ROS 2 核心库
#include "yolov8_ros2_msgs/msg/bounding_box.hpp"      // 单个检测框
#include "yolov8_ros2_msgs/msg/bounding_boxes.hpp"    // 检测框集合
#include <chrono>                               // 时间库
#include <vector>                               // 向量库


class YoloSimulator : public rclcpp::Node  // 继承 Node 类
{
public:
    YoloSimulator() : Node("yolo_simulator_node")  // 构造函数
    {
        // 1. 创建发布者（向 /yolo_simulator/detections 发送数据）
        publisher_ = this->create_publisher<yolov8_ros2_msgs::msg::BoundingBoxes>(
            "/yolo_simulator/detections", 10);
        
        // 2. 创建定时器（每 1 秒执行一次 timer_callback）
        timer_ = this->create_wall_timer(
            std::chrono::seconds(3), std::bind(&YoloSimulator::timer_callback, this));
    }

private:
    // timer_callback()：每 1 秒自动执行
    void timer_callback()
    {
        auto msg = generate_mock_data();  // 生成虚拟数据
        publisher_->publish(msg);          // 发布数据
    }
    
    // generate_mock_data()：创建虚拟 KFS 数据
    yolov8_ros2_msgs::msg::BoundingBoxes generate_mock_data()
    {
        // 创建消息
        yolov8_ros2_msgs::msg::BoundingBoxes msg;
        
        // 设置时间戳
        msg.header.stamp = this->now();
        msg.header.frame_id = "camera";
        
        // 添加虚拟检测 1：r1（真 KFS），红色，1.5 米
        yolov8_ros2_msgs::msg::BoundingBox bbox1;
        bbox1.xmin = 50.0;
        bbox1.ymin = 30.0;
        bbox1.xmax = 150.0;
        bbox1.ymax = 130.0;
        bbox1.class_name = "r1";
        bbox1.color = "red";
        bbox1.probability = 0.95;
        bbox1.distance = 1.5;
        msg.bounding_boxes.push_back(bbox1);  // 加入数组
        
        // 添加虚拟检测 2：f_kfs（假 KFS），蓝色，2.5 米
        yolov8_ros2_msgs::msg::BoundingBox bbox2;
        bbox2.xmin = 200.0;
        bbox2.ymin = 100.0;
        bbox2.xmax = 300.0;
        bbox2.ymax = 200.0;
        bbox2.class_name = "f_kfs";
        bbox2.color = "blue";
        bbox2.probability = 0.88;
        bbox2.distance = 2.5;
        msg.bounding_boxes.push_back(bbox2);
        
        // 添加虚拟检测 3：r2（真 KFS），红色，3.0 米
        yolov8_ros2_msgs::msg::BoundingBox bbox3;
        bbox3.xmin = 350.0;
        bbox3.ymin = 150.0;
        bbox3.xmax = 450.0;
        bbox3.ymax = 250.0;
        bbox3.class_name = "r2";
        bbox3.color = "red";
        bbox3.probability = 0.92;
        bbox3.distance = 3.0;
        msg.bounding_boxes.push_back(bbox3);
        
        return msg;  // 返回完整消息
    }
    
    // 成员变量
    rclcpp::Publisher<yolov8_ros2_msgs::msg::BoundingBoxes>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};

// main() 函数：程序入口
int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);                           // 初始化 ROS 2
    rclcpp::spin(std::make_shared<YoloSimulator>());    // 启动节点，持续运行
    rclcpp::shutdown();                                  // 关闭 ROS 2
    return 0;
}