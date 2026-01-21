#ifndef KFS_MANAGER_HPP_
#define KFS_MANAGER_HPP_
#include "yolov8_ros2_msgs/msg/bounding_boxes.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "yolov8_ros2_msgs/msg/kfs_decision.hpp"

<<<<<<< HEAD
=======
// ========== 新增头文件 ==========
#include "nav_msgs/msg/odometry.hpp"          // 里程计消息类型
#include "sensor_msgs/msg/point_cloud2.hpp"   // 点云消息类型
#include "tf2_ros/buffer.h"                   // TF缓冲区
#include "tf2_ros/transform_listener.h"       // TF监听器
#include "geometry_msgs/msg/point_stamped.hpp" // 坐标点消息
// ================================

>>>>>>> 54397099922242ec8ae745e171eebbe3b2b243ef
class KfsManager : public rclcpp::Node
{
public:
    KfsManager();
    
private:
    static constexpr double PROBABILITY_THRESHOLD = 0.80; //置信度阈值
    static constexpr double DANGER_ZONE_RADIUS = 0.2;
    static constexpr double CRITICAL_DANGER_RADIUS = 0.2;

    bool is_high_confidence(double probability) const;
    bool is_real_kfs(const std::string& class_name) const;
    bool is_fake_kfs(const std::string& class_name) const;


    void timer_callback();
<<<<<<< HEAD
=======
    void odometry_callback(const nav_msgs::msg::Odometry::SharedPtr msg);
    void terrain_callback(const sensor_msgs::msg::PointCloud2::SharedPtr msg);
>>>>>>> 54397099922242ec8ae745e171eebbe3b2b243ef
    void yolo_callback(const yolov8_ros2_msgs::msg::BoundingBoxes::SharedPtr msg);
    rclcpp::Subscription<yolov8_ros2_msgs::msg::BoundingBoxes>::SharedPtr yolo_subscription_;
    yolov8_ros2_msgs::msg::BoundingBoxes latest_detections_;

    rclcpp::Publisher<yolov8_ros2_msgs::msg::KFSDecision>::SharedPtr decision_publisher_;
    
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> real_kfs_list_;
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> fake_kfs_list_;

    rclcpp::TimerBase::SharedPtr timer_;
<<<<<<< HEAD
=======

    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odometry_subscription_;
    rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr terrain_subscription_;

    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  
>>>>>>> 54397099922242ec8ae745e171eebbe3b2b243ef
};

#endif
