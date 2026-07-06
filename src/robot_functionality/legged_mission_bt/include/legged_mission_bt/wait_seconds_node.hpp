#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <rclcpp/rclcpp.hpp>

class WaitSecondsNode : public BT::StatefulActionNode
{
public:
  WaitSecondsNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  std::shared_ptr<rclcpp::Node> node_;
  rclcpp::Time start_time_;
  double duration_sec_{0.0};
};
