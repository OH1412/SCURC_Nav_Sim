#include "legged_mission_bt/manual_arm_step_node.hpp"

#include <atomic>
#include <chrono>
#include <stdexcept>
#include <thread>

using namespace std::chrono_literals;

namespace legged_mission_bt
{

namespace
{
std::atomic<uint8_t> g_manual_step_counter{0};
}  // namespace

ManualArmStepNode::ManualArmStepNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node,
  std::shared_ptr<WaypointRegistry> registry,
  uint8_t action_code,
  uint8_t expected_ack_state)
: BT::StatefulActionNode(name, config),
  node_(std::move(node)),
  registry_(std::move(registry)),
  action_code_(action_code),
  expected_ack_state_(expected_ack_state)
{
  if (!node_->has_parameter("arm_command_topic")) {
    node_->declare_parameter("arm_command_topic", "/arm_command");
  }
  if (!node_->has_parameter("arm_status_topic")) {
    node_->declare_parameter("arm_status_topic", "/arm_status");
  }
  if (!node_->has_parameter("waypoint_wait_timeout")) {
    node_->declare_parameter("waypoint_wait_timeout", 120.0);
  }
  if (!node_->has_parameter("manual_arm_prompt_topic")) {
    node_->declare_parameter("manual_arm_prompt_topic", "/mission_bt/manual_arm_prompt");
  }
  if (!node_->has_parameter("manual_arm_input_topic")) {
    node_->declare_parameter("manual_arm_input_topic", "/mission_bt/manual_arm_input");
  }
  if (!node_->has_parameter("arm_pose_request_topic")) {
    node_->declare_parameter("arm_pose_request_topic", "/mission_bt/arm_pose_request");
  }

  waypoint_wait_timeout_ = node_->get_parameter("waypoint_wait_timeout").as_double();
  const auto prompt_topic = node_->get_parameter("manual_arm_prompt_topic").as_string();
  const auto input_topic = node_->get_parameter("manual_arm_input_topic").as_string();
  const auto arm_request_topic = node_->get_parameter("arm_pose_request_topic").as_string();
  const auto arm_cmd_topic = node_->get_parameter("arm_command_topic").as_string();
  const auto arm_status_topic = node_->get_parameter("arm_status_topic").as_string();

  auto prompt_qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
  auto data_qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();

  prompt_pub_ = node_->create_publisher<msg::ManualArmPrompt>(prompt_topic, prompt_qos);
  arm_request_pub_ = node_->create_publisher<msg::ArmPoseRequest>(arm_request_topic, data_qos);
  cmd_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>(arm_cmd_topic, data_qos);
  input_sub_ = node_->create_subscription<msg::ManualArmInput>(
    input_topic, data_qos,
    std::bind(&ManualArmStepNode::onManualInput, this, std::placeholders::_1));
  status_sub_ = node_->create_subscription<std_msgs::msg::UInt8MultiArray>(
    arm_status_topic, data_qos,
    std::bind(&ManualArmStepNode::onArmStatus, this, std::placeholders::_1));
}

BT::PortsList ManualArmStepNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("action", "pick", "pick or place"),
    BT::InputPort<double>("timeout", 120.0, "Manual confirm + arm ACK timeout (seconds)"),
  };
}

uint8_t ManualArmStepNode::parseActionCode(const std::string & action)
{
  if (action == "place" || action == "Place" || action == "PLACE") {
    return 2;
  }
  return 1;
}

void ManualArmStepNode::onManualInput(const msg::ManualArmInput::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(input_mutex_);
  pending_point_id_ = msg->arm_point_id;
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: received manual input arm_point_id=%u",
    name().c_str(), msg->arm_point_id);
}

void ManualArmStepNode::publishPrompt(bool bump_step_index)
{
  if (bump_step_index) {
    step_index_ = ++g_manual_step_counter;
  }
  msg::ManualArmPrompt prompt;
  prompt.action = action_code_;
  prompt.step_index = step_index_;
  if (action_code_ == 1) {
    prompt.hint = "遥控到位后按 Enter，再输入抓取点位 0~7";
  } else {
    prompt.hint = "遥控到位后按 Enter，再输入放置点位 8~15";
  }
  prompt_pub_->publish(prompt);
  last_prompt_pub_ = node_->now();
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: waiting manual confirm (step %u, %s)",
    name().c_str(), step_index_, action_code_ == 1 ? "Pick" : "Place");
}

void ManualArmStepNode::publishArmRequest()
{
  msg::ArmPoseRequest req;
  req.arm_point_id = pending_point_id_.value_or(0);
  req.nav_id = "manual_" + std::to_string(g_manual_step_counter.load());
  arm_request_pub_->publish(req);
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: arm_pose_request arm_point=%u",
    name().c_str(), req.arm_point_id);
}

void ManualArmStepNode::publishArmCommand()
{
  const double serial_x = -arm_wp_.x;
  const double serial_y = -arm_wp_.y;

  std_msgs::msg::Float64MultiArray msg;
  msg.data = {
    serial_x, serial_y, arm_wp_.z, arm_wp_.yaw,
    static_cast<double>(action_code_)};

  cmd_pub_->publish(msg);
  arm_cmd_time_ = node_->now();
  ack_received_.store(false);
  ack_success_.store(false);

  RCLCPP_INFO(
    node_->get_logger(),
    "%s: sent %s cmd slot='%s' (%.1f, %.1f, %.1f)",
    name().c_str(), action_code_ == 1 ? "Pick" : "Place",
    arm_slot_id_.c_str(), arm_wp_.x, arm_wp_.y, arm_wp_.z);
}

void ManualArmStepNode::onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg)
{
  if (phase_ != Phase::WAIT_ARM_ACK || msg->data.size() < 2 || ack_received_.load()) {
    return;
  }
  if (msg->data[0] != expected_ack_state_) {
    return;
  }
  ack_received_.store(true);
  ack_success_.store(msg->data[1] == 0x00);
}

bool ManualArmStepNode::waitForCommandSubscriber(double max_wait_sec)
{
  const auto deadline = node_->now() + rclcpp::Duration::from_seconds(max_wait_sec);
  while (rclcpp::ok() && node_->now() < deadline) {
    rclcpp::spin_some(node_);
    if (cmd_pub_->get_subscription_count() > 0) {
      return true;
    }
    std::this_thread::sleep_for(50ms);
  }
  rclcpp::spin_some(node_);
  return cmd_pub_->get_subscription_count() > 0;
}

BT::NodeStatus ManualArmStepNode::onStart()
{
  std::string action_str;
  getInput("action", action_str);
  getInput("timeout", timeout_sec_);

  action_code_ = parseActionCode(action_str);
  expected_ack_state_ = (action_code_ == 1) ? 0x01 : 0x02;

  {
    std::lock_guard<std::mutex> lock(input_mutex_);
    pending_point_id_.reset();
  }

  phase_ = Phase::WAIT_MANUAL;
  prompt_sent_ = false;
  step_index_ = 0;
  phase_start_ = node_->now();
  arm_slot_id_.clear();

  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus ManualArmStepNode::onRunning()
{
  rclcpp::spin_some(node_);

  switch (phase_) {
    case Phase::WAIT_MANUAL:
      if (!prompt_sent_) {
        publishPrompt(true);
        prompt_sent_ = true;
        phase_start_ = node_->now();
      } else if (
        (node_->now() - last_prompt_pub_).seconds() >= kPromptRepublishSec)
      {
        publishPrompt(false);
      }
      {
        std::lock_guard<std::mutex> lock(input_mutex_);
        if (pending_point_id_.has_value()) {
          const uint8_t pid = pending_point_id_.value();
          if (!isValidArmPointForAction(pid, action_code_)) {
            RCLCPP_ERROR(
              node_->get_logger(),
              "%s: arm_point_id=%u invalid for %s",
              name().c_str(), pid, action_code_ == 1 ? "Pick" : "Place");
            return BT::NodeStatus::FAILURE;
          }
          arm_slot_id_ = std::to_string(pid);
          phase_ = Phase::REQUEST_ARM;
        }
      }
      if ((node_->now() - phase_start_).seconds() > timeout_sec_) {
        RCLCPP_ERROR(node_->get_logger(), "%s: manual confirm timeout", name().c_str());
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::REQUEST_ARM:
      if (registry_) {
        registry_->clearArm(arm_slot_id_);
      }
      publishArmRequest();
      phase_ = Phase::WAIT_ARM_WP;
      phase_start_ = node_->now();
      break;

    case Phase::WAIT_ARM_WP:
      if (registry_ && registry_->tryGetArm(arm_slot_id_, arm_wp_)) {
        if (!waitForCommandSubscriber(5.0)) {
          RCLCPP_ERROR(
            node_->get_logger(),
            "%s: no subscriber on arm_command topic", name().c_str());
          return BT::NodeStatus::FAILURE;
        }
        publishArmCommand();
        phase_ = Phase::WAIT_ARM_ACK;
      } else if ((node_->now() - phase_start_).seconds() > waypoint_wait_timeout_) {
        RCLCPP_ERROR(
          node_->get_logger(),
          "%s: timeout waiting arm_waypoint slot='%s'",
          name().c_str(), arm_slot_id_.c_str());
        return BT::NodeStatus::FAILURE;
      }
      break;

    case Phase::WAIT_ARM_ACK:
      if (ack_received_.load()) {
        if (!ack_success_.load()) {
          RCLCPP_ERROR(node_->get_logger(), "%s: arm ACK failure", name().c_str());
          return BT::NodeStatus::FAILURE;
        }
        RCLCPP_INFO(node_->get_logger(), "%s: step completed", name().c_str());
        return BT::NodeStatus::SUCCESS;
      }
      if ((node_->now() - arm_cmd_time_).seconds() > timeout_sec_) {
        RCLCPP_ERROR(node_->get_logger(), "%s: arm ACK timeout", name().c_str());
        return BT::NodeStatus::FAILURE;
      }
      break;
  }

  return BT::NodeStatus::RUNNING;
}

void ManualArmStepNode::onHalted()
{
  RCLCPP_WARN(node_->get_logger(), "%s: halted", name().c_str());
}

}  // namespace legged_mission_bt
