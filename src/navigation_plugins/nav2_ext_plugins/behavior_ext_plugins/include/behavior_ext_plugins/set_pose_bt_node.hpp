// Copyright (c) 2026
//
// SetPoseStamped BT Sync Action Node
// 将 x, y, z, yaw 参数打包为 PoseStamped 写入黑board
//

#ifndef BEHAVIOR_EXT_PLUGINS__SET_POSE_BT_NODE_HPP_
#define BEHAVIOR_EXT_PLUGINS__SET_POSE_BT_NODE_HPP_

#include <string>
#include <cmath>

#include "behaviortree_cpp_v3/action_node.h"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "rclcpp/rclcpp.hpp"

namespace behavior_ext_plugins
{

class SetPoseStamped : public BT::SyncActionNode
{
public:
  SetPoseStamped(const std::string & name, const BT::NodeConfiguration & config)
  : BT::SyncActionNode(name, config)
  {
  }

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<double>("x", 0.0, "X (m, map frame)"),
      BT::InputPort<double>("y", 0.0, "Y (m, map frame)"),
      BT::InputPort<double>("z", 0.0, "Z (m, map frame)"),
      BT::InputPort<double>("yaw", 0.0, "Yaw (rad)"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("pose", "PoseStamped output"),
    };
  }

  BT::NodeStatus tick() override
  {
    const double x = getInput<double>("x").value_or(0.0);
    const double y = getInput<double>("y").value_or(0.0);
    const double z = getInput<double>("z").value_or(0.0);
    const double yaw = getInput<double>("yaw").value_or(0.0);

    geometry_msgs::msg::PoseStamped pose;
    pose.header.frame_id = "map";
    pose.header.stamp = rclcpp::Clock().now();
    pose.pose.position.x = x;
    pose.pose.position.y = y;
    pose.pose.position.z = z;
    pose.pose.orientation.z = std::sin(yaw / 2.0);
    pose.pose.orientation.w = std::cos(yaw / 2.0);

    setOutput("pose", pose);

    RCLCPP_INFO(rclcpp::get_logger("SetPoseStamped"),
      "Set pose: map(%.3f, %.3f, %.3f), yaw=%.3f",
      x, y, z, yaw);

    return BT::NodeStatus::SUCCESS;
  }
};

}  // namespace behavior_ext_plugins

#endif  // BEHAVIOR_EXT_PLUGINS__SET_POSE_BT_NODE_HPP_
