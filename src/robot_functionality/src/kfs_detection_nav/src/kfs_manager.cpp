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
        "/state_estimation", 
        10,
        std::bind(&KfsManager::odometry_callback, this, std::placeholders::_1));
  
  // ===== 新增：地形点云订阅 =====
    // terrain_subscription_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
    //     "/terrain_map_ext", 10,
    //     std::bind(&KfsManager::terrain_callback, this, std::placeholders::_1));
  
  // ===== 新增：TF初始化 =====
  // 这两行必须成对出现，顺序重要！
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
  

    decision_publisher_ = this->create_publisher<yolov8_ros2_msgs::msg::KFSDecision>(
        "/kfs_decision",  // 发布话题名称
        10                // 队列大小
    );
    
    // ===== 新增：台阶匹配结果发布器 =====
    stair_match_publisher_ = this->create_publisher<yolov8_ros2_msgs::msg::StairMatchResult>(
        "/stair_match_result",  // 发布台阶匹配详细结果
        10
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
// 相对于Gazebo world的全局坐标 (相对于 /map frame)
// const std::array<KfsManager::StairBoundary, 12> KfsManager::STAIR_BOUNDARIES = {{
//     // ===== 台深绿台阶（区域1-4）=====
//     // 深绿色台阶，位于Y负方向，高度0-0.4m
//     // DAE本地坐标加上模型偏移 (-0.034398, 0.217882, 0)
//     // 得到全局地图坐标系中的坐标
//     {-6.034398, -4.534398, -5.782118, -4.782118, 0.0, 0.4, 1, "Stair_Deep_Green_1"},
//     {-4.534398, -3.034398, -5.782118, -4.782118, 0.0, 0.4, 2, "Stair_Deep_Green_2"},
//     {-3.034398, -1.534398, -5.782118, -4.782118, 0.0, 0.4, 3, "Stair_Deep_Green_3"},
//     {-1.534398, 0.0, -5.782118, -4.782118, 0.0, 0.4, 4, "Stair_Deep_Green_4"},
    
//     // ===== 台浅绿台阶（区域5-8）=====
//     // 浅绿色台阶，位于Y中间位置，高度0-0.4m
//     // DAE本地坐标加上模型偏移后的全局地图坐标
//     {-6.034398, -4.534398, -5.282118, -4.282118, 0.0, 0.4, 5, "Stair_Light_Green_5"},
//     {-4.534398, -3.034398, -5.282118, -4.282118, 0.0, 0.4, 6, "Stair_Light_Green_6"},
//     {-3.034398, -1.534398, -5.282118, -4.282118, 0.0, 0.4, 7, "Stair_Light_Green_7"},
//     {-1.534398, 0.0, -5.282118, -4.282118, 0.0, 0.4, 8, "Stair_Light_Green_8"},
    
//     // ===== 台浅黄台阶（区域9-12）=====
//     // 浅黄色台阶，位于Y最外侧负方向，高度0-0.4m
//     // DAE本地坐标加上模型偏移后的全局地图坐标
//     {-6.034398, -4.534398, -3.582118, -3.282118, 0.0, 0.4, 9, "Stair_Light_Yellow_9"},
//     {-4.534398, -3.034398, -3.582118, -3.282118, 0.0, 0.4, 10, "Stair_Light_Yellow_10"},
//     {-3.034398, -1.534398, -3.582118, -3.282118, 0.0, 0.4, 11, "Stair_Light_Yellow_11"},
//     {-1.534398, 0.0, -3.582118, -3.282118, 0.0, 0.4, 12, "Stair_Light_Yellow_12"},
// }};

void KfsManager::timer_callback()
{
    // 【第0步】检查是否收到所有必要的数据
    if (!odometry_received_) {
        RCLCPP_WARN(this->get_logger(), "Waiting for odometry data...");
        return;  // 等待数据，不继续执行
    }
    
    // 【第1步】检查YOLO检测数据
    if (latest_detections_.bounding_boxes.empty()) 
    {
        RCLCPP_DEBUG(this->get_logger(), "No detections received.");
        return;  // 没有检测就直接返回
    }
    
    // ===== 新增：提取机器人位置信息 =====
    double robot_x = latest_odometry_.pose.pose.position.x;
    double robot_y = latest_odometry_.pose.pose.position.y;
    double robot_z = latest_odometry_.pose.pose.position.z;
    
    // 提取四元数并转换为欧拉角
    auto quat = latest_odometry_.pose.pose.orientation;
    double roll, pitch, yaw;
    tf2::Quaternion q(quat.x, quat.y, quat.z, quat.w);
    tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);
    
    RCLCPP_DEBUG(this->get_logger(),
        "Robot Position: x=%.2f, y=%.2f, z=%.2f, yaw=%.2f",
        robot_x, robot_y, robot_z, yaw);

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

    // ===== 新增：为每个真KFS计算map坐标并匹配台阶 =====
    std::vector<int> stair_ids;  // 存储每个KFS匹配的台阶ID
    std::vector<double> kfs_map_x_list;
    std::vector<double> kfs_map_y_list;
    std::vector<double> kfs_map_z_list;
    
    for (const auto& kfs : real_kfs_list_) {
        // 简化的坐标变换：从相机坐标到map坐标
        double kfs_map_x = robot_x + kfs.distance * cos(yaw);
        double kfs_map_y = robot_y + kfs.distance * sin(yaw);
        double kfs_map_z = robot_z;  // 简化：高度等于机器人高度
        
        // 查找该KFS属于哪个台阶
        int stair_id = find_stair_id(kfs_map_x, kfs_map_y, kfs_map_z);
        stair_ids.push_back(stair_id);
        kfs_map_x_list.push_back(kfs_map_x);
        kfs_map_y_list.push_back(kfs_map_y);
        kfs_map_z_list.push_back(kfs_map_z);
        
        RCLCPP_INFO(this->get_logger(),
            "KFS: class=%s, distance=%.2f, map_pos=(%.2f, %.2f, %.2f), stair=%d",
            kfs.class_name.c_str(), kfs.distance,
            kfs_map_x, kfs_map_y, kfs_map_z, stair_id);
    }

        // 【第4步】创建决策消息
    auto decision = yolov8_ros2_msgs::msg::KFSDecision();
    decision.timestamp = this->now();  // 时间戳
    decision.frame_id = "camera";

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

        // ===== 新增：判断每个台阶的可见性和遮挡情况 =====
// 这一步的目的：在初始化之前，标记哪些台阶是"可以看清的"
// 然后在后续逻辑中，如果这些可看清的台阶没有检测到KFS，就标记为"空"

std::array<bool, 12> stair_is_observable;  // 记录每个台阶是否可观察
std::array<StairState, 12> stairs_state;   // 初始化所有台阶状态

// 遍历所有12个台阶，判断每个是否可以被机器人观察到
for (int stair_id = 1; stair_id <= 12; ++stair_id) {
    int idx = stair_id - 1;
    
    // 【条件1】检查距离
    bool in_range = is_stair_in_detection_range(stair_id, robot_x, robot_y);
    
    // 【条件2】检查视角
    bool in_view = is_stair_in_view_angle(stair_id, robot_x, robot_y, yaw);
    
    // 【条件3】检查是否被前方台阶遮挡
    bool occluded = is_stair_occluded_by_front_stairs(stair_id);
    
    // 【综合判断】台阶可观察的条件：在距离范围内 AND 在视野内 AND 没被遮挡
    stair_is_observable[idx] = (in_range && in_view && !occluded);
    
    // 调试日志：打印不可观察的台阶信息
    if (!stair_is_observable[idx]) {
        if (!in_range) {
            RCLCPP_DEBUG(this->get_logger(),
                "Stair %d: Not observable - OUT OF RANGE", stair_id);
        } else if (!in_view) {
            RCLCPP_DEBUG(this->get_logger(),
                "Stair %d: Not observable - OUT OF VIEW", stair_id);
        } else if (occluded) {
            RCLCPP_DEBUG(this->get_logger(),
                "Stair %d: Not observable - OCCLUDED by front stairs", stair_id);
        }
    }
    }
    
    // ===== 新增：构建台阶内容快照 =====
    // 第1步：为每个台阶初始化状态-->已在前面声明，直接使用
    
    // 第2步：填充真KFS到对应台阶
    for (size_t i = 0; i < real_kfs_list_.size(); ++i) {
        int stair_id = stair_ids[i];
        
        if (stair_id >= 1 && stair_id <= 12) {
            int idx = stair_id - 1;  // 转换为数组索引
            
            // 确定物体类型
            if (real_kfs_list_[i].class_name == "r1") {
                stairs_state[idx].object_type = 1;
            } else if (real_kfs_list_[i].class_name == "r2") {
                stairs_state[idx].object_type = 2;
            }
            
            // 计算综合置信度 = YOLO置信度 × 位置匹配置信度
            double position_conf = compute_position_confidence(
                kfs_map_x_list[i], kfs_map_y_list[i], 
                STAIR_BOUNDARIES[idx]
            );
            stairs_state[idx].confidence = 
                real_kfs_list_[i].probability * position_conf;
        }
    }
    
    // 第3步：处理假KFS（只有1个）
    if (!fake_kfs_list_.empty()) {
        const auto& fake = fake_kfs_list_[0];
        
        // 计算假KFS的全局坐标
        double fake_map_x = robot_x + fake.distance * cos(yaw);
        double fake_map_y = robot_y + fake.distance * sin(yaw);
        double fake_map_z = robot_z;
        
        // 匹配到台阶
        int stair_id = find_stair_id(fake_map_x, fake_map_y, fake_map_z);
        
        if (stair_id >= 1 && stair_id <= 12) {
            int idx = stair_id - 1;
            
            // 只有在该台阶还没有其他物体时，才放置假KFS
            if (stairs_state[idx].object_type == 0) {
                stairs_state[idx].object_type = 3;  // 假KFS
                stairs_state[idx].confidence = fake.probability;
                
                RCLCPP_INFO(this->get_logger(),
                    "Fake KFS placed on stair %d", stair_id);
            } else {
                RCLCPP_WARN(this->get_logger(),
                    "Stair %d already occupied, fake_kfs ignored", stair_id);
            }
        }
    }

    // ===== 新增：判断可观察的台阶是否为空 =====
// 对于那些既可以被完全观察到、又没有检测到KFS的台阶，标记为"空"
for (int stair_id = 1; stair_id <= 12; ++stair_id) {
    int idx = stair_id - 1;
    
    // 只对可观察的台阶处理
    if (!stair_is_observable[idx]) {
        // 不可观察的台阶，保持"未知"状态，不做改动
        continue;
    }
    
    // 如果可观察，但当前没有任何物体
    if (stairs_state[idx].object_type == 4) {  // 4 = 未知
        stairs_state[idx].frames_without_detection++;
        
        // 多帧确认：连续 3 帧都没有检测到，才确认为"空"
        if (stairs_state[idx].frames_without_detection >= FRAMES_TO_CONFIRM_EMPTY) {
            stairs_state[idx].object_type = 0;  // 0 = 空
            stairs_state[idx].frames_without_detection = 0;  // 重置计数
            
            RCLCPP_INFO(this->get_logger(),
                "Stair %d confirmed as EMPTY after %d frames",
                stair_id, FRAMES_TO_CONFIRM_EMPTY);
        }
    } else {
        // 检测到了物体，重置"未检测帧数"
        stairs_state[idx].frames_without_detection = 0;
    }
    }
    
    // 第4步：构建并发布消息
    auto stair_match = yolov8_ros2_msgs::msg::StairMatchResult();
    stair_match.timestamp = this->now();
    stair_match.frame_id = "map";
    stair_match.total_stairs = 12;
    
    int r1_count = 0, r2_count = 0, fake_count = 0, empty_count = 0, unknown_count = 0;
    
    for (int i = 0; i < 12; ++i) {
        stair_match.stair_object_type.push_back(stairs_state[i].object_type);
        stair_match.stair_confidences.push_back(stairs_state[i].confidence);
        stair_match.stair_names.push_back(STAIR_BOUNDARIES[i].stair_name);
        
        // 统计
        switch (stairs_state[i].object_type) {
            case 1: r1_count++; break;
            case 2: r2_count++; break;
            case 3: fake_count++; break;
            case 4: unknown_count++; break;
            case 0: empty_count++; break;
        }
    }
    
    stair_match.total_r1_count = r1_count;
    stair_match.total_r2_count = r2_count;
    stair_match.total_fake_count = fake_count;
    stair_match.total_empty_count = empty_count;
    stair_match.total_unknown_count = unknown_count;
    
    stair_match_publisher_->publish(stair_match);
    
    RCLCPP_INFO(this->get_logger(),
        "Stairs: Unknown=%d, R1=%d, R2=%d, Fake=%d, Empty=%d",
        unknown_count, r1_count, r2_count, fake_count, empty_count);

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

int KfsManager::get_stair_row(int stair_id) const
{
    // 台阶1-3 在行1，4-6 在行2，7-9 在行3，10-12 在行4
    // 公式：行号 = (台阶ID - 1) / 3 + 1
    return (stair_id - 1) / 3 + 1;
}

int KfsManager::get_stair_col(int stair_id) const
{
    // 台阶1,4,7,10 在列1，2,5,8,11 在列2，3,6,9,12 在列3
    // 公式：列号 = (台阶ID - 1) % 3 + 1
    return (stair_id - 1) % 3 + 1;
}

int KfsManager::get_stair_height_level(int stair_id) const
{
    // 根据你的定义：
    // - 台阶 2, 4, 10, 12：高度 = h → 返回 1
    // - 台阶 1, 3, 5, 7, 9, 11：高度 = 2h → 返回 2
    // - 台阶 6, 8：高度 = 3h → 返回 3
    
    if (stair_id == 2 || stair_id == 4 || stair_id == 10 || stair_id == 12) {
        return 1;
    } else if (stair_id == 1 || stair_id == 3 || stair_id == 5 || 
               stair_id == 7 || stair_id == 9 || stair_id == 11) {
        return 2;
    } else if (stair_id == 6 || stair_id == 8) {
        return 3;
    }
    
    return -1;  // 错误：台阶ID无效
}

bool KfsManager::is_stair_in_detection_range(int stair_id, double robot_x, double robot_y) const
{
    if (stair_id < 1 || stair_id > 12) return false;
    
    // 获取台阶的中心坐标
    const auto& stair = STAIR_BOUNDARIES[stair_id - 1];
    double stair_x = (stair.x_min + stair.x_max) / 2.0;
    double stair_y = (stair.y_min + stair.y_max) / 2.0;
    
    // 计算机器人到台阶的欧几里得距离
    double dx = stair_x - robot_x;
    double dy = stair_y - robot_y;
    double distance = std::sqrt(dx * dx + dy * dy);
    
    // 判断是否在有效范围内
    return (distance >= MIN_STAIR_DETECTION_DISTANCE && 
            distance <= MAX_STAIR_DETECTION_DISTANCE);
}

bool KfsManager::is_stair_in_view_angle(int stair_id, double robot_x, double robot_y, double robot_yaw) const
{
    if (stair_id < 1 || stair_id > 12) return false;
    
    // 获取台阶的中心坐标
    const auto& stair = STAIR_BOUNDARIES[stair_id - 1];
    double stair_x = (stair.x_min + stair.x_max) / 2.0;
    double stair_y = (stair.y_min + stair.y_max) / 2.0;
    
    // 计算台阶相对于机器人的方向角（0° = 正东，逆时针为正）
    double dx = stair_x - robot_x;
    double dy = stair_y - robot_y;
    double stair_angle = std::atan2(dy, dx);  // 返回 [-π, π]
    
    // 计算相对角度（台阶相对于机器人的朝向）
    double relative_angle = stair_angle - robot_yaw;
    
    // 将角度标准化到 [-π, π]
    while (relative_angle > M_PI) relative_angle -= 2 * M_PI;
    while (relative_angle < -M_PI) relative_angle += 2 * M_PI;
    
    // RGB 视场角 69° = 1.204 弧度，所以左右各 34.5° = 0.602 弧度
    double half_fov = RGB_HORIZONTAL_FOV / 2.0;
    
    // 判断是否在视野范围内
    return (std::fabs(relative_angle) <= half_fov);
}

bool KfsManager::is_stair_occluded_by_front_stairs(int stair_id) const
{
    if (stair_id < 1 || stair_id > 12) return false;
    
    int target_row = get_stair_row(stair_id);
    int target_col = get_stair_col(stair_id);
    int target_height = get_stair_height_level(stair_id);
    
    // 如果在第1行，不可能被前面的遮挡
    if (target_row == 1) return false;
    
    // 检查前面所有行的台阶
    for (int front_row = 1; front_row < target_row; ++front_row) {
        // 检查同列和左右邻列（考虑视场角 69°）
        for (int col_offset = -1; col_offset <= 1; ++col_offset) {
            int check_col = target_col + col_offset;
            if (check_col < 1 || check_col > 3) continue;  // 超出范围
            
            // 计算前方台阶的ID
            int front_stair_id = (front_row - 1) * 3 + check_col;
            int front_height = get_stair_height_level(front_stair_id);
            
            // 如果前面的台阶高度 >= 目标台阶高度，被遮挡
            if (front_height >= target_height) {
                return true;
            }
        }
    }
    
    return false;  // 未被遮挡
}

void KfsManager::odometry_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
    // 保存最新的里程计数据到成员变量
    latest_odometry_ = *msg;
    odometry_received_ = true;  // 标记已收到
    
    // 可选：调试输出（查看是否正确接收）
    RCLCPP_DEBUG(this->get_logger(), 
        "Odometry: x=%.2f, y=%.2f, z=%.2f",
        msg->pose.pose.position.x,
        msg->pose.pose.position.y,
        msg->pose.pose.position.z);
}


// ===== 台阶匹配函数 =====
int KfsManager::find_stair_id(double kfs_x, double kfs_y, double kfs_z) const
{
    // 遍历所有定义好的台阶
    for (const auto& stair : STAIR_BOUNDARIES) {
        // 检查KFS是否在该台阶的3D边界内
        if (kfs_x >= stair.x_min && kfs_x <= stair.x_max &&
            kfs_y >= stair.y_min && kfs_y <= stair.y_max &&
            kfs_z >= stair.z_min && kfs_z <= stair.z_max) {
                RCLCPP_INFO(this->get_logger(),
                "KFS matched to stair %d (%s)",
                stair.stair_id, stair.stair_name);
            return stair.stair_id;  // 返回台阶ID
        }
    }
    
    // 如果不在任何台阶范围内
    RCLCPP_WARN(this->get_logger(),
        "KFS at (%.2f, %.2f, %.2f) doesn't match any stair",
        kfs_x, kfs_y, kfs_z);
    return -1;  // 返回-1表示无效
}

// ===== 辅助函数：计算位置匹配置信度 =====
double KfsManager::compute_position_confidence(double kfs_x, double kfs_y, 
                                              const StairBoundary& stair) const
{
    // 计算KFS距离台阶中心的相对位置
    double center_x = (stair.x_min + stair.x_max) / 2.0;
    double center_y = (stair.y_min + stair.y_max) / 2.0;
    
    double width = (stair.x_max - stair.x_min) / 2.0;
    double height = (stair.y_max - stair.y_min) / 2.0;
    
    // 避免除以零
    if (width < 0.001 || height < 0.001) {
        return 0.5;  // 默认值
    }
    
    // 计算相对距离
    double dx = fabs(kfs_x - center_x) / width;
    double dy = fabs(kfs_y - center_y) / height;
    double normalized_dist = std::max(dx, dy);
    
    // 高斯函数：中心为1.0，边界约0.6，远处趋向0.0
    return std::exp(-normalized_dist * normalized_dist);
}

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<KfsManager>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
