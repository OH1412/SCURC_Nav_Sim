#ifndef KFS_MANAGER_HPP_
#define KFS_MANAGER_HPP_
#include "yolov8_ros2_msgs/msg/bounding_boxes.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "yolov8_ros2_msgs/msg/kfs_decision.hpp"

// ========== 新增头文件 ==========
#include "nav_msgs/msg/odometry.hpp"          // 里程计消息类型
#include "yolov8_ros2_msgs/msg/stair_match_result.hpp"  // 新增：台阶匹配结果消息
#include "tf2_ros/buffer.h"                   // TF缓冲区
#include "tf2_ros/transform_listener.h"       // TF监听器
#include "geometry_msgs/msg/point_stamped.hpp" // 坐标点消息
// ================================

class KfsManager : public rclcpp::Node
{
public:
    KfsManager();
       // ===== StairBoundary 结构体定义 =====
    struct StairBoundary {
        double x_min, x_max;
        double y_min, y_max;
        double z_min, z_max;
        int stair_id;
        const char* stair_name;

        // constexpr 构造函数定义（必须在定义处）
        StairBoundary(
            double x_min_, double x_max_,
            double y_min_, double y_max_,
            double z_min_, double z_max_,
            int id_, const char* name_
        ) : 
            x_min(x_min_), x_max(x_max_),
            y_min(y_min_), y_max(y_max_),
            z_min(z_min_), z_max(z_max_),
            stair_id(id_), stair_name(name_)
        {}
    };

    // ===== 台阶边界数组：仅声明（类内不初始化）=====
    static const std::array<StairBoundary, 12> STAIR_BOUNDARIES;
    
private:
    static constexpr double PROBABILITY_THRESHOLD = 0.80; //置信度阈值
    static constexpr double DANGER_ZONE_RADIUS = 0.2;
    static constexpr double CRITICAL_DANGER_RADIUS = 0.2;
        
    bool is_high_confidence(double probability) const;
    bool is_real_kfs(const std::string& class_name) const;
    bool is_fake_kfs(const std::string& class_name) const;

    int find_stair_id(double kfs_x, double kfs_y, double kfs_z) const;
    // 辅助函数：计算位置匹配置信度
    double compute_position_confidence(double kfs_x, double kfs_y, 
                                  const StairBoundary& stair) const;
    void timer_callback();
    void odometry_callback(const nav_msgs::msg::Odometry::SharedPtr msg);
    // void terrain_callback(const sensor_msgs::msg::PointCloud2::SharedPtr msg);
    void yolo_callback(const yolov8_ros2_msgs::msg::BoundingBoxes::SharedPtr msg);
    rclcpp::Subscription<yolov8_ros2_msgs::msg::BoundingBoxes>::SharedPtr yolo_subscription_;
    yolov8_ros2_msgs::msg::BoundingBoxes latest_detections_;

    rclcpp::Publisher<yolov8_ros2_msgs::msg::KFSDecision>::SharedPtr decision_publisher_;
    
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> real_kfs_list_;
    std::vector<yolov8_ros2_msgs::msg::BoundingBox> fake_kfs_list_;

    rclcpp::TimerBase::SharedPtr timer_;

    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odometry_subscription_;
    // rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr terrain_subscription_;
    rclcpp::Publisher<yolov8_ros2_msgs::msg::StairMatchResult>::SharedPtr stair_match_publisher_;
    // ===== 缓存数据变量 =====
    nav_msgs::msg::Odometry latest_odometry_;      // 缓存最新的里程计数据
    bool odometry_received_ = false;               // 标志：里程计是否至少来过一次

    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  
};

#endif
