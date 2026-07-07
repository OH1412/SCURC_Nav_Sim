#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <legged_mission_bt/msg/nav_reached.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include "legged_mission_bt/waypoint_registry.hpp"

class Nav2PoseNode : public BT::StatefulActionNode
{
public:
  using NavigateToPose = nav2_msgs::action::NavigateToPose;
  using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;

  Nav2PoseNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node,
    std::shared_ptr<legged_mission_bt::WaypointRegistry> registry);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  bool ensureClient();
  bool resolveGoal(std::string & frame_id, double & x, double & y, double & yaw);
  bool sendGoal(const std::string & frame_id, double x, double y, double yaw);
  void publishNavReached(const std::string & nav_id);
  void resetNavProgressLogSchedule();
  void maybeLogNavProgress();
  bool getCurrentStateInGoalFrame(
    double & x, double & y, double & yaw, double & vx, double & vy, double & wz) const;

  geometry_msgs::msg::PoseStamped makePose(
    const std::string & frame_id,
    double x, double y, double yaw);

  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry_;
  rclcpp_action::Client<NavigateToPose>::SharedPtr client_;
  rclcpp::Publisher<legged_mission_bt::msg::NavReached>::SharedPtr nav_reached_pub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  nav_msgs::msg::Odometry::SharedPtr latest_odom_;

  std::string odom_topic_{"/state_estimation"};
  std::string base_frame_{"base_link"};
  double nav_progress_log_interval_{5.0};
  rclcpp::Time nav_progress_start_;
  rclcpp::Time next_progress_log_time_;

  std::string resolved_nav_id_;
  std::string resolved_frame_id_;
  double resolved_x_{0.0};
  double resolved_y_{0.0};
  double resolved_yaw_{0.0};

  GoalHandle::SharedPtr goal_handle_;
  GoalHandle::WrappedResult result_;
  bool goal_sent_{false};
  bool result_ready_{false};
  bool waiting_for_wp_{false};
  std::string wp_id_;
  rclcpp::Time resolve_start_;
  double waypoint_wait_timeout_{120.0};
};
