#pragma once

#include <atomic>
#include <memory>
#include <mutex>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <rclcpp/rclcpp.hpp>
#include <legged_mission_bt/msg/arm_pose_request.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <std_msgs/msg/u_int8_multi_array.hpp>

#include "legged_mission_bt/waypoint_registry.hpp"

namespace legged_mission_bt
{

class ArmActionNode : public BT::StatefulActionNode
{
public:
  ArmActionNode(
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
  /// Serial ACK (state=0x03): serial port confirmed command receipt → stop republishing
  void onSerialAck(const std_msgs::msg::UInt8MultiArray::SharedPtr msg);
  /// Arm behavior ACK (state=0x01 Pick / 0x02 Place): arm completed action → BT SUCCESS
  void onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg);
  bool waitForCommandSubscriber(double max_wait_sec);
  bool resolveCoords();
  void publishArmPoseRequest();
  void publishCommand();

  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<WaypointRegistry> registry_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr cmd_pub_;
  rclcpp::Publisher<legged_mission_bt::msg::ArmPoseRequest>::SharedPtr arm_request_pub_;
  rclcpp::Subscription<std_msgs::msg::UInt8MultiArray>::SharedPtr serial_ack_sub_;
  rclcpp::Subscription<std_msgs::msg::UInt8MultiArray>::SharedPtr status_sub_;

  uint8_t action_code_;
  uint8_t expected_ack_state_;

  std::string arm_command_topic_;
  std::string arm_serial_ack_topic_;
  std::string arm_status_topic_;

  double x_mm_{0.0};
  double y_mm_{0.0};
  double z_mm_{0.0};
  double yaw_{0.0};
  double timeout_sec_{30.0};

  rclcpp::Time start_time_;
  rclcpp::Time last_publish_time_;
  double arm_republish_interval_{0.01};
  std::mutex ack_mutex_;
  std::atomic<bool> serial_ack_received_{false};
  std::atomic<bool> ack_received_{false};
  std::atomic<bool> ack_success_{false};

  bool waiting_for_wp_{false};
  bool arm_request_sent_{false};
  std::string wp_id_;
  std::string nav_ref_id_;
  uint8_t arm_point_id_{0};
  rclcpp::Time resolve_start_;
  double waypoint_wait_timeout_{120.0};
};

}  // namespace legged_mission_bt
