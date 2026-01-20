#include "fly_step_mission/path_generator_node.hpp"
#include "fly_step_mission/bt_type_conversions.hpp"
#include <cmath>
#include <iostream>

namespace fly_step_mission
{

PathGeneratorNode::PathGeneratorNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node
) : BT::SyncActionNode(name, config), node_(node)
{
    // 从配置中获取航点文件路径
    if (!getInput("waypoints_file", waypoints_file_)) {
        // 默认路径
        waypoints_file_ = std::string(getenv("HOME")) + "/r2_ws/src/r2_waypoint_loader_cpp/config/waypoints.yaml";
        RCLCPP_WARN(node_->get_logger(), "Parameter 'waypoints_file' not found, using default: %s", waypoints_file_.c_str());
    }
    
    RCLCPP_INFO(node_->get_logger(), "PathGeneratorNode initialized with waypoints file: %s", waypoints_file_.c_str());
}

BT::PortsList PathGeneratorNode::providedPorts()
{
    return {
        BT::InputPort<std::vector<int>>("main_waypoints", "Main waypoint IDs to generate path for"),
        BT::InputPort<std::string>("waypoints_file", "Path to waypoints YAML file")
        // 注意：generated_path 和 waypoint_task_map 通过黑板直接存储，不作为端口
    };
}

BT::NodeStatus PathGeneratorNode::tick()
{
    RCLCPP_INFO(node_->get_logger(), "Starting PathGeneratorNode...");

    // 获取输入的主航点ID列表
    std::vector<int> main_waypoints;
    if (!getInput("main_waypoints", main_waypoints)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to get 'main_waypoints' input");
        return BT::NodeStatus::FAILURE;
    }

    // 先设置主航点ID（parseAllWaypointsFromYaml 会用到）
    main_waypoint_ids_ = main_waypoints;
    
    RCLCPP_INFO(node_->get_logger(), "Main waypoints count: %zu", main_waypoint_ids_.size());
    
    // 调试：打印每个主航点ID
    for (size_t i = 0; i < main_waypoint_ids_.size(); ++i) {
        RCLCPP_INFO(node_->get_logger(), "  Main waypoint[%zu] = %d", i, main_waypoint_ids_[i]);
    }

    // 解析YAML文件
    if (!parseAllWaypointsFromYaml()) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to parse waypoints from YAML file");
        return BT::NodeStatus::FAILURE;
    }

    // 构建完整路径
    if (!buildFullWaypath()) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to build full waypoint path");
        return BT::NodeStatus::FAILURE;
    }

    // 通过黑板存储生成的路径和任务映射（复杂类型不能通过端口传递）
    config().blackboard->set("generated_path", full_waypoints_);
    config().blackboard->set("waypoint_task_map", wp_task_map_);
    // 同时存储航点ID到索引的映射，方便后续查找
    config().blackboard->set("all_wp_map", all_wp_map_);

    RCLCPP_INFO(node_->get_logger(), "Successfully generated path with %zu waypoints", full_waypoints_.size());
    RCLCPP_INFO(node_->get_logger(), "Found %zu waypoints with tasks", wp_task_map_.size());

    return BT::NodeStatus::SUCCESS;
}

bool PathGeneratorNode::parseAllWaypointsFromYaml()
{
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

    // 读取prepoints（航点ID列表）
    if (!root["prepoints"]) {
        RCLCPP_ERROR(node_->get_logger(), "YAML中缺少prepoints字段（航点ID列表）");
        return false;
    }
    
    // 清空之前的数据
    all_wp_map_.clear();
    wp_task_map_.clear();
    
    // 获取所有航点ID
    prepoints_ = root["prepoints"].as<std::vector<std::string>>();
    RCLCPP_INFO(node_->get_logger(), "读取到%d个航点ID（prepoints）", (int)prepoints_.size());

    // 读取所有航点的位姿数据（主+过渡）
    for (const auto& wp_id_str : prepoints_) {
        if (!root[wp_id_str]) {
            RCLCPP_WARN(node_->get_logger(), "YAML中缺少航点：%s，跳过", wp_id_str.c_str());
            continue;
        }

        // 解析航点位姿
        geometry_msgs::msg::PoseStamped wp;
        try {
            wp.header.frame_id = root[wp_id_str]["header"]["frame_id"].as<std::string>();
            wp.header.stamp = node_->get_clock()->now();
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
                    RCLCPP_DEBUG(node_->get_logger(), "航点%s绑定任务：action=%s, height_mm=%d",
                        wp_id_str.c_str(), task_info.action.c_str(), task_info.height_mm);
                } catch (const YAML::Exception& e) {
                    RCLCPP_WARN(node_->get_logger(), "解析航点%s的task字段失败：%s", wp_id_str.c_str(), e.what());
                    // 即使 task 解析失败，也不中断整体流程，继续解析其他航点
                    continue;
                }
            }

            all_wp_map_[wp_id_str] = wp;
            RCLCPP_INFO(node_->get_logger(), "解析航点：%s → (X:%.3f, Y:%.3f)", 
                wp_id_str.c_str(), wp.pose.position.x, wp.pose.position.y);
        } catch (const YAML::Exception& e) {
            RCLCPP_ERROR(node_->get_logger(), "解析航点%s失败：%s", wp_id_str.c_str(), e.what());
            return false;
        }
    }

    // 从预定义的prepoints中提取主航点数据
    waypoints_.clear();
    for (int wp_id : main_waypoint_ids_) {
        std::string wp_id_str = std::to_string(wp_id);
        if (all_wp_map_.count(wp_id_str)) {
            waypoints_.push_back(all_wp_map_[wp_id_str]);
        } else {
            RCLCPP_ERROR(node_->get_logger(), "主航点ID%d在YAML中不存在！", wp_id);
            return false;
        }

        RCLCPP_INFO(node_->get_logger(), "添加主航点：ID%d → (X:%.2f, Y:%.2f)", 
            wp_id, all_wp_map_[wp_id_str].pose.position.x, all_wp_map_[wp_id_str].pose.position.y);
    }

    if (waypoints_.empty()) {
        RCLCPP_ERROR(node_->get_logger(), "主航点列表为空，无法启动导航");
        return false;
    }
    
    RCLCPP_INFO(node_->get_logger(), "YAML解析完成：共%d个主航点，%d个总航点", 
        (int)waypoints_.size(), (int)all_wp_map_.size());
    return true;
}

WaypointRelation PathGeneratorNode::judgeWaypointRelation(int start_id, int end_id) {
    int id_diff = end_id - start_id;

    // 左侧以及右侧无法离开梅林限制，直接写出节点id为了增加代码可读性，不建议取模计算
    // 0,3,6,9,12 不能有+1关系（即不能作为start_id且end_id=start_id+1）
    if (id_diff == 1) {
        if (start_id == 0 || start_id == 3 || start_id == 6 || start_id == 9 || start_id == 12) {
            RCLCPP_ERROR(node_->get_logger(), "航点%d向左移动掉出梅林，行为禁止", start_id);
            return WaypointRelation::RELATION_ERROR;
        }
    }
    // -2,1,4,7,10 不能有-1关系（即不能作为start_id且end_id=start_id-1）
    else if (id_diff == -1) {
        if (start_id == -2 || start_id == 1 || start_id == 4 || start_id == 7 || start_id == 10) {
            RCLCPP_ERROR(node_->get_logger(), "航点%d向右移动掉出梅林，行为禁止", start_id);
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
        RCLCPP_ERROR(node_->get_logger(), "航点关系无效：start_id=%d, end_id=%d, 差值=%d", 
            start_id, end_id, id_diff);
        return WaypointRelation::RELATION_ERROR;
    }
}

bool PathGeneratorNode::getTransitionPoints(int start_id, int end_id, 
    geometry_msgs::msg::PoseStamped& trans1, geometry_msgs::msg::PoseStamped& trans2) {
    
    // 判断航点关系
    WaypointRelation relation = judgeWaypointRelation(start_id, end_id);
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
        RCLCPP_ERROR(node_->get_logger(), "过渡点1不存在：%s", tp1_id_str.c_str());
        return false;
    }
    if (!all_wp_map_.count(tp2_id_str)) {
        RCLCPP_ERROR(node_->get_logger(), "过渡点2不存在：%s", tp2_id_str.c_str());
        return false;
    }

    trans1 = all_wp_map_[tp1_id_str];
    trans2 = all_wp_map_[tp2_id_str];
    RCLCPP_DEBUG(node_->get_logger(), "生成过渡点：%s → %s", 
        tp1_id_str.c_str(), tp2_id_str.c_str());
    return true;
}

bool PathGeneratorNode::buildFullWaypath() {
    full_waypoints_.clear();  // 先清空，避免累积旧数据

    // 主航点数量：由传入的main_waypoint_ids_决定
    size_t main_count = main_waypoint_ids_.size();
    if (main_count == 0) {
        RCLCPP_ERROR(node_->get_logger(), "主航点列表为空，无法构建路径");
        return false;
    }

    RCLCPP_INFO(node_->get_logger(), "开始构建路径：共%d个主航点", (int)main_count);

    // 遍历主航点，插入过渡点
    for (size_t i = 0; i < main_count - 1; ++i) {
        // 获取当前主航点与下一个主航点的ID
        int start_id = main_waypoint_ids_[i];    // 第i个主航点ID
        int end_id = main_waypoint_ids_[i+1];    // 第i+1个主航点ID
        geometry_msgs::msg::PoseStamped trans1, trans2;

        // 添加当前主航点
        full_waypoints_.push_back(waypoints_[i]);
        
        // 获取并添加两个过渡点
        if (!getTransitionPoints(start_id, end_id, trans1, trans2)) {
            RCLCPP_ERROR(node_->get_logger(), "主航点%d→%d的过渡点生成失败，中断路径构建", start_id, end_id);
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
            RCLCPP_ERROR(node_->get_logger(), "最后一个主航点%d_front过渡航点不存在：%s", last_main_id, front_id_str.c_str());
            full_waypoints_.clear();
            return false;
        }
        // 添加_front过渡点
        full_waypoints_.push_back(all_wp_map_[front_id_str]);
        RCLCPP_INFO(node_->get_logger(), "离开梅林航点%d,执行离开操作过渡航点已添加：%s", last_main_id, front_id_str.c_str());
    }

    // 打印完整路径信息
    RCLCPP_INFO(node_->get_logger(), "完整路径构建完成：共%d个航点", (int)full_waypoints_.size());
    for (size_t i = 0; i < full_waypoints_.size(); ++i) {
        RCLCPP_INFO(node_->get_logger(), "  航点%d：(X:%.2f, Y:%.2f, 帧ID:%s)",
            (int)i,
            full_waypoints_[i].pose.position.x,
            full_waypoints_[i].pose.position.y,
            full_waypoints_[i].header.frame_id.c_str()
        );
    }
    return true;
}

} // namespace fly_step_mission