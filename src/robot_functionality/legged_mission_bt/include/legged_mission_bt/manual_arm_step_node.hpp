#pragma once

#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <optional>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <legged_mission_bt/msg/arm_pose_request.hpp>
#include <legged_mission_bt/msg/manual_arm_input.hpp>
#include <legged_mission_bt/msg/manual_arm_prompt.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <std_msgs/msg/u_int8_multi_array.hpp>

#include "legged_mission_bt/waypoint_registry.hpp"

namespace legged_mission_bt
{

class ManualArmStepNode : public BT::StatefulActionNode
{
public:
  ManualArmStepNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node,
    std::shared_ptr<WaypointRegistry> registry,
    uint8_t action_code,
    uint8_t expected_ack_state);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  enum class Phase
  {
    WAIT_MANUAL,
    REQUEST_ARM,
    WAIT_ARM_WP,
    WAIT_ARM_ACK,
  };

  void onManualInput(const msg::ManualArmInput::SharedPtr msg);
  void publishPrompt(bool bump_step_index);
  void publishArmRequest();
  void publishArmCommand();
  void onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg);
  bool waitForCommandSubscriber(double max_wait_sec);
  static uint8_t parseActionCode(const std::string & action);

  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<WaypointRegistry> registry_;

  rclcpp::Publisher<msg::ManualArmPrompt>::SharedPtr prompt_pub_;
  rclcpp::Publisher<msg::ArmPoseRequest>::SharedPtr arm_request_pub_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr cmd_pub_;
  rclcpp::Subscription<msg::ManualArmInput>::SharedPtr input_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt8MultiArray>::SharedPtr status_sub_;

  uint8_t action_code_{1};
  uint8_t expected_ack_state_{0x01};
  Phase phase_{Phase::WAIT_MANUAL};

  bool prompt_sent_{false};
  uint8_t step_index_{0};
  rclcpp::Time last_prompt_pub_;
  static constexpr double kPromptRepublishSec = 3.0;
  std::mutex input_mutex_;
  std::optional<uint8_t> pending_point_id_;

  std::string arm_slot_id_;
  ArmWaypoint arm_wp_;
  double timeout_sec_{120.0};
  double waypoint_wait_timeout_{120.0};
  rclcpp::Time phase_start_;
  rclcpp::Time arm_cmd_time_;

  std::atomic<bool> ack_received_{false};
  std::atomic<bool> ack_success_{false};
};

}  // namespace legged_mission_bt
