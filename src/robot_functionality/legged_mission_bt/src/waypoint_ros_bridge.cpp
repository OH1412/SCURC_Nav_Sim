#include "legged_mission_bt/waypoint_ros_bridge.hpp"

namespace legged_mission_bt
{

WaypointRosBridge::WaypointRosBridge(
  const rclcpp::Node::SharedPtr & node,
  const std::shared_ptr<WaypointRegistry> & registry)
: node_(node),
  registry_(registry)
{
  if (!node_->has_parameter("nav_waypoint_topic")) {
    node_->declare_parameter("nav_waypoint_topic", "/mission_bt/nav_waypoint");
  }
  if (!node_->has_parameter("arm_waypoint_topic")) {
    node_->declare_parameter("arm_waypoint_topic", "/mission_bt/arm_waypoint");
  }
  if (!node_->has_parameter("clear_waypoints_topic")) {
    node_->declare_parameter("clear_waypoints_topic", "/mission_bt/clear_waypoints");
  }
  if (!node_->has_parameter("mission_plan_topic")) {
    node_->declare_parameter("mission_plan_topic", "/mission_bt/mission_plan");
  }

  const auto nav_topic = node_->get_parameter("nav_waypoint_topic").as_string();
  const auto arm_topic = node_->get_parameter("arm_waypoint_topic").as_string();
  const auto clear_topic = node_->get_parameter("clear_waypoints_topic").as_string();
  const auto plan_topic = node_->get_parameter("mission_plan_topic").as_string();

  auto qos = rclcpp::QoS(rclcpp::KeepLast(50)).reliable();

  nav_sub_ = node_->create_subscription<msg::NavWaypoint>(
    nav_topic, qos,
    std::bind(&WaypointRosBridge::onNavWaypoint, this, std::placeholders::_1));

  arm_sub_ = node_->create_subscription<msg::ArmWaypoint>(
    arm_topic, qos,
    std::bind(&WaypointRosBridge::onArmWaypoint, this, std::placeholders::_1));

  plan_sub_ = node_->create_subscription<msg::MissionPlan>(
    plan_topic, qos,
    std::bind(&WaypointRosBridge::onMissionPlan, this, std::placeholders::_1));

  clear_sub_ = node_->create_subscription<std_msgs::msg::Empty>(
    clear_topic, qos,
    std::bind(&WaypointRosBridge::onClearWaypoints, this, std::placeholders::_1));

  clear_srv_ = node_->create_service<std_srvs::srv::Trigger>(
    "/mission_bt/clear_waypoints",
    std::bind(
      &WaypointRosBridge::handleClearService, this,
      std::placeholders::_1, std::placeholders::_2));

  RCLCPP_INFO(
    node_->get_logger(),
    "WaypointRosBridge: plan=%s, nav=%s, arm=%s, clear=%s",
    plan_topic.c_str(), nav_topic.c_str(), arm_topic.c_str(), clear_topic.c_str());
}

void WaypointRosBridge::onMissionPlan(const msg::MissionPlan::SharedPtr msg)
{
  std::vector<PlannedStep> steps;
  steps.reserve(msg->steps.size());
  for (const auto & step : msg->steps) {
    PlannedStep planned;
    planned.nav_id = step.nav_id;
    planned.arm_point_id = step.arm_point_id;
    planned.arm_action = step.arm_action;
    steps.push_back(planned);
    RCLCPP_INFO(
      node_->get_logger(),
      "MissionPlan step: nav='%s' arm_point=%u action=%u",
      planned.nav_id.c_str(), planned.arm_point_id, planned.arm_action);
  }
  registry_->setMissionPlan(std::move(steps));
  RCLCPP_INFO(node_->get_logger(), "Registered mission plan with %zu steps", msg->steps.size());
}

void WaypointRosBridge::onNavWaypoint(const msg::NavWaypoint::SharedPtr msg)
{
  if (msg->id.empty()) {
    RCLCPP_WARN(node_->get_logger(), "WaypointRosBridge: ignored nav waypoint with empty id");
    return;
  }

  NavWaypoint wp;
  wp.frame_id = msg->frame_id.empty() ? "map" : msg->frame_id;
  wp.x = msg->x;
  wp.y = msg->y;
  wp.yaw = msg->yaw;
  registry_->setNav(msg->id, wp);

  RCLCPP_INFO(
    node_->get_logger(),
    "Registered nav wp_id='%s' frame=%s (%.3f, %.3f, yaw=%.3f)",
    msg->id.c_str(), wp.frame_id.c_str(), wp.x, wp.y, wp.yaw);
}

void WaypointRosBridge::onArmWaypoint(const msg::ArmWaypoint::SharedPtr msg)
{
  if (msg->id.empty()) {
    RCLCPP_WARN(node_->get_logger(), "WaypointRosBridge: ignored arm waypoint with empty id");
    return;
  }

  ArmWaypoint wp;
  wp.x = msg->x;
  wp.y = msg->y;
  wp.z = msg->z;
  wp.yaw = msg->yaw;
  registry_->setArm(msg->id, wp);

  RCLCPP_INFO(
    node_->get_logger(),
    "Registered arm wp_id='%s' (%.1f, %.1f, %.1f, yaw=%.3f)",
    msg->id.c_str(), wp.x, wp.y, wp.z, wp.yaw);
}

void WaypointRosBridge::onClearWaypoints(const std_msgs::msg::Empty::SharedPtr /*msg*/)
{
  registry_->clearAll();
  RCLCPP_INFO(node_->get_logger(), "WaypointRosBridge: cleared all waypoints");
}

void WaypointRosBridge::handleClearService(
  const std_srvs::srv::Trigger::Request::SharedPtr /*request*/,
  std_srvs::srv::Trigger::Response::SharedPtr response)
{
  registry_->clearAll();
  response->success = true;
  response->message = "All mission waypoints cleared";
  RCLCPP_INFO(node_->get_logger(), "WaypointRosBridge: cleared all waypoints (service)");
}

}  // namespace legged_mission_bt
