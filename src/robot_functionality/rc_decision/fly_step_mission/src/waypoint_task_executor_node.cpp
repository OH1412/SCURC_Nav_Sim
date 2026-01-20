#include "fly_step_mission/waypoint_task_executor_node.hpp"
#include <cmath>
#include <iostream>

namespace fly_step_mission
{

WaypointTaskExecutorNode::WaypointTaskExecutorNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node
) : BT::SyncActionNode(name, config), node_(node)
{
    RCLCPP_INFO(node_->get_logger(), "WaypointTaskExecutorNode initialized");
}

BT::PortsList WaypointTaskExecutorNode::providedPorts()
{
    return {
        BT::InputPort<std::string>("current_waypoint_id", "Current waypoint ID to check for tasks"),
        BT::InputPort<std::map<std::string, WaypointTaskInfo>>("waypoint_task_map", "Map of waypoint IDs to tasks"),
        BT::OutputPort<bool>("task_executed", "Whether a task was executed at this waypoint"),
        BT::OutputPort<std::string>("task_type", "Type of task executed ('ascend', 'delayed_descend', 'none')"),
        BT::OutputPort<bool>("requires_next_waypoint_task", "Whether a task should be executed at the next waypoint"),
        BT::OutputPort<std::string>("next_waypoint_task_type", "Type of task to execute at next waypoint")
    };
}

BT::NodeStatus WaypointTaskExecutorNode::tick()
{
    RCLCPP_INFO(node_->get_logger(), "Starting WaypointTaskExecutorNode...");

    // 获取当前航点ID
    std::string current_waypoint_id;
    if (!getInput("current_waypoint_id", current_waypoint_id)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to get 'current_waypoint_id' input");
        return BT::NodeStatus::FAILURE;
    }

    // 获取航点任务映射
    if (!getInput("waypoint_task_map", wp_task_map_)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to get 'waypoint_task_map' input");
        return BT::NodeStatus::FAILURE;
    }

    // 检查当前航点是否有任务
    bool task_executed = false;
    std::string task_type = "none";
    bool requires_next_waypoint_task = false;
    std::string next_waypoint_task_type = "none";

    if (wp_task_map_.find(current_waypoint_id) != wp_task_map_.end()) {
        WaypointTaskInfo task_info = wp_task_map_[current_waypoint_id];
        RCLCPP_INFO(node_->get_logger(), "Found task for waypoint %s: action=%s, height=%d mm", 
                   current_waypoint_id.c_str(), task_info.action.c_str(), task_info.height_mm);

        // 设置任务类型
        task_type = task_info.action;

        // 根据任务类型设置输出参数到黑板，供后续的AscendNode或DescendNode使用
        double height_meters = task_info.height_mm / 1000.0; // 转换毫米到米
        
        // 从黑板获取TF缓冲区以获取当前Z值
        double current_z = 0.0;
        try {
            auto tf_buffer = config().blackboard->get<std::shared_ptr<tf2_ros::Buffer>>("tf_buffer");
            if (tf_buffer) {
                auto transform = tf_buffer->lookupTransform("map", "base_link", tf2::TimePointZero);
                current_z = transform.transform.translation.z;
            } else {
                RCLCPP_WARN(node_->get_logger(), "Could not get tf_buffer from blackboard, using default value 0.0");
            }
        } catch (const tf2::TransformException &ex) {
            // 如果无法获取当前Z值，则使用默认值
            RCLCPP_WARN(node_->get_logger(), "Could not get current Z from TF: %s, using default value 0.0", ex.what());
        }
        
        if (task_info.action == "ascend") {
            // 为AscendNode设置参数 - 立即执行
            double target_z = current_z + height_meters;
            
            // 将目标高度等参数存储到黑板中，供后续节点使用
            config().blackboard->set("target_ascend_height", target_z);
            config().blackboard->set("ascend_speed", 0.5); // 默认上升速度
            config().blackboard->set("ascend_max_duration", 10.0); // 默认最大持续时间
            
            RCLCPP_INFO(node_->get_logger(), "Prepared immediate ascend task: current_z=%.3f m, target height=%.3f m", current_z, target_z);
            
            task_executed = true;
        } 
        else if (task_info.action == "delayed_descend") {
            // 为延迟下降设置参数 - 不立即执行，而是标记下一个航点需要执行下降
            double target_z = current_z - height_meters;
            
            // 将目标高度等参数存储到黑板中，供后续节点使用
            config().blackboard->set("target_descend_height", target_z);
            config().blackboard->set("descend_speed", 0.5); // 默认下降速度
            config().blackboard->set("descend_max_duration", 10.0); // 默认最大持续时间
            
            RCLCPP_INFO(node_->get_logger(), "Prepared delayed descend task: current_z=%.3f m, target height=%.3f m", current_z, target_z);
            
            // 标记下一个航点需要执行下降任务
            requires_next_waypoint_task = true;
            next_waypoint_task_type = "descend";
        }
        
    } else {
        RCLCPP_INFO(node_->get_logger(), "No task found for waypoint %s", current_waypoint_id.c_str());
    }

    // 设置输出
    if (!setOutput("task_executed", task_executed)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'task_executed' output");
        return BT::NodeStatus::FAILURE;
    }
    
    if (!setOutput("task_type", task_type)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'task_type' output");
        return BT::NodeStatus::FAILURE;
    }
    
    if (!setOutput("requires_next_waypoint_task", requires_next_waypoint_task)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'requires_next_waypoint_task' output");
        return BT::NodeStatus::FAILURE;
    }
    
    if (!setOutput("next_waypoint_task_type", next_waypoint_task_type)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'next_waypoint_task_type' output");
        return BT::NodeStatus::FAILURE;
    }

    RCLCPP_INFO(node_->get_logger(), "WaypointTaskExecutorNode completed: task_executed=%s, task_type=%s, requires_next_waypoint_task=%s, next_waypoint_task_type=%s", 
               task_executed ? "true" : "false", task_type.c_str(), requires_next_waypoint_task ? "true" : "false", next_waypoint_task_type.c_str());

    return BT::NodeStatus::SUCCESS;
}

} // namespace fly_step_mission