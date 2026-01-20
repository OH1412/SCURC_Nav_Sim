#include "fly_step_mission/delayed_task_executor_node.hpp"
#include <cmath>
#include <iostream>

namespace fly_step_mission
{

DelayedTaskExecutorNode::DelayedTaskExecutorNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node
) : BT::SyncActionNode(name, config), node_(node)
{
    RCLCPP_INFO(node_->get_logger(), "DelayedTaskExecutorNode initialized");
}

BT::PortsList DelayedTaskExecutorNode::providedPorts()
{
    return {
        BT::InputPort<bool>("requires_next_waypoint_task", "Whether a task should be executed at this waypoint"),
        BT::InputPort<std::string>("next_waypoint_task_type", "Type of task to execute at this waypoint"),
        BT::OutputPort<bool>("executed_delayed_task", "Whether a delayed task was executed at this waypoint"),
        BT::OutputPort<std::string>("executed_task_type", "Type of executed task ('ascend', 'descend', 'none')")
    };
}

BT::NodeStatus DelayedTaskExecutorNode::tick()
{
    RCLCPP_INFO(node_->get_logger(), "Starting DelayedTaskExecutorNode...");

    // 获取是否需要执行延迟任务的标志
    bool requires_next_waypoint_task = false;
    if (!getInput("requires_next_waypoint_task", requires_next_waypoint_task)) {
        RCLCPP_WARN(node_->get_logger(), "Failed to get 'requires_next_waypoint_task' input, assuming false");
        requires_next_waypoint_task = false;
    }

    // 获取要执行的任务类型
    std::string next_waypoint_task_type = "none";
    if (!getInput("next_waypoint_task_type", next_waypoint_task_type)) {
        RCLCPP_WARN(node_->get_logger(), "Failed to get 'next_waypoint_task_type' input, assuming 'none'");
        next_waypoint_task_type = "none";
    }

    bool executed_delayed_task = false;
    std::string executed_task_type = "none";

    if (requires_next_waypoint_task && next_waypoint_task_type != "none") {
        RCLCPP_INFO(node_->get_logger(), "Executing delayed task: %s", next_waypoint_task_type.c_str());
        
        // 根据任务类型执行相应的操作
        if (next_waypoint_task_type == "descend") {
            // 准备下降任务参数，供DescendNode使用
            // 从黑板获取之前设置的目标高度和其他参数
            try {
                double target_descend_height = config().blackboard->get<double>("target_descend_height");
                double descend_speed = config().blackboard->get<double>("descend_speed");
                double descend_max_duration = config().blackboard->get<double>("descend_max_duration");
                
                // 将参数设置为可供DescendNode使用的格式
                config().blackboard->set("target_descend_height", target_descend_height);
                config().blackboard->set("descend_speed", descend_speed);
                config().blackboard->set("descend_max_duration", descend_max_duration);
                
                executed_delayed_task = true;
                executed_task_type = "descend";
                
                RCLCPP_INFO(node_->get_logger(), "Prepared delayed descend task: target height=%.3f m", target_descend_height);
            } catch (...) {
                RCLCPP_ERROR(node_->get_logger(), "Failed to get required parameters for delayed descend task from blackboard");
            }
        }
        
    } else {
        RCLCPP_INFO(node_->get_logger(), "No delayed task to execute at this waypoint");
    }

    // 设置输出
    if (!setOutput("executed_delayed_task", executed_delayed_task)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'executed_delayed_task' output");
        return BT::NodeStatus::FAILURE;
    }
    
    if (!setOutput("executed_task_type", executed_task_type)) {
        RCLCPP_ERROR(node_->get_logger(), "Failed to set 'executed_task_type' output");
        return BT::NodeStatus::FAILURE;
    }

    RCLCPP_INFO(node_->get_logger(), "DelayedTaskExecutorNode completed: executed_delayed_task=%s, executed_task_type=%s", 
               executed_delayed_task ? "true" : "false", executed_task_type.c_str());

    return BT::NodeStatus::SUCCESS;
}

} // namespace fly_step_mission