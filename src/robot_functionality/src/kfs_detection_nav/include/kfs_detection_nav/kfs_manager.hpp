#ifndef KFS_MANAGER_HPP_
#define KFS_MANAGER_HPP_
#include "yolov8_ros2_msgs/msg/bounding_boxes.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "yolov8_ros2_msgs/msg/kfs_decision.hpp"

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
    void yolo_callback(const yolov8_ros2_msgs::msg::BoundingBoxes::SharedPtr msg);
    rclcpp::Subscription<yolov8_ros2_msgs::msg::BoundingBoxes>::SharedPtr yolo_subscription_;
    yolov8_ros2_msgs::msg::BoundingBoxes latest_detections_;

    rclcpp::Publisher<yolov8_ros2_msgs::msg::KFSDecision>::SharedPtr decision_publisher_;
    
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> real_kfs_list_;
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> fake_kfs_list_;

    rclcpp::TimerBase::SharedPtr timer_;
};

#endif
