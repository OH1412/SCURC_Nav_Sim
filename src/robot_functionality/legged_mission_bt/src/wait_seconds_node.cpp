#include "legged_mission_bt/wait_seconds_node.hpp"

WaitSecondsNode::WaitSecondsNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node)
: BT::StatefulActionNode(name, config),
  node_(std::move(node))
{
}

BT::PortsList WaitSecondsNode::providedPorts()
{
  return {
    BT::InputPort<double>("duration", "Wait duration in seconds"),
  };
}

BT::NodeStatus WaitSecondsNode::onStart()
{
  if (!getInput("duration", duration_sec_) || duration_sec_ < 0.0) {
    RCLCPP_ERROR(node_->get_logger(), "WaitSecondsNode: invalid duration");
    return BT::NodeStatus::FAILURE;
  }
  start_time_ = node_->now();
  RCLCPP_INFO(node_->get_logger(), "WaitSecondsNode: waiting %.1fs", duration_sec_);
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus WaitSecondsNode::onRunning()
{
  rclcpp::spin_some(node_);
  const double elapsed = (node_->now() - start_time_).seconds();
  if (elapsed >= duration_sec_) {
    RCLCPP_INFO(node_->get_logger(), "WaitSecondsNode: done");
    return BT::NodeStatus::SUCCESS;
  }
  return BT::NodeStatus::RUNNING;
}

void WaitSecondsNode::onHalted()
{
  RCLCPP_WARN(node_->get_logger(), "WaitSecondsNode: halted");
}
