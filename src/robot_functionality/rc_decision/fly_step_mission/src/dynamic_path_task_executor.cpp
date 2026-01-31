#include "fly_step_mission/dynamic_path_task_executor.hpp"
#include <cmath>
#include <iostream>
#include <memory>
#include <future>
#include <set> 
#include <string>
// ament helper to locate package share dir
#include <ament_index_cpp/get_package_share_directory.hpp>

namespace fly_step_mission
{

DynamicPathTaskExecutor::DynamicPathTaskExecutor(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node
) : BT::StatefulActionNode(name, config), node_(node), current_index_(0), state_(NAVIGATING_TO_WAYPOINT),
    task_executed_(false), requires_next_waypoint_task_(false), next_waypoint_task_type_("none"),
    target_ascend_height_(0.0), target_descend_height_(0.0), 
    ascend_speed_(0.5), descend_speed_(0.5), 
    ascend_max_duration_(10.0), descend_max_duration_(10.0),
    ascend_margin_mm_(200), // 初始化上升裕量为 200mm
    descend_margin_mm_(100), // 初始化下降裕量为 100mm
    nav_goal_sent_(false), nav_result_ready_(false)
{
    // 创建 Nav2 Action Client
    nav_client_ = rclcpp_action::create_client<NavigateToPose>(node_, "navigate_to_pose");
    
    // 创建速度发布者
    vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);
    
    // 创建 TF buffer 和 listener
    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(node_->get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
    
    RCLCPP_INFO(node_->get_logger(), "DynamicPathTaskExecutor initialized");
}

BT::PortsList DynamicPathTaskExecutor::providedPorts()
{
    return {
        BT::InputPort<std::vector<geometry_msgs::msg::PoseStamped>>("waypoint_path", "Complete path with waypoints to execute"),
        BT::InputPort<std::vector<int>>("main_waypoints", "Main waypoint IDs for task mapping"),
        BT::InputPort<std::string>("waypoints_file", "Path to waypoints YAML file with task definitions"),
        BT::InputPort<int>("ascend_margin_mm", 200, "Extra height margin for ascend tasks in mm (default: 200)"),
        BT::InputPort<int>("descend_margin_mm", 100, "Subtract margin from descend tasks in mm (default: 100)")
    };
}

bool DynamicPathTaskExecutor::parseTaskInfoFromYaml()
{
    // 获取航点文件路径
    if (!getInput("waypoints_file", waypoints_file_)) {
        try {
            std::string pkg_share = ament_index_cpp::get_package_share_directory("fly_step_mission");
            waypoints_file_ = pkg_share + "/config/waypoints.yaml";
        } catch (const std::exception & e) {
            // 如果查询失败，使用包内相对路径（运行时从安装或源码顶层查找）
            waypoints_file_ = std::string("config/waypoints.yaml");
            RCLCPP_WARN(node_->get_logger(), "Could not find package share dir: %s; falling back to: %s", e.what(), waypoints_file_.c_str());
        }
        RCLCPP_INFO(node_->get_logger(), "Parameter 'waypoints_file' not found, using default: %s", waypoints_file_.c_str());
    }

    // 打开YAML文件
    std::ifstream yaml_file(waypoints_file_);
    if (!yaml_file.is_open()) {
        RCLCPP_ERROR(node_->get_logger(), "无法打开YAML文件：%s", waypoints_file_.c_str());
        return false;
    }

    // 加载YAML根节点
    YAML::Node root;
    try {
        root = YAML::Load(yaml_file);
    } catch (const YAML::Exception& e) {
        RCLCPP_ERROR(node_->get_logger(), "YAML解析错误：%s", e.what());
        return false;
    }

    // 清空之前的任务映射
    wp_task_map_.clear();

    // 获取所有航点ID
    std::vector<std::string> all_wp_ids = root["prepoints"].as<std::vector<std::string>>();

    // 读取所有航点的task信息
    for (const auto& wp_id_str : all_wp_ids) {
        if (!root[wp_id_str]) {
            RCLCPP_WARN(node_->get_logger(), "YAML中缺少航点：%s，跳过", wp_id_str.c_str());
            continue;
        }

        // 读取 YAML 中的 task 字段（如果存在的话）
        if (root[wp_id_str]["task"]) {
            try {
                WaypointTaskInfo task_info;
                // 读取 YAML 中的 action（对应 "ascend" 或 "delayed_descend"）
                task_info.action = root[wp_id_str]["task"]["action"].as<std::string>();
                // 读取 YAML 中的 height_mm（对应 200 或 400）
                task_info.height_mm = root[wp_id_str]["task"]["height_mm"].as<int>();
                // 关联航点ID和任务信息
                wp_task_map_[wp_id_str] = task_info;
                RCLCPP_DEBUG(node_->get_logger(), "航点%s绑定任务：action=%s, height_mm=%d",
                    wp_id_str.c_str(), task_info.action.c_str(), task_info.height_mm);
            } catch (const YAML::Exception& e) {
                RCLCPP_WARN(node_->get_logger(), "解析航点%s的task字段失败：%s", wp_id_str.c_str(), e.what());
                // 即使 task 解析失败，也不中断整体流程，继续解析其他航点
                continue;
            }
        }
    }

    RCLCPP_INFO(node_->get_logger(), "成功解析YAML文件，共%d个航点包含任务定义", (int)wp_task_map_.size());
    return true;
}

std::string DynamicPathTaskExecutor::getWaypointIdByIndex(size_t index)
{
    if (index >= full_path_.size()) return "";
    auto& target_pose = full_path_[index].pose;

    // 使用 all_wp_map_ 查找最接近的航点ID
    std::string closest_id = "";
    double min_distance = std::numeric_limits<double>::max();

    for (const auto& [wp_id, wp_pose] : all_wp_map_) {
        double x = wp_pose.pose.position.x;
        double y = wp_pose.pose.position.y;
        double distance = sqrt(pow(target_pose.position.x - x, 2) + pow(target_pose.position.y - y, 2));
        
        if (distance < min_distance && distance < 0.1) { // 误差小于0.1米认为是同一个点
            min_distance = distance;
            closest_id = wp_id;
        }
    }

    // 如果上面的方法没找到，我们尝试另一种方法：从路径本身获取ID
    if (closest_id.empty() && index < wp_ids_.size()) {
        closest_id = wp_ids_[index];
    }

    RCLCPP_DEBUG(node_->get_logger(), "Waypoint index %zu -> ID: %s (distance: %.3f)", 
                 index, closest_id.c_str(), min_distance);

    return closest_id;
}

BT::NodeStatus DynamicPathTaskExecutor::onStart()
{
    RCLCPP_INFO(node_->get_logger(), "Starting DynamicPathTaskExecutor...");

    // 1a. 获取升降裕量
    if (!getInput("ascend_margin_mm", ascend_margin_mm_)) {
        ascend_margin_mm_ = 200;
    }

    // 1b. 获取下降裕量
    if (!getInput("descend_margin_mm", descend_margin_mm_)) {
        descend_margin_mm_ = 100;
        RCLCPP_INFO(node_->get_logger(), "Descend margin not set, using default: 100mm");
    } else {
        RCLCPP_INFO(node_->get_logger(), "Descend margin set to: %d mm", descend_margin_mm_);
    }

    // 2. 获取并存储主航点 ID 集合
    main_wp_ids_set_.clear();
    std::vector<int> main_wps_input;
    if (getInput("main_waypoints", main_wps_input)) {
        for(int id : main_wps_input) {
            main_wp_ids_set_.insert(std::to_string(id));
        }
        RCLCPP_INFO(node_->get_logger(), "Loaded %zu main waypoints for logic checking.", main_wp_ids_set_.size());
    } else {
        RCLCPP_WARN(node_->get_logger(), "Failed to load main_waypoints port!");
    }

    // 3. 从黑板获取路径（由PathGeneratorNode生成）
    try {
        full_path_ = config().blackboard->get<std::vector<geometry_msgs::msg::PoseStamped>>("generated_path");
    } catch (const std::exception& e) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to get 'generated_path': %s", e.what());
        return BT::NodeStatus::FAILURE;
    }

    // 4. 从黑板获取任务映射（由PathGeneratorNode生成）
    try {
        wp_task_map_ = config().blackboard->get<std::map<std::string, WaypointTaskInfo>>("waypoint_task_map");
        RCLCPP_INFO(node_->get_logger(), "Got waypoint_task_map from blackboard with %zu tasks", wp_task_map_.size());
    } catch (const std::exception& e) {
        RCLCPP_WARN(node_->get_logger(), "Failed to get 'waypoint_task_map' from blackboard: %s, will parse from YAML", e.what());
        // 如果黑板中没有，则从YAML解析
        if (!parseTaskInfoFromYaml()) {
            RCLCPP_ERROR(node_->get_logger(), "Failed to parse task information from YAML");
            return BT::NodeStatus::FAILURE;
        }
    }

    // 5. 获取所有航点映射
    try {
        all_wp_map_ = config().blackboard->get<std::map<std::string, geometry_msgs::msg::PoseStamped>>("all_wp_map");
    } catch (const std::exception& e) {
        RCLCPP_WARN(node_->get_logger(), "Failed to get 'all_wp_map': %s", e.what());
    }

    current_index_ = 0;
    state_ = NAVIGATING_TO_WAYPOINT;
    task_executed_ = false;
    requires_next_waypoint_task_ = false;
    next_waypoint_task_type_ = "none";

    RCLCPP_INFO(node_->get_logger(), "Initialized to execute %zu waypoints", full_path_.size());

    if (full_path_.empty()) {
        RCLCPP_WARN(node_->get_logger(), "Waypoint path is empty");
        return BT::NodeStatus::SUCCESS;
    }

    // 开始导航到第一个航点
    current_target_pose_ = full_path_[0];
    current_waypoint_id_ = getWaypointIdByIndex(0);

    return BT::NodeStatus::RUNNING;
}

BT::NodeStatus DynamicPathTaskExecutor::onRunning()
{
    bool should_execute_task = false;
    auto task_it = wp_task_map_.end();

    switch (state_) {
        case NAVIGATING_TO_WAYPOINT:
        {
            // 如果还没发送导航目标，先发送
            if (!nav_goal_sent_) {
                RCLCPP_INFO(node_->get_logger(), "Navigating to WP %zu (ID: %s)", 
                           current_index_, current_waypoint_id_.c_str());
                
                if (!startNavigation(current_target_pose_)) {
                    RCLCPP_ERROR(node_->get_logger(), "Failed to start navigation");
                    return BT::NodeStatus::FAILURE;
                }
                nav_goal_sent_ = true;
                goal_handshake_pending_ = true; // 标记开始握手
                return BT::NodeStatus::RUNNING; // 立即返回，不阻塞
            }

            if (goal_handshake_pending_) {
                // 检查 future 是否这就绪了 (wait_for 0秒 = 立即检查)
                if (future_goal_handle_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                    auto goal_handle = future_goal_handle_.get();
                    if (!goal_handle) {
                        RCLCPP_ERROR(node_->get_logger(), "Navigation goal was rejected by server");
                        return BT::NodeStatus::FAILURE;
                    }
                    // 握手成功
                    nav_goal_handle_ = goal_handle;
                    goal_handshake_pending_ = false; 
                    RCLCPP_INFO(node_->get_logger(), "Goal accepted by server.");
                } else {
                    // 还没收到回复，下一帧再来检查
                    return BT::NodeStatus::RUNNING;
                }
            }

            // 检查导航状态
            auto nav_status = checkNavigationStatus();
            if (nav_status == BT::NodeStatus::RUNNING) {
                return BT::NodeStatus::RUNNING;
            } else if (nav_status == BT::NodeStatus::FAILURE) {
                RCLCPP_ERROR(node_->get_logger(), "Navigation failed for waypoint %zu", current_index_);
                return BT::NodeStatus::FAILURE;
            }
            
            // 导航成功，进入任务检查阶段
            RCLCPP_INFO(node_->get_logger(), "Reached waypoint %zu (ID: %s)", 
                       current_index_, current_waypoint_id_.c_str());

            // 重置导航相关标志，防止影响下一次导航
            nav_goal_sent_ = false;
            nav_result_ready_ = false;
            goal_handshake_pending_ = false;

            state_ = CHECKING_TASK;
            return BT::NodeStatus::RUNNING;
        }

        case CHECKING_TASK:
        {
            // 默认是否执行任务：否
            should_execute_task = false;

            // 1. 检查是否有任务定义
            task_it = wp_task_map_.find(current_waypoint_id_);
            if (task_it != wp_task_map_.end()) {
                
                // 2. 检查上一个航点是否是主航点
                // 只有当前一点是主航点时，当前点的任务才有效 (例如 -1 是主航点，则 -1_front 执行)
                if (current_index_ > 0) {
                    std::string prev_wp_id = getWaypointIdByIndex(current_index_ - 1);
                    
                    // 检查 prev_wp_id 是否存在于主航点集合中
                    if (main_wp_ids_set_.find(prev_wp_id) != main_wp_ids_set_.end()) {
                        should_execute_task = true;
                        RCLCPP_INFO(node_->get_logger(), "Task Approved: Previous WP (%s) is a Main Waypoint.", prev_wp_id.c_str());
                    } else {
                        RCLCPP_INFO(node_->get_logger(), "Task Skipped: Previous WP (%s) is NOT a Main Waypoint.", prev_wp_id.c_str());
                    }
                } else {
                    // 如果是第0个点，通常没有“上一个点”，所以不执行任务
                    RCLCPP_INFO(node_->get_logger(), "Task Skipped: Start point has no previous waypoint.");
                }

                // 3. 执行逻辑
                if (should_execute_task) {
                    WaypointTaskInfo task_info = task_it->second;

                    if (task_info.action == "ascend") {
                        // Ascend 任务执行逻辑
                        double current_z = 0.0;
                        if (!getCurrentZ(current_z)) RCLCPP_WARN(node_->get_logger(), "No TF for Z");

                    // 加上裕量 ascend_margin_mm_
                        int effective_height_mm = task_info.height_mm + ascend_margin_mm_;
                        target_ascend_height_ = current_z + (effective_height_mm / 1000.0);
                        state_ = EXECUTING_ASCEND;
                        action_start_time_ = node_->get_clock()->now();
                        
                        RCLCPP_INFO(node_->get_logger(), ">>> START ASCEND: Target=%.3f (Margin=%d)", target_ascend_height_, ascend_margin_mm_);
                        return BT::NodeStatus::RUNNING;
                    }
                    else if (task_info.action == "delayed_descend") {
                        // 标记阶段：计算并保存“净下降距离”
                        RCLCPP_INFO(node_->get_logger(), ">>> MARKED DESCEND for next WP. Raw: %d, Margin: %d", task_info.height_mm, descend_margin_mm_);
                        requires_next_waypoint_task_ = true;
                        next_waypoint_task_type_ = "descend";

                        // 计算：任务高度 - 裕量 (例如 200 - 100 = 100mm)
                        int effective_drop_mm = task_info.height_mm - descend_margin_mm_;
                        if (effective_drop_mm < 0) effective_drop_mm = 0; // 防止变成上升

                        // 等到了下一个点执行时，计算绝对坐标
                        target_descend_height_ = effective_drop_mm / 1000.0;

                        // 跳转到移动逻辑
                        // 重置导航状态，移动到下一个航点
                        nav_goal_sent_ = false;
                        nav_result_ready_ = false;

                        current_index_++;
                        if (current_index_ >= full_path_.size()) {
                            state_ = COMPLETED;
                            return BT::NodeStatus::SUCCESS;
                        }

                        current_target_pose_ = full_path_[current_index_];
                        current_waypoint_id_ = getWaypointIdByIndex(current_index_);
                        state_ = NAVIGATING_TO_WAYPOINT;
                        return BT::NodeStatus::RUNNING;
                    }
                }
            } else {
                RCLCPP_DEBUG(node_->get_logger(), "No task found for waypoint %s", current_waypoint_id_.c_str());
            }

            // 检查是否有延迟任务需要在此航点执行
            if (requires_next_waypoint_task_ && next_waypoint_task_type_ == "descend") {
                RCLCPP_INFO(node_->get_logger(), "Executing marked delayed descend task.");
                
                // 获取当前Z值
                double current_z = 0.0;
                if (!getCurrentZ(current_z)) {
                    RCLCPP_WARN(node_->get_logger(), "Could not get current Z, using 0.0");
                }

                // 执行阶段：取出暂存的“下降距离”，计算绝对目标
                double drop_distance = target_descend_height_;

                // 目标 = 当前高度 - 下降距离 (0.4 - 0.1 = 0.3)
                target_descend_height_ = current_z - drop_distance;

                state_ = EXECUTING_DESCEND;
                action_start_time_ = node_->get_clock()->now();
                
                RCLCPP_INFO(node_->get_logger(), "Starting descend: current_z=%.3f, drop=%.3f, target=%.3f",
                           current_z, drop_distance, target_descend_height_);
                
                // 重置延迟任务标记
                requires_next_waypoint_task_ = false;
                next_waypoint_task_type_ = "none";
                return BT::NodeStatus::RUNNING;
            }

            // 没有任务需要执行，移动到下一个航点
            // 重置导航状态
            nav_goal_sent_ = false;
            nav_result_ready_ = false;
            current_index_++;
            if (current_index_ >= full_path_.size()) {
                state_ = COMPLETED;
                return BT::NodeStatus::SUCCESS;
            }
            current_target_pose_ = full_path_[current_index_];
            current_waypoint_id_ = getWaypointIdByIndex(current_index_);
            state_ = NAVIGATING_TO_WAYPOINT;
            return BT::NodeStatus::RUNNING;
        }

        case EXECUTING_ASCEND:
        {
            // 检查超时
            auto elapsed = (node_->get_clock()->now() - action_start_time_).seconds();
            if (elapsed > ascend_max_duration_) {
                RCLCPP_WARN(node_->get_logger(), "Ascend timeout (%.2fs > %.2fs)", elapsed, ascend_max_duration_);
                publishZVelocity(0.0);
                return BT::NodeStatus::FAILURE;
            }
            
            // 获取当前高度
            double current_z;
            if (!getCurrentZ(current_z)) {
                RCLCPP_ERROR(node_->get_logger(), "Failed to get current Z during ascend");
                publishZVelocity(0.0);
                return BT::NodeStatus::FAILURE;
            }
            
            // 检查是否达到目标高度
            const double eps = 0.01;
            if (current_z + eps >= target_ascend_height_) {
                RCLCPP_INFO(node_->get_logger(), "Ascend completed: z=%.3f, target=%.3f", 
                           current_z, target_ascend_height_);
                publishZVelocity(0.0);
                
                // 重置导航状态，准备下一个航点
                nav_goal_sent_ = false;
                nav_result_ready_ = false;
                current_index_++;
                if (current_index_ >= full_path_.size()) {
                    state_ = COMPLETED;
                    return BT::NodeStatus::SUCCESS;
                }
                current_target_pose_ = full_path_[current_index_];
                current_waypoint_id_ = getWaypointIdByIndex(current_index_);
                state_ = NAVIGATING_TO_WAYPOINT;
                return BT::NodeStatus::RUNNING;
            }
            
            // 继续上升
            publishZVelocity(ascend_speed_);
            return BT::NodeStatus::RUNNING;
        }

        case EXECUTING_DESCEND:
        {
            // 检查超时
            auto elapsed = (node_->get_clock()->now() - action_start_time_).seconds();
            if (elapsed > descend_max_duration_) {
                RCLCPP_WARN(node_->get_logger(), "Descend timeout (%.2fs > %.2fs)", elapsed, descend_max_duration_);
                publishZVelocity(0.0);
                return BT::NodeStatus::FAILURE; // 或者 SUCCESS，视安全性而定
            }
            
            // 获取当前高度
            double current_z;
            if (!getCurrentZ(current_z)) {
                RCLCPP_ERROR(node_->get_logger(), "Failed to get current Z during descend");
                publishZVelocity(0.0);
                return BT::NodeStatus::FAILURE;
            }
            
            // 检查是否达到目标高度
            const double eps = 0.01;
            if (current_z <= target_descend_height_ + eps) {
                RCLCPP_INFO(node_->get_logger(), "Descend completed: z=%.3f, target=%.3f", 
                           current_z, target_descend_height_);
                publishZVelocity(0.0);
                
                // 重置导航状态，准备下一个航点
                nav_goal_sent_ = false;
                nav_result_ready_ = false;
                current_index_++;
                if (current_index_ >= full_path_.size()) {
                    state_ = COMPLETED;
                    return BT::NodeStatus::SUCCESS;
                }
                current_target_pose_ = full_path_[current_index_];
                current_waypoint_id_ = getWaypointIdByIndex(current_index_);
                state_ = NAVIGATING_TO_WAYPOINT;
                return BT::NodeStatus::RUNNING;
            }
            
            publishZVelocity(-descend_speed_);
            return BT::NodeStatus::RUNNING;
        }

        case COMPLETED:
            RCLCPP_INFO(node_->get_logger(), "Completed executing all waypoints and tasks");
            return BT::NodeStatus::SUCCESS;

        default:
            return BT::NodeStatus::RUNNING;
    }
}

void DynamicPathTaskExecutor::onHalted()
{
    RCLCPP_INFO(node_->get_logger(), "DynamicPathTaskExecutor halted");
    // 停止任何正在进行的升降
    publishZVelocity(0.0);
    // 取消正在进行的导航
    if (nav_goal_handle_) {
        nav_client_->async_cancel_goal(nav_goal_handle_);
    }
}

bool DynamicPathTaskExecutor::ensureNavClient()
{
    if (!nav_client_) {
        RCLCPP_ERROR(node_->get_logger(), "Nav2 action client not initialized");
        return false;
    }

    if (!nav_client_->action_server_is_ready()) {
        RCLCPP_INFO(node_->get_logger(), "Waiting for Nav2 action server (up to 60s)...");
        if (!nav_client_->wait_for_action_server(std::chrono::seconds(60))) {
            RCLCPP_ERROR(node_->get_logger(), "Nav2 action server not available after 60s");
            return false;
        }
        RCLCPP_INFO(node_->get_logger(), "Nav2 action server is ready!");
    }
    return true;
}

bool DynamicPathTaskExecutor::startNavigation(const geometry_msgs::msg::PoseStamped & goal)
{
    if (!ensureNavClient()) {
        return false;
    }

    nav_goal_sent_ = false;
    nav_result_ready_ = false;

    NavigateToPose::Goal nav_goal;
    nav_goal.pose = goal;
    nav_goal.pose.header.stamp = node_->now();

    auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};
    send_goal_options.result_callback = [this](const GoalHandle::WrappedResult & result) {
        nav_result_ = result;
        nav_result_ready_ = true;
    };

    RCLCPP_INFO(node_->get_logger(), "Sending navigation goal: (%.2f, %.2f) frame=%s",
        goal.pose.position.x, goal.pose.position.y, goal.header.frame_id.c_str());

    future_goal_handle_ = nav_client_->async_send_goal(nav_goal, send_goal_options);
    // auto future_goal_handle = nav_client_->async_send_goal(nav_goal, send_goal_options);

    // // 等待 goal 被接受
    // if (rclcpp::spin_until_future_complete(node_, future_goal_handle, std::chrono::seconds(5))
    //     != rclcpp::FutureReturnCode::SUCCESS)
    // {
    //     RCLCPP_ERROR(node_->get_logger(), "Failed to send navigation goal");
    //     return false;
    // }

    // nav_goal_handle_ = future_goal_handle.get();
    // if (!nav_goal_handle_) {
    //     RCLCPP_ERROR(node_->get_logger(), "Navigation goal was rejected");
    //     return false;
    // }

    // nav_goal_sent_ = true;
    // RCLCPP_INFO(node_->get_logger(), "Navigation goal accepted");
    return true;
}

BT::NodeStatus DynamicPathTaskExecutor::checkNavigationStatus()
{
    if (!nav_goal_sent_) {
        return BT::NodeStatus::FAILURE;
    }

    if (!nav_result_ready_) {
        rclcpp::spin_some(node_);
        return BT::NodeStatus::RUNNING;
    }

    switch (nav_result_.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
            RCLCPP_INFO(node_->get_logger(), "Navigation succeeded");
            return BT::NodeStatus::SUCCESS;
        case rclcpp_action::ResultCode::ABORTED:
            RCLCPP_WARN(node_->get_logger(), "Navigation aborted");
            return BT::NodeStatus::FAILURE;
        case rclcpp_action::ResultCode::CANCELED:
            RCLCPP_WARN(node_->get_logger(), "Navigation canceled");
            return BT::NodeStatus::FAILURE;
        default:
            RCLCPP_ERROR(node_->get_logger(), "Navigation unknown result");
            return BT::NodeStatus::FAILURE;
    }
}

bool DynamicPathTaskExecutor::getCurrentZ(double & z_out)
{
    try {
        if (!tf_buffer_->canTransform("map", "base_link", tf2::TimePointZero, std::chrono::milliseconds(10))) {
            RCLCPP_WARN(node_->get_logger(), "TF not available after 10ms (map -> base_link)");
            return false;
        }
        auto tf = tf_buffer_->lookupTransform("map", "base_link", tf2::TimePointZero);
        z_out = tf.transform.translation.z;
        return true;
    }
    catch (const tf2::TransformException & ex) {
        RCLCPP_WARN(node_->get_logger(), "TF lookup failed: %s", ex.what());
        return false;
    }
}

void DynamicPathTaskExecutor::publishZVelocity(double z_vel)
{
    geometry_msgs::msg::Twist cmd;
    cmd.linear.z = z_vel;
    vel_pub_->publish(cmd);
}

} // namespace fly_step_mission