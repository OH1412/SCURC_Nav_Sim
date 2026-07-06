#pragma once

#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <legged_mission_bt/msg/manual_arm_input.hpp>
#include <legged_mission_bt/msg/manual_arm_prompt.hpp>
#include <rclcpp/rclcpp.hpp>

#include "legged_mission_bt/waypoint_registry.hpp"

namespace legged_mission_bt
{

/** 仅负责终端确认 + 选择 arm_point_id，执行交给 ArmPickNode/ArmPlaceNode。 */
class ManualConfirmNode : public BT::StatefulActionNode
{
public:
  ManualConfirmNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  void onManualInput(const msg::ManualArmInput::SharedPtr msg);
  void publishPrompt(bool bump_step_index);
  static uint8_t parseActionCode(const std::string & action);

  std::shared_ptr<rclcpp::Node> node_;
  rclcpp::Publisher<msg::ManualArmPrompt>::SharedPtr prompt_pub_;
  rclcpp::Subscription<msg::ManualArmInput>::SharedPtr input_sub_;

  uint8_t action_code_{1};
  uint8_t step_index_{0};
  bool prompt_sent_{false};
  rclcpp::Time last_prompt_pub_;
  rclcpp::Time phase_start_;
  double timeout_sec_{300.0};
  static constexpr double kPromptRepublishSec = 3.0;

  std::mutex input_mutex_;
  std::optional<uint8_t> pending_point_id_;
  std::string arm_slot_id_;
};

}  // namespace legged_mission_bt
