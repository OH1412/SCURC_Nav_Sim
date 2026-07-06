#include "legged_mission_bt/mission_plan_executor_node.hpp"

#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

using namespace std::chrono_literals;

MissionPlanExecutorNode::MissionPlanExecutorNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node,
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry)
: BT::StatefulActionNode(name, config),
  node_(std::move(node)),
  registry_(std::move(registry))
{
  if (!node_->has_parameter("plan_wait_timeout")) {
    node_->declare_parameter("plan_wait_timeout", 120.0);
  }
  if (!node_->has_parameter("waypoint_wait_timeout")) {
    node_->declare_parameter("waypoint_wait_timeout", 120.0);
  }
  if (!node_->has_parameter("arm_command_topic")) {
    node_->declare_parameter("arm_command_topic", "/arm_command");
  }
  if (!node_->has_parameter("arm_status_topic")) {
    node_->declare_parameter("arm_status_topic", "/arm_status");
  }
  if (!node_->has_parameter("nav_reached_topic")) {
    node_->declare_parameter("nav_reached_topic", "/mission_bt/nav_reached");
  }
  if (!node_->has_parameter("arm_pose_request_topic")) {
    node_->declare_parameter("arm_pose_request_topic", "/mission_bt/arm_pose_request");
  }

  plan_wait_timeout_ = node_->get_parameter("plan_wait_timeout").as_double();
  waypoint_wait_timeout_ = node_->get_parameter("waypoint_wait_timeout").as_double();
  const auto arm_cmd_topic = node_->get_parameter("arm_command_topic").as_string();
  const auto arm_status_topic = node_->get_parameter("arm_status_topic").as_string();
  const auto nav_reached_topic = node_->get_parameter("nav_reached_topic").as_string();
  const auto arm_request_topic = node_->get_parameter("arm_pose_request_topic").as_string();

  nav_client_ = rclcpp_action::create_client<NavigateToPose>(node_, "navigate_to_pose");

  auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();
  nav_reached_pub_ = node_->create_publisher<legged_mission_bt::msg::NavReached>(nav_reached_topic, qos);
  arm_request_pub_ = node_->create_publisher<legged_mission_bt::msg::ArmPoseRequest>(arm_request_topic, qos);
  arm_cmd_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>(arm_cmd_topic, qos);
  arm_status_sub_ = node_->create_subscription<std_msgs::msg::UInt8MultiArray>(
    arm_status_topic, qos,
    std::bind(&MissionPlanExecutorNode::onArmStatus, this, std::placeholders::_1));
}

BT::PortsList MissionPlanExecutorNode::providedPorts()
{
  return {
    BT::InputPort<double>("arm_timeout", 30.0, "Arm ACK timeout per step"),
  };
}

bool MissionPlanExecutorNode::ensureNavClient()
{
  if (!nav_client_->action_server_is_ready()) {
    if (!nav_client_->wait_for_action_server(5s)) {
      return false;
    }
  }
  return true;
}

bool MissionPlanExecutorNode::loadCurrentStep()
{
  if (!registry_->tryGetMissionStep(step_index_, current_step_)) {
    return false;
  }
  current_arm_slot_id_ = legged_mission_bt::resolveArmSlotId(current_step_);
  if (current_step_.arm_action != 0 &&
    !legged_mission_bt::isValidArmPointForAction(
      current_step_.arm_point_id, current_step_.arm_action))
  {
    RCLCPP_ERROR(
      node_->get_logger(),
      "MissionPlanExecutor: arm_point_id=%u invalid for action=%u "
      "(pick: 0~7, place: 8~15)",
      current_step_.arm_point_id, current_step_.arm_action);
    return false;
  }
  return true;
}

bool MissionPlanExecutorNode::sendNavGoal(const legged_mission_bt::NavWaypoint & wp)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = wp.frame_id;
  pose.header.stamp = node_->now();
  pose.pose.position.x = wp.x;
  pose.pose.position.y = wp.y;
  pose.pose.position.z = 0.0;
  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, wp.yaw);
  pose.pose.orientation = tf2::toMsg(q);

  NavigateToPose::Goal goal;
  goal.pose = pose;

  nav_goal_sent_ = false;
  nav_result_ready_ = false;

  auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};
  send_goal_options.result_callback =
    [this](const GoalHandle::WrappedResult & result) {
      nav_result_ = result;
      nav_result_ready_ = true;
    };

  RCLCPP_INFO(
    node_->get_logger(),
    "MissionPlanExecutor: step %zu nav '%s' → (%.3f, %.3f)",
    step_index_, current_step_.nav_id.c_str(), wp.x, wp.y);

  auto future_goal_handle = nav_client_->async_send_goal(goal, send_goal_options);
  if (rclcpp::spin_until_future_complete(node_, future_goal_handle, 5s) !=
    rclcpp::FutureReturnCode::SUCCESS)
  {
    return false;
  }

  goal_handle_ = future_goal_handle.get();
  if (!goal_handle_) {
    return false;
  }

  nav_goal_sent_ = true;
  return true;
}

void MissionPlanExecutorNode::publishNavReached(const std::string & nav_id)
{
  legged_mission_bt::msg::NavReached msg;
  msg.nav_id = nav_id;
  nav_reached_pub_->publish(msg);
  RCLCPP_INFO(node_->get_logger(), "MissionPlanExecutor: published nav_reached id='%s'", nav_id.c_str());
}

void MissionPlanExecutorNode::publishArmRequest()
{
  legged_mission_bt::msg::ArmPoseRequest msg;
  msg.arm_point_id = current_step_.arm_point_id;
  msg.nav_id = current_step_.nav_id;
  arm_request_pub_->publish(msg);
  RCLCPP_INFO(
    node_->get_logger(),
    "MissionPlanExecutor: arm_pose_request arm_point=%u nav_id='%s'",
    msg.arm_point_id, msg.nav_id.c_str());
}

void MissionPlanExecutorNode::publishArmCommand()
{
  const double serial_x = current_arm_wp_.x;
  const double serial_y = current_arm_wp_.y;
  const uint8_t action_code = current_step_.arm_action;

  std_msgs::msg::Float64MultiArray msg;
  msg.data = {
    serial_x, serial_y, current_arm_wp_.z, current_arm_wp_.yaw,
    static_cast<double>(action_code)};

  arm_cmd_pub_->publish(msg);
  arm_cmd_time_ = node_->now();
  arm_ack_received_ = false;
  arm_ack_success_ = false;
  expected_ack_state_ = (action_code == 1) ? 0x01 : 0x02;

  RCLCPP_INFO(
    node_->get_logger(),
    "MissionPlanExecutor: arm cmd slot='%s' action=%u",
    current_arm_slot_id_.c_str(), action_code);
}

void MissionPlanExecutorNode::onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg)
{
  if (phase_ != Phase::WAIT_ARM_ACK || msg->data.size() < 2) {
    return;
  }
  if (msg->data[0] != expected_ack_state_ || arm_ack_received_) {
    return;
  }
  arm_ack_received_ = true;
  arm_ack_success_ = (msg->data[1] == 0x00);
}

BT::NodeStatus MissionPlanExecutorNode::onStart()
{
  getInput("arm_timeout", arm_timeout_);
  step_index_ = 0;
  phase_ = Phase::WAIT_PLAN;
  phase_start_ = node_->now();
  arm_request_sent_ = false;

  RCLCPP_INFO(node_->get_logger(), "MissionPlanExecutor: waiting for external mission_plan...");
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus MissionPlanExecutorNode::onRunning()
{
  rclcpp::spin_some(node_);

  switch (phase_) {
    case Phase::WAIT_PLAN:
      if (registry_->hasMissionPlan()) {
        RCLCPP_INFO(
          node_->get_logger(), "MissionPlanExecutor: loaded %zu steps",
          registry_->missionStepCount());
        phase_ = Phase::NEXT_STEP;
      } else if ((node_->now() - phase_start_).seconds() > plan_wait_timeout_) {
        RCLCPP_ERROR(node_->get_logger(), "MissionPlanExecutor: mission_plan timeout");
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::NEXT_STEP:
      if (!loadCurrentStep()) {
        phase_ = Phase::DONE;
        break;
      }
      RCLCPP_INFO(
        node_->get_logger(),
        "MissionPlanExecutor: --- step %zu nav='%s' arm_point=%u action=%u ---",
        step_index_, current_step_.nav_id.c_str(), current_step_.arm_point_id,
        current_step_.arm_action);
      if (!current_step_.nav_id.empty()) {
        phase_ = Phase::WAIT_NAV_WP;
        phase_start_ = node_->now();
      } else if (current_step_.arm_action != 0) {
        phase_ = Phase::REQUEST_ARM;
        arm_request_sent_ = false;
      } else {
        ++step_index_;
      }
      break;

    case Phase::WAIT_NAV_WP:
      if (registry_->tryGetNav(current_step_.nav_id, current_nav_wp_)) {
        if (!ensureNavClient()) {
          RCLCPP_WARN(node_->get_logger(), "MissionPlanExecutor: navigate_to_pose not ready");
          break;
        }
        if (sendNavGoal(current_nav_wp_)) {
          phase_ = Phase::NAVIGATING;
        } else {
          return BT::NodeStatus::FAILURE;
        }
      } else if ((node_->now() - phase_start_).seconds() > waypoint_wait_timeout_) {
        RCLCPP_ERROR(
          node_->get_logger(), "MissionPlanExecutor: nav wp '%s' timeout",
          current_step_.nav_id.c_str());
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::NAVIGATING:
      if (!nav_result_ready_) {
        break;
      }
      if (nav_result_.code != rclcpp_action::ResultCode::SUCCEEDED) {
        RCLCPP_ERROR(node_->get_logger(), "MissionPlanExecutor: navigation failed");
        return BT::NodeStatus::FAILURE;
      }
      publishNavReached(current_step_.nav_id);
      if (current_step_.arm_action != 0) {
        phase_ = Phase::REQUEST_ARM;
        arm_request_sent_ = false;
      } else {
        ++step_index_;
        phase_ = Phase::NEXT_STEP;
      }
      break;

    case Phase::REQUEST_ARM:
      if (!arm_request_sent_) {
        registry_->clearArm(current_arm_slot_id_);
        publishArmRequest();
        arm_request_sent_ = true;
        phase_start_ = node_->now();
      }
      phase_ = Phase::WAIT_ARM_WP;
      break;

    case Phase::WAIT_ARM_WP:
      if (registry_->tryGetArm(current_arm_slot_id_, current_arm_wp_)) {
        publishArmCommand();
        phase_ = Phase::WAIT_ARM_ACK;
      } else if ((node_->now() - phase_start_).seconds() > waypoint_wait_timeout_) {
        RCLCPP_ERROR(
          node_->get_logger(),           "MissionPlanExecutor: arm wp '%s' timeout",
          current_arm_slot_id_.c_str());
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::WAIT_ARM_ACK:
      if (arm_ack_received_) {
        if (!arm_ack_success_) {
          return BT::NodeStatus::FAILURE;
        }
        ++step_index_;
        phase_ = Phase::NEXT_STEP;
      } else if ((node_->now() - arm_cmd_time_).seconds() > arm_timeout_) {
        RCLCPP_ERROR(node_->get_logger(), "MissionPlanExecutor: arm ACK timeout");
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::DONE:
      RCLCPP_INFO(node_->get_logger(), "MissionPlanExecutor: all steps completed");
      return BT::NodeStatus::SUCCESS;

    default:
      break;
  }

  return BT::NodeStatus::RUNNING;
}

void MissionPlanExecutorNode::onHalted()
{
  if (goal_handle_) {
    nav_client_->async_cancel_goal(goal_handle_);
  }
}
