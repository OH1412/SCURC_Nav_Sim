#include "../include/waypoint_loader.hpp"
#include "../include/plugins/r2_waypoint_task.hpp"
#include <yaml-cpp/yaml.h>
#include <fstream>
#include <cmath>
#include <iostream>

using namespace r2_waypoint_loader_cpp;
using namespace std::chrono_literals;

// 构造函数：初始化节点、参数与组件
WaypointLoader::WaypointLoader(const rclcpp::NodeOptions& options) 
    : Node("r2_waypoint_loader_node", options) {
    RCLCPP_INFO(this->get_logger(), "初始化航点加载器节点...");
    init_parameters();   // 获取参数
    init_components();   // 初始化组件
    // 启动延迟定时器（延迟后开始解析航点）
    start_timer_ = this->create_wall_timer(
        std::chrono::duration<double>(start_delay_),
        std::bind(&WaypointLoader::on_start_timer, this)
    );
}

// 初始化节点参数（从参数服务器或默认值获取）
void WaypointLoader::init_parameters() {
    // 1. 声明参数并设置默认值
    this->declare_parameter("start_delay", 2.0, 
        rcl_interfaces::msg::ParameterDescriptor{}
            .set__description("节点启动后延迟多久开始解析航点（单位：秒）"));
    this->declare_parameter("waypoints_file", 
        std::string(getenv("HOME") + std::string("/r2_ws/src/r2_waypoint_loader_cpp/config/waypoints.yaml")),
        rcl_interfaces::msg::ParameterDescriptor{}
            .set__description("获取航点YAML文件的绝对路径"));
    
    // 2. 获取参数值
    this->get_parameter("start_delay", start_delay_);
    this->get_parameter("waypoints_file", waypoints_path_);

    RCLCPP_INFO(this->get_logger(), "参数初始化完成：");
    RCLCPP_INFO(this->get_logger(), "  - 启动延迟：%.1f秒", start_delay_);
    RCLCPP_INFO(this->get_logger(), "  - YAML路径：%s", waypoints_path_.c_str());
}

// 初始化Action客户端、速度发布者等组件
void WaypointLoader::init_components() {
    // 初始化FollowWaypoints Action客户端
    follow_action_client_ = rclcpp_action::create_client<FollowWaypoints>(
        this, "/follow_waypoints");  // 对应Nav2的waypoint_follower动作话题

    RCLCPP_INFO(this->get_logger(), 
        "组件初始化完成：Action客户端、速度发布器、任务执行器已创建");

    // 初始化自定义航点任务插件
    task_plugin_ = std::make_shared<r2_waypoint_loader_cpp::R2WaypointTask>();
    auto weak_ptr = this->get_node_base_interface();  // 获取当前节点的弱指针
    task_plugin_->initialize(
        std::dynamic_pointer_cast<rclcpp_lifecycle::LifecycleNode>(
            this->shared_from_this()),  // 转换为生命周期节点指针
        "r2_waypoint_loader_cpp/R2WaypointTask"  // 插件名称
    );
    RCLCPP_INFO(this->get_logger(), "R2航点任务插件实例创建成功");
}

// 解析YAML文件中的所有航点（主航点+过渡航点）
bool WaypointLoader::parse_all_waypoints_from_yaml() {
    // 打开YAML文件
    std::ifstream yaml_file(waypoints_path_);
    if (!yaml_file.is_open()) {
        RCLCPP_ERROR(this->get_logger(), "无法打开YAML文件：%s", waypoints_path_.c_str());
        return false;
    }

    // 加载YAML根节点
    YAML::Node root;
    try {
        root = YAML::Load(yaml_file);
    } catch (const YAML::Exception& e) {
        RCLCPP_ERROR(this->get_logger(), "YAML解析错误：%s", e.what());
        return false;
    }

    // 读取prepoints（航点ID列表，用于加载所有航点数据，保留此逻辑）
    if (!root["prepoints"]) {
        RCLCPP_ERROR(this->get_logger(), "YAML中缺少prepoints字段（航点ID列表）");
        return false;
    }
    prepoints_ = root["prepoints"].as<std::vector<std::string>>();
    RCLCPP_INFO(this->get_logger(), "读取到%d个航点ID（prepoints）", (int)prepoints_.size());

    // 读取所有航点的位姿数据（主+过渡，保留此逻辑）
    all_wp_map_.clear();  // 清空之前的数据
    for (const auto& wp_id_str : prepoints_) {
        if (!root[wp_id_str]) {
            RCLCPP_WARN(this->get_logger(), "YAML中缺少航点：%s，跳过", wp_id_str.c_str());
            continue;
        }

        // 解析航点位姿
        geometry_msgs::msg::PoseStamped wp;
        try {
            wp.header.frame_id = root[wp_id_str]["header"]["frame_id"].as<std::string>();
            wp.header.stamp = this->get_clock()->now();
            wp.pose.position.x = root[wp_id_str]["pose"]["position"]["x"].as<double>();
            wp.pose.position.y = root[wp_id_str]["pose"]["position"]["y"].as<double>();
            wp.pose.position.z = root[wp_id_str]["pose"]["position"]["z"].as<double>();
            wp.pose.orientation.x = root[wp_id_str]["pose"]["orientation"]["x"].as<double>();
            wp.pose.orientation.y = root[wp_id_str]["pose"]["orientation"]["y"].as<double>();
            wp.pose.orientation.z = root[wp_id_str]["pose"]["orientation"]["z"].as<double>();
            wp.pose.orientation.w = root[wp_id_str]["pose"]["orientation"]["w"].as<double>();

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
                    RCLCPP_DEBUG(this->get_logger(), "航点%s绑定任务：action=%s, height_mm=%d",
                        wp_id_str.c_str(), task_info.action.c_str(), task_info.height_mm);
                } catch (const YAML::Exception& e) {
                    RCLCPP_WARN(this->get_logger(), "解析航点%s的task字段失败：%s", wp_id_str.c_str(), e.what());
                    // 即使 task 解析失败，也不中断整体流程，继续解析其他航点
                    continue;
                }
            }

            all_wp_map_[wp_id_str] = wp;
            RCLCPP_DEBUG(this->get_logger(), "解析航点：%s → (X:%.2f, Y:%.2f)", 
                wp_id_str.c_str(), wp.pose.position.x, wp.pose.position.y);
        } catch (const YAML::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "解析航点%s失败：%s", wp_id_str.c_str(), e.what());
            return false;
        }
    }

    // 读取主航点列表（waypoints字段），并新增main_waypoint_ids_存储ID
    if (!root["waypoints"]) {
        RCLCPP_ERROR(this->get_logger(), "YAML中缺少waypoints字段（主航点ID列表）");
        return false;
    }
    std::vector<int> main_wp_ids = root["waypoints"].as<std::vector<int>>();
    waypoints_.clear();         // 清空主航点位姿列表
    main_waypoint_ids_.clear(); // 清空主航点ID列表

    for (int wp_id : main_wp_ids) {
        std::string wp_id_str = std::to_string(wp_id);
        if (all_wp_map_.count(wp_id_str)) {
            main_waypoint_ids_.push_back(wp_id);  // 只添加waypoints中定义的ID
            waypoints_.push_back(all_wp_map_[wp_id_str]);
        } else {
            RCLCPP_ERROR(this->get_logger(), "主航点ID%d在YAML中不存在！", wp_id);
            return false;
        }

        RCLCPP_INFO(this->get_logger(), "添加主航点：ID%d → (X:%.2f, Y:%.2f)", 
            wp_id, all_wp_map_[wp_id_str].pose.position.x, all_wp_map_[wp_id_str].pose.position.y);
    }

    if (waypoints_.empty()) {
        RCLCPP_ERROR(this->get_logger(), "主航点列表为空，无法启动导航");
        return false;
    }
    RCLCPP_INFO(this->get_logger(), "YAML解析完成：共%d个主航点，%d个总航点", 
        (int)waypoints_.size(), (int)all_wp_map_.size());
    return true;
}


// 判断两个主航点间的关系，匹配过渡点
WaypointLoader::WaypointRelation WaypointLoader::judge_waypoint_relation(int start_id, int end_id) {
    int id_diff = end_id - start_id;

    //左侧以及右侧无法离开梅林限制，直接写出节点id为了增加代码可读性，不建议取模计算
    // 0,3,6,9,12 不能有+1关系（即不能作为start_id且end_id=start_id+1）
    if (id_diff == 1) {
        if (start_id == 0 || start_id == 3 || start_id == 6 || start_id == 9 || start_id == 12) {
            RCLCPP_ERROR(this->get_logger(), "航点%d向左移动掉出梅林，行为禁止", start_id);
            return WaypointRelation::RELATION_ERROR;
        }
    }
    // -2,1,4,7,10 不能有-1关系（即不能作为start_id且end_id=start_id-1）
    else if (id_diff == -1) {
        if (start_id == -2 || start_id == 1 || start_id == 4 || start_id == 7 || start_id == 10) {
            RCLCPP_ERROR(this->get_logger(), "航点%d向右移动掉出梅林，行为禁止", start_id);
            return WaypointRelation::RELATION_ERROR;
        }
    }

    if (id_diff == 3) {
        return WaypointRelation::RELATION_PLUS_3;
    } else if (id_diff == -3) {
        return WaypointRelation::RELATION_MINUS_3;
    } else if (id_diff == 1) {
        return WaypointRelation::RELATION_PLUS_1;
    } else if (id_diff == -1) {
        return WaypointRelation::RELATION_MINUS_1;
    } else {
        RCLCPP_ERROR(this->get_logger(), "航点关系无效：start_id=%d, end_id=%d, 差值=%d", 
            start_id, end_id, id_diff);
        return WaypointRelation::RELATION_ERROR;
    }
}

// 根据主航点关系获取两个过渡点
bool WaypointLoader::get_transition_points(int start_id, int end_id, 
    geometry_msgs::msg::PoseStamped& trans1, geometry_msgs::msg::PoseStamped& trans2) {
    
    // 判断航点关系
    WaypointRelation relation = judge_waypoint_relation(start_id, end_id);
    if (relation == WaypointRelation::RELATION_ERROR) {
        return false;
    }

    // 生成过渡点ID（根据关系匹配_front/_back/_left/_right）
    std::string tp1_id_str, tp2_id_str;
    switch (relation) {
        case WaypointRelation::RELATION_PLUS_3:
            tp1_id_str = std::to_string(start_id) + "_front";
            tp2_id_str = std::to_string(end_id) + "_back";
            break;
        case WaypointRelation::RELATION_MINUS_3:
            tp1_id_str = std::to_string(start_id) + "_back";
            tp2_id_str = std::to_string(end_id) + "_front";
            break;
        case WaypointRelation::RELATION_PLUS_1:
            tp1_id_str = std::to_string(start_id) + "_left";
            tp2_id_str = std::to_string(end_id) + "_right";
            break;
        case WaypointRelation::RELATION_MINUS_1:
            tp1_id_str = std::to_string(start_id) + "_right";
            tp2_id_str = std::to_string(end_id) + "_left";
            break;
        default:
            return false;
    }

    // 从航点地图中获取过渡点位姿
    if (!all_wp_map_.count(tp1_id_str)) {
        RCLCPP_ERROR(this->get_logger(), "过渡点1不存在：%s", tp1_id_str.c_str());
        return false;
    }
    if (!all_wp_map_.count(tp2_id_str)) {
        RCLCPP_ERROR(this->get_logger(), "过渡点2不存在：%s", tp2_id_str.c_str());
        return false;
    }

    trans1 = all_wp_map_[tp1_id_str];
    trans2 = all_wp_map_[tp2_id_str];
    RCLCPP_DEBUG(this->get_logger(), "生成过渡点：%s → %s", 
        tp1_id_str.c_str(), tp2_id_str.c_str());
    return true;
}

// 辅助函数：通过航点索引找到对应的航点ID（如 "-2_front"），效率非常低，未来考虑优化
std::string WaypointLoader::get_wp_id_by_index(uint32_t index) {
    if (index >= full_waypoints_.size()) return "";
    auto& target_pose = full_waypoints_[index].pose;

    // 遍历 all_wp_map_，匹配位姿（x/y/z 误差允许±0.001）
    for (const auto& [wp_id, wp_pose] : all_wp_map_) {
        double x_diff = fabs(wp_pose.pose.position.x - target_pose.position.x);
        double y_diff = fabs(wp_pose.pose.position.y - target_pose.position.y);
        double z_diff = fabs(wp_pose.pose.position.z - target_pose.position.z);
        if (x_diff < 0.001 && y_diff < 0.001 && z_diff < 0.001) {
            return wp_id;
        }
    }
    return "";
}

// 构建完整路径（主航点+过渡点：主→过1→过2→主→...）
bool WaypointLoader::build_full_waypath() {
    full_waypoints_.clear();  // 先清空，避免累积旧数据

    // 主航点数量：由YAML的waypoints字段决定（如[-1,2]则size=2）
    size_t main_count = main_waypoint_ids_.size();
    if (main_count == 0) {
        RCLCPP_ERROR(this->get_logger(), "主航点列表为空，无法构建路径");
        return false;
    }

    RCLCPP_INFO(this->get_logger(), "开始构建路径：共%d个主航点", (int)main_count);

    // 遍历主航点，插入过渡点
    for (size_t i = 0; i < main_count - 1; ++i) {
        // 获取当前主航点与下一个主航点的ID
        // 从main_waypoint_ids_中取当前和下一个主航点的ID
        int start_id = main_waypoint_ids_[i];    // 第i个主航点ID
        int end_id = main_waypoint_ids_[i+1];    // 第i+1个主航点ID
        // int start_id = std::stoi(prepoints_[i]);  // prepoints与waypoints顺序一致
        // int end_id = std::stoi(prepoints_[i+1]);
        geometry_msgs::msg::PoseStamped trans1, trans2;

        // 添加当前主航点
        full_waypoints_.push_back(waypoints_[i]);
        // 获取并添加两个过渡点
        if (!get_transition_points(start_id, end_id, trans1, trans2)) {
            RCLCPP_ERROR(this->get_logger(), "主航点%d→%d的过渡点生成失败，中断路径构建", start_id, end_id);
            full_waypoints_.clear();
            return false;
        }
        full_waypoints_.push_back(trans1);  // 过渡点1（执行Z轴上升）
        full_waypoints_.push_back(trans2);  // 过渡点2（执行延迟2s）
    }

    // 添加最后一个主航点
    full_waypoints_.push_back(waypoints_.back());

    // 若最后一个主航点是10、11、12，即R2准备出梅林，额外添加其_front过渡点负责下降
    int last_main_id = main_waypoint_ids_.back();
    if (last_main_id == 10 || last_main_id == 11 || last_main_id == 12) {
        std::string front_id_str = std::to_string(last_main_id) + "_front";
        if (!all_wp_map_.count(front_id_str)) {
            RCLCPP_ERROR(this->get_logger(), "最后一个主航点%d_front过渡航点不存在：%s", last_main_id, front_id_str.c_str());
            full_waypoints_.clear();
            return false;
        }
        // 添加_front过渡点
        full_waypoints_.push_back(all_wp_map_[front_id_str]);
        RCLCPP_INFO(this->get_logger(), "离开梅林航点%d,执行离开操作过渡航点已添加：%s", last_main_id, front_id_str.c_str());
    }

    // 打印完整路径信息
    RCLCPP_INFO(this->get_logger(), "完整路径构建完成：共%d个航点", (int)full_waypoints_.size());
    for (size_t i = 0; i < full_waypoints_.size(); ++i) {
        RCLCPP_INFO(this->get_logger(), "  航点%d：(X:%.2f, Y:%.2f, 帧ID:%s)",
            (int)i,
            full_waypoints_[i].pose.position.x,
            full_waypoints_[i].pose.position.y,
            full_waypoints_[i].header.frame_id.c_str()
        );
    }
    return true;
}

// 启动延迟定时器回调：开始解析航点并启动导航
void WaypointLoader::on_start_timer() {
    RCLCPP_INFO(this->get_logger(), "启动延迟结束，开始解析航点...");
    
    // 解析YAML并构建完整路径
    if (!parse_all_waypoints_from_yaml() || !build_full_waypath()) {
        RCLCPP_ERROR(this->get_logger(), "航点解析或路径构建失败，无法启动导航");
        return;
    }

    if (!wait_for_nav2_system_ready()) {
        RCLCPP_ERROR(this->get_logger(), "Nav2系统未就绪，导航终止");
        return;
    }

    if (task_plugin_) {
        // 传递航点ID→任务的映射
        task_plugin_->setTaskMap(wp_task_map_);
        // 传递通过索引查询航点ID的函数
        auto get_id_func = std::bind(&WaypointLoader::get_wp_id_by_index, this, std::placeholders::_1);
        task_plugin_->setGetWpIdFunc(get_id_func);
        RCLCPP_INFO(this->get_logger(), "R2航点任务插件数据传递完成（共%d个航点绑定任务）", (int)wp_task_map_.size());
    } else {
        RCLCPP_ERROR(this->get_logger(), "插件实例未创建，无法传递数据");
        return;
    }

    // 等待Action服务器就绪
    if (!wait_for_action_server_with_timeout(std::chrono::seconds(10))) {  // 超时10秒
        RCLCPP_ERROR(this->get_logger(), "未连接到FollowWaypoints Action服务器，导航终止");
        return;
    }

    // 发送导航目标
    send_nav_goal();

    // 取消定时器，防止重复触发
    start_timer_->cancel();  
}

// 等待Nav2系统就绪（地图加载+节点激活）
bool WaypointLoader::wait_for_nav2_system_ready() {
    RCLCPP_INFO(this->get_logger(), "等待Nav2系统就绪...");

    // 等待地图加载（订阅/map_metadata话题）
    bool map_loaded = false;
    auto map_sub = this->create_subscription<nav_msgs::msg::MapMetaData>(
        "/map_metadata", 10,
        [&map_loaded](const nav_msgs::msg::MapMetaData::SharedPtr) {
            map_loaded = true;
        }
    );

    // 等待核心节点激活
    auto check_node_active = [this](const std::string& node_name) {
        auto client = this->create_client<lifecycle_msgs::srv::GetState>(node_name + "/get_state");
        if (!client->wait_for_service(1s)) return false;
        auto req = std::make_shared<lifecycle_msgs::srv::GetState::Request>();
        auto future = client->async_send_request(req);
        if (rclcpp::spin_until_future_complete(this->get_node_base_interface(), future, 1s) 
            != rclcpp::FutureReturnCode::SUCCESS) return false;
        return future.get()->current_state.id == lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE;
    };

    // 超时时间：30秒
    auto start_time = this->now();
    while (rclcpp::ok() && (this->now() - start_time < rclcpp::Duration(30s))) {
        bool nodes_active = check_node_active("/controller_server") 
                         && check_node_active("/planner_server")
                         && check_node_active("/bt_navigator");

        if (map_loaded && nodes_active) {
            RCLCPP_INFO(this->get_logger(), "Nav2系统已就绪");
            return true;
        }

        RCLCPP_INFO(this->get_logger(), "等待中... 地图:%s, 节点:%s",
            map_loaded ? "已加载" : "未加载",
            nodes_active ? "已激活" : "未激活");
        rclcpp::sleep_for(1s);
    }

    RCLCPP_ERROR(this->get_logger(), "等待Nav2系统超时（30秒）");
    return false;
}


// 等待Action服务器（带超时）
bool WaypointLoader::wait_for_action_server_with_timeout(const std::chrono::seconds& timeout) {
    auto start_time = std::chrono::steady_clock::now();
    while (!follow_action_client_->wait_for_action_server(1s)) {
        if (std::chrono::steady_clock::now() - start_time > timeout) {
            return false;
        }
        RCLCPP_INFO(this->get_logger(), "等待FollowWaypoints Action服务器（剩余%.1f秒）...",
            std::chrono::duration<double>(timeout - (std::chrono::steady_clock::now() - start_time)).count());
    }
    RCLCPP_INFO(this->get_logger(), "已连接到FollowWaypoints Action服务器");
    return true;
}

// 发送完整路径导航目标
void WaypointLoader::send_nav_goal() {
    if (full_waypoints_.empty()) {
        RCLCPP_ERROR(this->get_logger(), "完整路径为空，无法发送导航目标");
        return;
    }

    // 构建导航目标消息
    auto goal_msg = FollowWaypoints::Goal();
    goal_msg.poses = full_waypoints_;  // 完整路径（主航点+过渡点）

    // 配置Action回调
    auto send_goal_options = rclcpp_action::Client<FollowWaypoints>::SendGoalOptions();
    send_goal_options.goal_response_callback =
        std::bind(&WaypointLoader::goal_response_callback, this, std::placeholders::_1);
    send_goal_options.feedback_callback =
        std::bind(&WaypointLoader::feedback_callback, this, std::placeholders::_1, std::placeholders::_2);
    send_goal_options.result_callback =
        std::bind(&WaypointLoader::result_callback, this, std::placeholders::_1);

    // 发送目标
    follow_action_client_->async_send_goal(goal_msg, send_goal_options);
    RCLCPP_INFO(this->get_logger(), "已发送导航目标，共%d个航点", (int)full_waypoints_.size());
}

// Action目标响应回调
void WaypointLoader::goal_response_callback(const GoalHandleFollow::SharedPtr& goal_handle) {
    if (!goal_handle) {
        RCLCPP_ERROR(this->get_logger(), "导航目标被服务器拒绝");
    } else {
        RCLCPP_INFO(this->get_logger(), "导航目标已被服务器接受，开始导航...");
    }
}

// Action反馈回调（实时获取已完成的航点）
void WaypointLoader::feedback_callback(GoalHandleFollow::SharedPtr,
    const std::shared_ptr<const FollowWaypoints::Feedback> feedback) {
    std::lock_guard<std::mutex> lock(waypoint_mutex_);

    // current_waypoint 是当前正在执行的航点索引（从0开始）
    uint32_t current_idx = feedback->current_waypoint;
    if (current_idx == last_processed_waypoint_) {
        return; // 过滤重复反馈
    }
    // 仅在索引变化时输出日志（避免重复刷屏）
    else {
        // 输出当前开始执行的航点信息
        RCLCPP_INFO(this->get_logger(), "开始执行航点%d（共%d个）",
            current_idx, (int)full_waypoints_.size());
        
        // 记录最后一次报告的索引
        last_processed_waypoint_ = current_idx;
    }
}

// Action结果回调（导航完成/失败）
void WaypointLoader::result_callback(const GoalHandleFollow::WrappedResult& result) {
    switch (result.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
            if (result.result->missed_waypoints.empty()) {
                RCLCPP_INFO(this->get_logger(), "导航成功完成！所有航点均到达");
            } else {
                RCLCPP_WARN(this->get_logger(), "导航完成，但有 %zu 个航点未到达",
                           result.result->missed_waypoints.size());
                for (const auto& missed_idx : result.result->missed_waypoints) {
                    RCLCPP_WARN(this->get_logger(), "未到达航点索引：%u", missed_idx);
                }
            }
            break;
        case rclcpp_action::ResultCode::ABORTED:
            RCLCPP_ERROR(this->get_logger(), "导航被中止！");
            break;
        case rclcpp_action::ResultCode::CANCELED:
            RCLCPP_WARN(this->get_logger(), "导航被取消！");
            break;
        default:
            RCLCPP_ERROR(this->get_logger(), "导航结果未知（错误码：%d）", (int)result.code);
            break;
    }

    // 重置状态
    // std::lock_guard<std::mutex> lock(waypoint_mutex_);
}

// 未使用函数实现
void WaypointLoader::execute_post_waypoint_actions(int current_wp) {
    (void)current_wp;  
}

// 添加标准main函数
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<r2_waypoint_loader_cpp::WaypointLoader>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}