#pragma once

#include <memory>

#include <legged_mission_bt/msg/arm_waypoint.hpp>
#include <legged_mission_bt/msg/mission_plan.hpp>
#include <legged_mission_bt/msg/nav_waypoint.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/empty.hpp>
#include <std_srvs/srv/trigger.hpp>

#include "legged_mission_bt/waypoint_registry.hpp"

namespace legged_mission_bt
{

class WaypointRosBridge
{
public:
  WaypointRosBridge(
    const rclcpp::Node::SharedPtr & node,
    const std::shared_ptr<WaypointRegistry> & registry);

private:
  void onNavWaypoint(const msg::NavWaypoint::SharedPtr msg);
  void onArmWaypoint(const msg::ArmWaypoint::SharedPtr msg);
  void onMissionPlan(const msg::MissionPlan::SharedPtr msg);
  void onClearWaypoints(const std_msgs::msg::Empty::SharedPtr msg);
  void handleClearService(
    const std_srvs::srv::Trigger::Request::SharedPtr request,
    std_srvs::srv::Trigger::Response::SharedPtr response);

  rclcpp::Node::SharedPtr node_;
  std::shared_ptr<WaypointRegistry> registry_;
  rclcpp::Subscription<msg::NavWaypoint>::SharedPtr nav_sub_;
  rclcpp::Subscription<msg::ArmWaypoint>::SharedPtr arm_sub_;
  rclcpp::Subscription<msg::MissionPlan>::SharedPtr plan_sub_;
  rclcpp::Subscription<std_msgs::msg::Empty>::SharedPtr clear_sub_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr clear_srv_;
};

}  // namespace legged_mission_bt
