#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

class Nav2PoseNode : public BT::StatefulActionNode
{
public:
  using NavigateToPose = nav2_msgs::action::NavigateToPose;
  using GoalHandle     = rclcpp_action::ClientGoalHandle<NavigateToPose>;

  Nav2PoseNode(const std::string & name,
               const BT::NodeConfiguration & config,
               std::shared_ptr<rclcpp::Node> node);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  bool ensureClient();

  geometry_msgs::msg::PoseStamped makePose(
    const std::string & frame_id,
    double x, double y, double yaw);

  std::shared_ptr<rclcpp::Node> node_;
  rclcpp_action::Client<NavigateToPose>::SharedPtr client_;

  GoalHandle::SharedPtr      goal_handle_;
  GoalHandle::WrappedResult  result_;
  bool goal_sent_{false};
  bool result_ready_{false};
};