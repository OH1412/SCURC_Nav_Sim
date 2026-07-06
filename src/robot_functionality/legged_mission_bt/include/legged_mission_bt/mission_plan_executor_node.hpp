#pragma once

#include <cstdint>
#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <legged_mission_bt/msg/arm_pose_request.hpp>
#include <legged_mission_bt/msg/nav_reached.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <std_msgs/msg/u_int8_multi_array.hpp>

#include "legged_mission_bt/waypoint_registry.hpp"

class MissionPlanExecutorNode : public BT::StatefulActionNode
{
public:
  using NavigateToPose = nav2_msgs::action::NavigateToPose;
  using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;

  MissionPlanExecutorNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node,
    std::shared_ptr<legged_mission_bt::WaypointRegistry> registry);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  enum class Phase
  {
    WAIT_PLAN,
    WAIT_NAV_WP,
    NAVIGATING,
    REQUEST_ARM,
    WAIT_ARM_WP,
    ARM_EXEC,
    WAIT_ARM_ACK,
    NEXT_STEP,
    DONE,
  };

  bool ensureNavClient();
  bool sendNavGoal(const legged_mission_bt::NavWaypoint & wp);
  void publishNavReached(const std::string & nav_id);
  void publishArmRequest();
  void publishArmCommand();
  void onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg);
  bool loadCurrentStep();

  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry_;

  rclcpp_action::Client<NavigateToPose>::SharedPtr nav_client_;
  rclcpp::Publisher<legged_mission_bt::msg::NavReached>::SharedPtr nav_reached_pub_;
  rclcpp::Publisher<legged_mission_bt::msg::ArmPoseRequest>::SharedPtr arm_request_pub_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr arm_cmd_pub_;
  rclcpp::Subscription<std_msgs::msg::UInt8MultiArray>::SharedPtr arm_status_sub_;

  Phase phase_{Phase::WAIT_PLAN};
  size_t step_index_{0};
  legged_mission_bt::PlannedStep current_step_;
  std::string current_arm_slot_id_;
  legged_mission_bt::NavWaypoint current_nav_wp_;
  legged_mission_bt::ArmWaypoint current_arm_wp_;

  GoalHandle::SharedPtr goal_handle_;
  GoalHandle::WrappedResult nav_result_;
  bool nav_goal_sent_{false};
  bool nav_result_ready_{false};

  rclcpp::Time phase_start_;
  rclcpp::Time arm_cmd_time_;
  double plan_wait_timeout_{120.0};
  double waypoint_wait_timeout_{120.0};
  double arm_timeout_{30.0};
  bool arm_request_sent_{false};
  bool arm_ack_received_{false};
  bool arm_ack_success_{false};
  uint8_t expected_ack_state_{0};
};
