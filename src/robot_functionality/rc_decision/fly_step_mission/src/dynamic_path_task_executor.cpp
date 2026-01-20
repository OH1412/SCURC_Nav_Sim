#include "fly_step_mission/dynamic_path_task_executor.hpp"
#include <cmath>
#include <iostream>
#include <memory>
#include <future>

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
    ascend_margin_mm_(200), // 初始化默认裕量为200mm
    nav_goal_sent_(false), nav_result_ready_(false)
{
    // 创建 Nav2 Action Client
    nav_client_ = rclcpp_action::create_client<NavigateToPose>(node_, "navigate_to_pose");
    
    // 创建速度发布者（用于升降控制）
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
        // [新增] 升降裕量参数，默认200mm
        BT::InputPort<int>("ascend_margin_mm", 200, "Extra height margin for ascend tasks in mm (default: 200)")
    };
}

bool DynamicPathTaskExecutor::parseTaskInfoFromYaml()
{
    // 获取航点文件路径
    if (!getInput("waypoints_file", waypoints_file_)) {
        waypoints_file_ = std::string(getenv("HOME")) + "/r2_ws/src/r2_waypoint_loader_cpp/config/waypoints.yaml";
        RCLCPP_WARN(node_->get_logger(), "Parameter 'waypoints_file' not found, using default: %s", waypoints_file_.c_str());
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

    // 获取升降裕量参数
    if (!getInput("ascend_margin_mm", ascend_margin_mm_)) {
        ascend_margin_mm_ = 200; // 如果XML没配置，默认200
        RCLCPP_INFO(node_->get_logger(), "Ascend margin not set, using default: 200mm");
    } else {
        RCLCPP_INFO(node_->get_logger(), "Ascend margin set to: %d mm", ascend_margin_mm_);
    }

    // 从黑板获取路径（由PathGeneratorNode生成）
    try {
        full_path_ = config().blackboard->get<std::vector<geometry_msgs::msg::PoseStamped>>("generated_path");
        RCLCPP_INFO(node_->get_logger(), "Got generated_path from blackboard with %zu waypoints", full_path_.size());
        
        // 调试：打印从黑板获取的每个航点坐标
        for (size_t i = 0; i < full_path_.size(); ++i) {
            RCLCPP_INFO(node_->get_logger(), "  [DEBUG] Blackboard waypoint[%zu]: X=%.3f, Y=%.3f, frame=%s",
                i, full_path_[i].pose.position.x, full_path_[i].pose.position.y,
                full_path_[i].header.frame_id.c_str());
        }
    } catch (const std::exception& e) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to get 'generated_path' from blackboard: %s", e.what());
        return BT::NodeStatus::FAILURE;
    }

    // 从黑板获取任务映射（由PathGeneratorNode生成）
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

    // 从黑板获取所有航点映射（用于ID查找）
    try {
        all_wp_map_ = config().blackboard->get<std::map<std::string, geometry_msgs::msg::PoseStamped>>("all_wp_map");
        RCLCPP_INFO(node_->get_logger(), "Got all_wp_map from blackboard with %zu waypoints", all_wp_map_.size());
    } catch (const std::exception& e) {
        RCLCPP_WARN(node_->get_logger(), "Failed to get 'all_wp_map' from blackboard: %s", e.what());
    }

    // 初始化索引
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
    switch (state_) {
        case NAVIGATING_TO_WAYPOINT:
        {
            // 如果还没发送导航目标，先发送
            if (!nav_goal_sent_) {
                RCLCPP_INFO(node_->get_logger(), "Starting navigation to waypoint %zu (ID: %s)", 
                           current_index_, current_waypoint_id_.c_str());
                
                if (!startNavigation(current_target_pose_)) {
                    RCLCPP_ERROR(node_->get_logger(), "Failed to start navigation");
                    return BT::NodeStatus::FAILURE;
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
            state_ = CHECKING_TASK;
            return BT::NodeStatus::RUNNING;
        }

        case CHECKING_TASK:
        {
            // 检查当前航点是否有任务
            auto task_it = wp_task_map_.find(current_waypoint_id_);
            if (task_it != wp_task_map_.end()) {
                WaypointTaskInfo task_info = task_it->second;
                RCLCPP_INFO(node_->get_logger(), "Found task for waypoint %s: %s", 
                           current_waypoint_id_.c_str(), task_info.action.c_str());

                if (task_info.action == "ascend") {
                    // 立即执行上升任务
                    RCLCPP_INFO(node_->get_logger(), "Preparing to execute immediate ascend task");

                    // 获取当前Z值
                    double current_z = 0.0;
                    if (!getCurrentZ(current_z)) {
                        RCLCPP_WARN(node_->get_logger(), "Could not get current Z, using 0.0");
                    }

                    // 加上裕量 ascend_margin_mm_
                    int effective_height_mm = task_info.height_mm + ascend_margin_mm_;
                    target_ascend_height_ = current_z + (effective_height_mm / 1000.0);
                    
                    state_ = EXECUTING_ASCEND;
                    action_start_time_ = node_->get_clock()->now();
                    
                    RCLCPP_INFO(node_->get_logger(), "Starting ascend: current_z=%.3f, target=%.3f, base_height=%d, margin=%d, total=%d",
                               current_z, target_ascend_height_, task_info.height_mm, ascend_margin_mm_, effective_height_mm);
                    
                    return BT::NodeStatus::RUNNING;
                }
                else if (task_info.action == "delayed_descend") {
                    // 标记下一个航点需要执行下降任务
                    RCLCPP_INFO(node_->get_logger(), "Marking delayed descend task for next waypoint (height_mm=%d)", 
                               task_info.height_mm);
                    
                    requires_next_waypoint_task_ = true;
                    next_waypoint_task_type_ = "descend";
                    // 保存下降高度供后续使用
                    // target_descend_height_ 会在实际执行时根据当前Z计算
                    
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
            } else {
                RCLCPP_DEBUG(node_->get_logger(), "No task found for waypoint %s", current_waypoint_id_.c_str());
            }

            // 检查是否有延迟任务需要在此航点执行
            if (requires_next_waypoint_task_ && next_waypoint_task_type_ == "descend") {
                RCLCPP_INFO(node_->get_logger(), "Executing delayed descend task at waypoint %s", current_waypoint_id_.c_str());

                // 获取当前Z值
                double current_z = 0.0;
                if (!getCurrentZ(current_z)) {
                    RCLCPP_WARN(node_->get_logger(), "Could not get current Z, using 0.0");
                }

                target_descend_height_ = current_z - 0.2; // 默认下降200mm，后续可从配置读取
                state_ = EXECUTING_DESCEND;
                action_start_time_ = node_->get_clock()->now();
                
                RCLCPP_INFO(node_->get_logger(), "Starting descend: current_z=%.3f, target=%.3f",
                           current_z, target_descend_height_);
                
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
                return BT::NodeStatus::FAILURE;
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
            
            // 继续下降
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

    auto future_goal_handle = nav_client_->async_send_goal(nav_goal, send_goal_options);

    // 等待 goal 被接受
    if (rclcpp::spin_until_future_complete(node_, future_goal_handle, std::chrono::seconds(5))
        != rclcpp::FutureReturnCode::SUCCESS)
    {
        RCLCPP_ERROR(node_->get_logger(), "Failed to send navigation goal");
        return false;
    }

    nav_goal_handle_ = future_goal_handle.get();
    if (!nav_goal_handle_) {
        RCLCPP_ERROR(node_->get_logger(), "Navigation goal was rejected");
        return false;
    }

    nav_goal_sent_ = true;
    RCLCPP_INFO(node_->get_logger(), "Navigation goal accepted");
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
        if (!tf_buffer_->canTransform("map", "base_link", tf2::TimePointZero, std::chrono::seconds(5))) {
            RCLCPP_WARN(node_->get_logger(), "TF not available after 5s (map -> base_link)");
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