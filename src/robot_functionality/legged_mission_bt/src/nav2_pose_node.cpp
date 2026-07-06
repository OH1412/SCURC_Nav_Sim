#include "legged_mission_bt/nav2_pose_node.hpp"

#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

using namespace std::chrono_literals;

Nav2PoseNode::Nav2PoseNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node,
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry)
: BT::StatefulActionNode(name, config),
  node_(std::move(node)),
  registry_(std::move(registry))
{
  if (!node_->has_parameter("waypoint_wait_timeout")) {
    node_->declare_parameter("waypoint_wait_timeout", 120.0);
  }
  waypoint_wait_timeout_ = node_->get_parameter("waypoint_wait_timeout").as_double();
  if (!node_->has_parameter("nav_reached_topic")) {
    node_->declare_parameter("nav_reached_topic", "/mission_bt/nav_reached");
  }
  const auto nav_reached_topic = node_->get_parameter("nav_reached_topic").as_string();
  nav_reached_pub_ = node_->create_publisher<legged_mission_bt::msg::NavReached>(
    nav_reached_topic, rclcpp::QoS(rclcpp::KeepLast(10)).reliable());
  client_ = rclcpp_action::create_client<NavigateToPose>(node_, "navigate_to_pose");
}

BT::PortsList Nav2PoseNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("wp_id", "", "Nav waypoint id (from external topic or YAML seed)"),
    BT::InputPort<std::string>("frame_id", "map", "Goal frame (inline mode)"),
    BT::InputPort<double>("x", "Goal X (inline mode)"),
    BT::InputPort<double>("y", "Goal Y (inline mode)"),
    BT::InputPort<double>("yaw", 0.0, "Yaw in radians (inline mode)"),
  };
}

bool Nav2PoseNode::ensureClient()
{
  if (!client_) {
    return false;
  }
  if (!client_->action_server_is_ready()) {
    RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: waiting for navigate_to_pose (up to 60s)...");
    if (!client_->wait_for_action_server(60s)) {
      RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: navigate_to_pose not available after 60s");
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: navigate_to_pose ready");
  }
  return true;
}

geometry_msgs::msg::PoseStamped Nav2PoseNode::makePose(
  const std::string & frame_id, double x, double y, double yaw)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = frame_id;
  pose.header.stamp = node_->now();
  pose.pose.position.x = x;
  pose.pose.position.y = y;
  pose.pose.position.z = 0.0;

  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, yaw);
  pose.pose.orientation = tf2::toMsg(q);
  return pose;
}

bool Nav2PoseNode::resolveGoal(std::string & frame_id, double & x, double & y, double & yaw)
{
  getInput("wp_id", wp_id_);

  if (!wp_id_.empty()) {
    legged_mission_bt::NavWaypoint wp;
    if (registry_ && registry_->tryGetNav(wp_id_, wp)) {
      frame_id = wp.frame_id;
      x = wp.x;
      y = wp.y;
      yaw = wp.yaw;
      resolved_nav_id_ = wp_id_;
      resolved_frame_id_ = frame_id;
      resolved_x_ = x;
      resolved_y_ = y;
      resolved_yaw_ = yaw;
      RCLCPP_INFO(
        node_->get_logger(),
        "Nav2PoseNode: resolved wp_id='%s' → frame=%s (%.3f, %.3f, yaw=%.3f)",
        wp_id_.c_str(), frame_id.c_str(), x, y, yaw);
      return true;
    }
    return false;
  }

  if (!getInput("x", x) || !getInput("y", y)) {
    RCLCPP_ERROR(
      node_->get_logger(),
      "Nav2PoseNode: provide wp_id or inline x/y");
    return false;
  }
  getInput("frame_id", frame_id);
  getInput("yaw", yaw);
  resolved_nav_id_ = wp_id_;
  resolved_frame_id_ = frame_id;
  resolved_x_ = x;
  resolved_y_ = y;
  resolved_yaw_ = yaw;
  return true;
}

void Nav2PoseNode::publishNavReached(const std::string & nav_id)
{
  legged_mission_bt::msg::NavReached msg;
  msg.nav_id = nav_id;
  nav_reached_pub_->publish(msg);
}

bool Nav2PoseNode::sendGoal(const std::string & frame_id, double x, double y, double yaw)
{
  NavigateToPose::Goal goal;
  goal.pose = makePose(frame_id, x, y, yaw);

  goal_sent_ = false;
  result_ready_ = false;

  auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};
  send_goal_options.result_callback =
    [this](const GoalHandle::WrappedResult & result) {
      result_ = result;
      result_ready_ = true;
    };

  RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: sending goal (%.3f, %.3f, yaw=%.3f)", x, y, yaw);

  auto future_goal_handle = client_->async_send_goal(goal, send_goal_options);
  if (rclcpp::spin_until_future_complete(node_, future_goal_handle, 5s) !=
    rclcpp::FutureReturnCode::SUCCESS)
  {
    RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: failed to send goal");
    return false;
  }

  goal_handle_ = future_goal_handle.get();
  if (!goal_handle_) {
    RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: goal rejected");
    return false;
  }

  goal_sent_ = true;
  return true;
}

BT::NodeStatus Nav2PoseNode::onStart()
{
  if (!ensureClient()) {
    return BT::NodeStatus::FAILURE;
  }

  std::string frame_id = "map";
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;

  waiting_for_wp_ = false;
  goal_sent_ = false;
  result_ready_ = false;

  if (resolveGoal(frame_id, x, y, yaw)) {
    return sendGoal(frame_id, x, y, yaw) ? BT::NodeStatus::RUNNING : BT::NodeStatus::FAILURE;
  }

  if (wp_id_.empty()) {
    return BT::NodeStatus::FAILURE;
  }

  waiting_for_wp_ = true;
  resolve_start_ = node_->now();
  RCLCPP_INFO(
    node_->get_logger(),
    "Nav2PoseNode: waiting for nav wp_id='%s' on /mission_bt/nav_waypoint (up to %.0fs)...",
    wp_id_.c_str(), waypoint_wait_timeout_);
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus Nav2PoseNode::onRunning()
{
  if (waiting_for_wp_) {
    rclcpp::spin_some(node_);

    std::string frame_id = "map";
    double x = 0.0;
    double y = 0.0;
    double yaw = 0.0;
    if (resolveGoal(frame_id, x, y, yaw)) {
      waiting_for_wp_ = false;
      return sendGoal(frame_id, x, y, yaw) ? BT::NodeStatus::RUNNING : BT::NodeStatus::FAILURE;
    }

    const double elapsed = (node_->now() - resolve_start_).seconds();
    if (elapsed > waypoint_wait_timeout_) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "Nav2PoseNode: timeout waiting for nav wp_id='%s' (%.0fs)",
        wp_id_.c_str(), waypoint_wait_timeout_);
      return BT::NodeStatus::FAILURE;
    }
    return BT::NodeStatus::RUNNING;
  }

  if (!goal_sent_) {
    return BT::NodeStatus::FAILURE;
  }
  if (!result_ready_) {
    rclcpp::spin_some(node_);
    return BT::NodeStatus::RUNNING;
  }

  switch (result_.code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      if (!resolved_nav_id_.empty()) {
        publishNavReached(resolved_nav_id_);
      }
      RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: navigation succeeded");
      return BT::NodeStatus::SUCCESS;
    case rclcpp_action::ResultCode::ABORTED:
      RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: navigation aborted");
      return BT::NodeStatus::FAILURE;
    case rclcpp_action::ResultCode::CANCELED:
      RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: navigation canceled");
      return BT::NodeStatus::FAILURE;
    default:
      RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: unknown result code");
      return BT::NodeStatus::FAILURE;
  }
}

void Nav2PoseNode::onHalted()
{
  if (goal_handle_) {
    RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: halted, cancel goal");
    client_->async_cancel_goal(goal_handle_);
  }
  goal_sent_ = false;
  result_ready_ = false;
  waiting_for_wp_ = false;
}
