#include "kfs_detection_nav/kfs_manager.hpp"

KfsManager::KfsManager() : Node("kfs_manager")
{
    RCLCPP_INFO(this->get_logger(), "KFS Detection & Nav Manager started.");
    timer_ = this->create_wall_timer(std::chrono::seconds(1),
        std::bind(&KfsManager::timer_callback, this));
    yolo_subscription_ = this->create_subscription<yolov8_ros2_msgs::msg::BoundingBoxes>(
        "/yolo_simulator/detections",  // 接收yolo话题名称
        10,  // 队列大小
        std::bind(&KfsManager::yolo_callback, this, std::placeholders::_1)  // 回调函数
    );

    odometry_subscription_ = this->create_subscription<nav_msgs::msg::Odometry>(
        "/state_estimation", 10,
        std::bind(&KfsManager::odometry_callback, this, std::placeholders::_1));
  
  // ===== 新增：地形点云订阅 =====
    terrain_subscription_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
        "/terrain_map_ext", 10,
        std::bind(&KfsManager::terrain_callback, this, std::placeholders::_1));
  
  // ===== 新增：TF初始化 =====
  // 这两行必须成对出现，顺序重要！
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
  

    decision_publisher_ = this->create_publisher<yolov8_ros2_msgs::msg::KFSDecision>(
        "/kfs_decision",  // 发布话题名称
        10                // 队列大小
    );
}

// void KfsManager::timer_callback()
// {
//     RCLCPP_INFO(this->get_logger(), "KFS Manager running...");
// }

bool KfsManager::is_high_confidence(double probability) const
{
    return probability >= PROBABILITY_THRESHOLD;
}

bool KfsManager::is_real_kfs(const std::string& class_name) const
{
    return class_name == "r1" || class_name == "r2";
}

bool KfsManager::is_fake_kfs(const std::string& class_name) const
{
    return class_name == "f_kfs";
}

void KfsManager::timer_callback()
{
    // 【第1步】检查数据
    if (latest_detections_.bounding_boxes.empty()) 
    {
        RCLCPP_WARN(this->get_logger(), "No detections received yet.");
    }

    // 【第2步】清空上一次的列表
    real_kfs_list_.clear();
    fake_kfs_list_.clear();

    // 【第3步】遍历并分离真假KFS
    for (const auto& bbox : latest_detections_.bounding_boxes) {
        // 过滤低置信度
        if (!is_high_confidence(bbox.probability)) {
            continue;  // 跳过这个检测
        }
        
        // 分类
        if (is_real_kfs(bbox.class_name)) {
            real_kfs_list_.push_back(bbox);
        } else if (is_fake_kfs(bbox.class_name)) {
            fake_kfs_list_.push_back(bbox);
        }
    }

        // 【第4步】创建决策消息
    auto decision = yolov8_ros2_msgs::msg::KFSDecision();
    decision.timestamp = this->now();  // 时间戳
    decision.frame_id = "camera";

    // 【第5步】设置目标信息
    // 【第5步】设置所有可抓取的真KFS目标信息
    if (!real_kfs_list_.empty()) {
    // 第一步：按距离排序所有真KFS（从近到远）
    std::sort(
        real_kfs_list_.begin(),
        real_kfs_list_.end(),
        [](const auto& a, const auto& b) {
            return a.distance < b.distance;
        }
        );
    
    // 第二步：填充所有真KFS的信息到数组
    decision.real_kfs_available = true;
    decision.real_kfs_count = real_kfs_list_.size();
    decision.primary_target_index = 0;  // 第一个（最近的）是首选
    
    for (const auto& kfs : real_kfs_list_) {
        decision.real_kfs_class_names.push_back(kfs.class_name);
        decision.real_kfs_distances.push_back(kfs.distance);
        decision.real_kfs_confidences.push_back(kfs.probability);
        decision.real_kfs_colors.push_back(kfs.color);
        decision.real_kfs_bbox_xmin.push_back(kfs.xmin);
        decision.real_kfs_bbox_ymin.push_back(kfs.ymin);
        decision.real_kfs_bbox_xmax.push_back(kfs.xmax);
        decision.real_kfs_bbox_ymax.push_back(kfs.ymax);
    }
    } else {
        decision.real_kfs_available = false;
        decision.real_kfs_count = 0;
    }
    
    // 【第6步】设置假KFS危险区信息
    decision.fake_kfs_count = fake_kfs_list_.size();
    
    if (!fake_kfs_list_.empty()) {
        // 找最近的假KFS
        double closest_distance = fake_kfs_list_[0].distance;
        for (const auto& fake : fake_kfs_list_) {
            decision.fake_kfs_distances.push_back(fake.distance);
            decision.fake_kfs_confidences.push_back(fake.probability);
            decision.fake_kfs_colors.push_back(fake.color);
            
            if (fake.distance < closest_distance) {
                closest_distance = fake.distance;
            }
        }
        decision.closest_fake_kfs_distance = closest_distance;
    } else {
        decision.closest_fake_kfs_distance = -1.0;  // 无效值
    }
    
    // // 【第7步】评估安全状态
    // if (fake_kfs_list_.empty()) {
    //     decision.safety_status = "SAFE";
    // } else if (decision.closest_fake_kfs_distance < CRITICAL_DANGER_RADIUS) {
    //     decision.safety_status = "DANGER";
    // } else if (decision.closest_fake_kfs_distance < DANGER_ZONE_RADIUS) {
    //     decision.safety_status = "WARNING";
    // } else {
    //     decision.safety_status = "SAFE";
    // }
    
    // 【第8步】评估优先级
    // if (!decision.real_kfs_available) {
    //     decision.priority_level = "WAIT";
    // } else if (decision.safety_status == "SAFE") {
    //     decision.priority_level = "HIGH";
    // } else if (decision.safety_status == "WARNING") {
    //     decision.priority_level = "MEDIUM";
    // } else {
    //     decision.priority_level = "LOW";
    // }    

    decision_publisher_->publish(decision);

    RCLCPP_INFO(this->get_logger(), 
        "Published KFS : Real KFS=%s, Count=%u, Fake KFS Count=%u, Closest Fake Distance=%.2f m",
        decision.real_kfs_available ? "Yes" : "No",
        decision.real_kfs_count,
        decision.fake_kfs_count,
        decision.closest_fake_kfs_distance);

}

void KfsManager::yolo_callback(const yolov8_ros2_msgs::msg::BoundingBoxes::SharedPtr msg)
{
    // 保存最新的检测数据
    latest_detections_ = *msg;
    
    RCLCPP_DEBUG(this->get_logger(), "Received %lu detections", msg->bounding_boxes.size());

    // 打印接收到的检测数据
    // RCLCPP_INFO(this->get_logger(), "Received %zu detections", msg->bounding_boxes.size());
    
    // // 遍历所有检测框
    // for (const auto& bbox : msg->bounding_boxes) {
    //     RCLCPP_INFO(this->get_logger(), 
    //         "Detection: class=%s, color=%s, distance=%.2f m",
    //         bbox.class_name.c_str(), bbox.color.c_str(), bbox.distance);
    // }
}



int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<KfsManager>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
