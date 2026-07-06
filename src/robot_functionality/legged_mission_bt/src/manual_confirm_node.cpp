#include "legged_mission_bt/manual_confirm_node.hpp"

#include <atomic>

using namespace std::chrono_literals;

namespace legged_mission_bt
{

namespace
{
std::atomic<uint8_t> g_manual_step_counter{0};
}  // namespace

ManualConfirmNode::ManualConfirmNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node)
: BT::StatefulActionNode(name, config),
  node_(std::move(node))
{
  if (!node_->has_parameter("manual_arm_prompt_topic")) {
    node_->declare_parameter("manual_arm_prompt_topic", "/mission_bt/manual_arm_prompt");
  }
  if (!node_->has_parameter("manual_arm_input_topic")) {
    node_->declare_parameter("manual_arm_input_topic", "/mission_bt/manual_arm_input");
  }

  const auto prompt_topic = node_->get_parameter("manual_arm_prompt_topic").as_string();
  const auto input_topic = node_->get_parameter("manual_arm_input_topic").as_string();

  auto prompt_qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
  auto data_qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();

  prompt_pub_ = node_->create_publisher<msg::ManualArmPrompt>(prompt_topic, prompt_qos);
  input_sub_ = node_->create_subscription<msg::ManualArmInput>(
    input_topic, data_qos,
    std::bind(&ManualConfirmNode::onManualInput, this, std::placeholders::_1));
}

BT::PortsList ManualConfirmNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("action", "pick", "pick or place"),
    BT::InputPort<double>("timeout", 300.0, "Wait for operator input (seconds)"),
    BT::OutputPort<std::string>("arm_slot", "Selected arm point id string"),
  };
}

uint8_t ManualConfirmNode::parseActionCode(const std::string & action)
{
  if (action == "place" || action == "Place" || action == "PLACE") {
    return 2;
  }
  return 1;
}

void ManualConfirmNode::onManualInput(const msg::ManualArmInput::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(input_mutex_);
  pending_point_id_ = msg->arm_point_id;
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: received manual input arm_point_id=%u",
    name().c_str(), msg->arm_point_id);
}

void ManualConfirmNode::publishPrompt(bool bump_step_index)
{
  if (bump_step_index) {
    step_index_ = ++g_manual_step_counter;
  }
  msg::ManualArmPrompt prompt;
  prompt.action = action_code_;
  prompt.step_index = step_index_;
  prompt.hint = (action_code_ == 1) ?
    "遥控到位后按 Enter，再输入抓取点位 0~7" :
    "遥控到位后按 Enter，再输入放置点位 8~15";
  prompt_pub_->publish(prompt);
  last_prompt_pub_ = node_->now();
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: waiting manual confirm (step %u, %s)",
    name().c_str(), step_index_, action_code_ == 1 ? "Pick" : "Place");
}

BT::NodeStatus ManualConfirmNode::onStart()
{
  std::string action_str;
  getInput("action", action_str);
  getInput("timeout", timeout_sec_);
  action_code_ = parseActionCode(action_str);

  {
    std::lock_guard<std::mutex> lock(input_mutex_);
    pending_point_id_.reset();
  }

  prompt_sent_ = false;
  step_index_ = 0;
  arm_slot_id_.clear();
  phase_start_ = node_->now();
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus ManualConfirmNode::onRunning()
{
  rclcpp::spin_some(node_);

  if (!prompt_sent_) {
    publishPrompt(true);
    prompt_sent_ = true;
    phase_start_ = node_->now();
  } else if ((node_->now() - last_prompt_pub_).seconds() >= kPromptRepublishSec) {
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
      setOutput("arm_slot", arm_slot_id_);
      RCLCPP_INFO(
        node_->get_logger(), "%s: confirmed arm_slot='%s'", name().c_str(), arm_slot_id_.c_str());
      return BT::NodeStatus::SUCCESS;
    }
  }

  if ((node_->now() - phase_start_).seconds() > timeout_sec_) {
    RCLCPP_ERROR(node_->get_logger(), "%s: manual confirm timeout", name().c_str());
    return BT::NodeStatus::FAILURE;
  }

  return BT::NodeStatus::RUNNING;
}

void ManualConfirmNode::onHalted()
{
  RCLCPP_WARN(node_->get_logger(), "%s: halted", name().c_str());
}

}  // namespace legged_mission_bt
