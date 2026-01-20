#pragma once

#include <memory>
#include <string>
#include <vector>
#include <map>
#include <functional>

#include <behaviortree_cpp_v3/action_node.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

#include "fly_step_mission/waypoint_mission_node.hpp"

namespace fly_step_mission
{

/**
 * @brief 延迟任务执行节点
 * 检查是否需要在当前航点执行之前标记的延迟任务（如delayed_descend）
 */
class DelayedTaskExecutorNode : public BT::SyncActionNode
{
public:
    DelayedTaskExecutorNode(
        const std::string & name,
        const BT::NodeConfiguration & config,
        std::shared_ptr<rclcpp::Node> node
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus tick() override;

private:
    std::shared_ptr<rclcpp::Node> node_;
};

} // namespace fly_step_mission