#include <algorithm>
#include <chrono>
#include <memory>
#include <string>
#include <thread>

#include <behaviortree_cpp_v3/bt_factory.h>
#include <lifecycle_msgs/msg/state.hpp>
#include <lifecycle_msgs/srv/get_state.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>

#include "legged_mission_bt/arm_action_node.hpp"
#include "legged_mission_bt/mission_plan_executor_node.hpp"
#include "legged_mission_bt/manual_confirm_node.hpp"
#include "legged_mission_bt/manual_arm_step_node.hpp"
#include "legged_mission_bt/nav2_pose_node.hpp"
#include "legged_mission_bt/wait_seconds_node.hpp"
#include "legged_mission_bt/waypoint_registry.hpp"
#include "legged_mission_bt/waypoint_ros_bridge.hpp"

using namespace std::chrono_literals;

namespace
{

constexpr uint8_t kLifecycleActive = lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE;

bool waitForLifecycleActive(
  const rclcpp::Node::SharedPtr & node,
  const std::string & lifecycle_node_name,
  double timeout_sec)
{
  const std::string service_name = lifecycle_node_name + "/get_state";
  auto client = node->create_client<lifecycle_msgs::srv::GetState>(service_name);

  RCLCPP_INFO(
    node->get_logger(),
    "Waiting for %s lifecycle ACTIVE (up to %.0fs)...",
    lifecycle_node_name.c_str(), timeout_sec);

  const rclcpp::Time deadline =
    node->now() + rclcpp::Duration::from_seconds(timeout_sec);
  auto last_log = node->now();

  while (rclcpp::ok() && node->now() < deadline) {
    if (!client->service_is_ready()) {
      rclcpp::spin_some(node);
      rclcpp::sleep_for(200ms);
      if ((node->now() - last_log).seconds() >= 5.0) {
        RCLCPP_INFO(
          node->get_logger(),
          "Still waiting for %s/get_state service...",
          lifecycle_node_name.c_str());
        last_log = node->now();
      }
      continue;
    }

    auto request = std::make_shared<lifecycle_msgs::srv::GetState::Request>();
    auto future = client->async_send_request(request);

    const double remaining_s = (deadline - node->now()).seconds();
    const auto spin_timeout = std::min(1.0, std::max(0.0, remaining_s));
    if (rclcpp::spin_until_future_complete(
        node, future, std::chrono::duration<double>(spin_timeout)) ==
      rclcpp::FutureReturnCode::SUCCESS)
    {
      const auto state = future.get()->current_state;
      if (state.id == kLifecycleActive) {
        RCLCPP_INFO(
          node->get_logger(),
          "%s lifecycle ACTIVE (label=%s)",
          lifecycle_node_name.c_str(), state.label.c_str());
        return true;
      }
      if ((node->now() - last_log).seconds() >= 5.0) {
        RCLCPP_INFO(
          node->get_logger(),
          "%s lifecycle state=%s (%u), still waiting...",
          lifecycle_node_name.c_str(), state.label.c_str(), state.id);
        last_log = node->now();
      }
    }

    rclcpp::spin_some(node);
    rclcpp::sleep_for(500ms);
  }

  RCLCPP_ERROR(
    node->get_logger(),
    "Timeout waiting for %s lifecycle ACTIVE (%.0fs)",
    lifecycle_node_name.c_str(), timeout_sec);
  return false;
}

bool waitForNavigateToPoseAction(
  const rclcpp::Node::SharedPtr & node,
  const rclcpp_action::Client<nav2_msgs::action::NavigateToPose>::SharedPtr & client,
  double timeout_sec)
{
  RCLCPP_INFO(
    node->get_logger(),
    "Waiting for navigate_to_pose action server (up to %.0fs)...",
    timeout_sec);

  const rclcpp::Time deadline =
    node->now() + rclcpp::Duration::from_seconds(timeout_sec);
  auto last_log = node->now();

  while (rclcpp::ok() && node->now() < deadline) {
    if (client->wait_for_action_server(0s)) {
      RCLCPP_INFO(node->get_logger(), "navigate_to_pose action server ready.");
      return true;
    }
    if ((node->now() - last_log).seconds() >= 5.0) {
      RCLCPP_INFO(node->get_logger(), "Still waiting for navigate_to_pose...");
      last_log = node->now();
    }
    rclcpp::spin_some(node);
    rclcpp::sleep_for(200ms);
  }

  RCLCPP_ERROR(
    node->get_logger(),
    "navigate_to_pose not available after %.0fs", timeout_sec);
  return false;
}

}  // namespace

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  auto node = std::make_shared<rclcpp::Node>("mission_bt_node");

  node->declare_parameter<std::string>("bt_xml_file", "");
  node->declare_parameter<std::string>("waypoints_file", "");
  node->declare_parameter<bool>("require_nav2", true);
  node->declare_parameter<double>("wait_for_nav2_timeout", 60.0);
  node->declare_parameter<std::string>("bt_navigator_node_name", "bt_navigator");
  node->declare_parameter<double>("wait_for_bt_navigator_active_timeout", 120.0);
  node->declare_parameter<double>("waypoint_wait_timeout", 120.0);
  node->declare_parameter<std::string>("arm_command_topic", "/arm_command");
  node->declare_parameter<std::string>("arm_status_topic", "/arm_status");
  node->declare_parameter<std::string>("nav_waypoint_topic", "/mission_bt/nav_waypoint");
  node->declare_parameter<std::string>("arm_waypoint_topic", "/mission_bt/arm_waypoint");
  node->declare_parameter<std::string>("mission_plan_topic", "/mission_bt/mission_plan");
  node->declare_parameter<std::string>("nav_reached_topic", "/mission_bt/nav_reached");
  node->declare_parameter<std::string>("arm_pose_request_topic", "/mission_bt/arm_pose_request");
  node->declare_parameter<std::string>("manual_arm_prompt_topic", "/mission_bt/manual_arm_prompt");
  node->declare_parameter<std::string>("manual_arm_input_topic", "/mission_bt/manual_arm_input");
  node->declare_parameter<double>("plan_wait_timeout", 120.0);

  std::string bt_xml_file;
  node->get_parameter("bt_xml_file", bt_xml_file);

  if (bt_xml_file.empty()) {
    RCLCPP_ERROR(node->get_logger(), "Parameter 'bt_xml_file' is empty.");
    return 1;
  }

  RCLCPP_INFO(node->get_logger(), "Loading mission BT: %s", bt_xml_file.c_str());

  auto registry = legged_mission_bt::WaypointRegistry::create();

  std::string waypoints_file;
  node->get_parameter("waypoints_file", waypoints_file);
  try {
    registry->seedFromFile(waypoints_file);
    if (!waypoints_file.empty()) {
      RCLCPP_INFO(
        node->get_logger(),
        "Seeded %zu nav + %zu arm waypoints from %s",
        registry->navCount(), registry->armCount(), waypoints_file.c_str());
    }
  } catch (const std::exception & e) {
    RCLCPP_ERROR(node->get_logger(), "%s", e.what());
    return 1;
  }

  legged_mission_bt::WaypointRosBridge waypoint_bridge(node, registry);
  RCLCPP_INFO(
    node->get_logger(),
    "Runtime waypoint injection enabled (publish to /mission_bt/nav_waypoint and /mission_bt/arm_waypoint)");

  BT::BehaviorTreeFactory factory;

  BT::NodeBuilder nav_builder =
    [node, registry](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<Nav2PoseNode>(name, config, node, registry);
    };
  factory.registerBuilder<Nav2PoseNode>("Nav2PoseNode", nav_builder);

  BT::NodeBuilder pick_builder =
    [node, registry](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<legged_mission_bt::ArmActionNode>(
        name, config, node, registry, 1, 0x01);
    };
  factory.registerBuilder<legged_mission_bt::ArmActionNode>("ArmPickNode", pick_builder);

  BT::NodeBuilder place_builder =
    [node, registry](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<legged_mission_bt::ArmActionNode>(
        name, config, node, registry, 2, 0x02);
    };
  factory.registerBuilder<legged_mission_bt::ArmActionNode>("ArmPlaceNode", place_builder);

  BT::NodeBuilder plan_executor_builder =
    [node, registry](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<MissionPlanExecutorNode>(name, config, node, registry);
    };
  factory.registerBuilder<MissionPlanExecutorNode>("MissionPlanExecutorNode", plan_executor_builder);

  BT::NodeBuilder wait_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<WaitSecondsNode>(name, config, node);
    };
  factory.registerBuilder<WaitSecondsNode>("WaitSecondsNode", wait_builder);

  BT::NodeBuilder manual_arm_builder =
    [node, registry](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<legged_mission_bt::ManualArmStepNode>(
        name, config, node, registry, 1, 0x01);
    };
  factory.registerBuilder<legged_mission_bt::ManualArmStepNode>(
    "ManualArmStepNode", manual_arm_builder);

  BT::NodeBuilder manual_confirm_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config) {
      return std::make_unique<legged_mission_bt::ManualConfirmNode>(name, config, node);
    };
  factory.registerBuilder<legged_mission_bt::ManualConfirmNode>(
    "ManualConfirmNode", manual_confirm_builder);

  BT::Tree tree;
  try {
    tree = factory.createTreeFromFile(bt_xml_file);
  } catch (const std::exception & e) {
    RCLCPP_ERROR(node->get_logger(), "Failed to load BT xml: %s", e.what());
    return 1;
  }

  bool require_nav2 = true;
  node->get_parameter("require_nav2", require_nav2);

  if (require_nav2) {
    double nav_timeout = 120.0;
    node->get_parameter("wait_for_nav2_timeout", nav_timeout);

    std::string bt_navigator_node;
    node->get_parameter("bt_navigator_node_name", bt_navigator_node);
    double bt_navigator_timeout = 120.0;
    node->get_parameter("wait_for_bt_navigator_active_timeout", bt_navigator_timeout);
    const double lifecycle_timeout = std::max(nav_timeout, bt_navigator_timeout);

    // Nav2 须先完成 lifecycle activate，navigate_to_pose 才会可用
    if (!waitForLifecycleActive(node, bt_navigator_node, lifecycle_timeout)) {
      RCLCPP_ERROR(
        node->get_logger(),
        "Nav2 not ready: %s not ACTIVE. Check lifecycle_manager_navigation logs "
        "(planner_server/controller_server change_state timeout).",
        bt_navigator_node.c_str());
      return 1;
    }

    auto nav_client = rclcpp_action::create_client<nav2_msgs::action::NavigateToPose>(
      node, "navigate_to_pose");
    if (!waitForNavigateToPoseAction(node, nav_client, nav_timeout)) {
      return 1;
    }
  } else {
    RCLCPP_INFO(node->get_logger(), "require_nav2=false, skipping Nav2 wait (arm-only mode).");
  }

  RCLCPP_INFO(node->get_logger(), "Starting mission BT tick loop.");

  rclcpp::Rate rate(10.0);
  while (rclcpp::ok()) {
    const auto status = tree.tickRoot();

    if (status == BT::NodeStatus::SUCCESS) {
      RCLCPP_INFO(node->get_logger(), "Mission BT finished SUCCESS");
      break;
    }
    if (status == BT::NodeStatus::FAILURE) {
      RCLCPP_ERROR(node->get_logger(), "Mission BT finished FAILURE");
      rclcpp::shutdown();
      return 2;
    }

    rclcpp::spin_some(node);
    rate.sleep();
  }

  rclcpp::shutdown();
  return 0;
}
