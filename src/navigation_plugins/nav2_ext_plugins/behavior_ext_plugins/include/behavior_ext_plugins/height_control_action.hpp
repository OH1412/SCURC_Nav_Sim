#ifndef BEHAVIOR_EXT_PLUGINS_HEIGHT_CONTROL_ACTION_HPP_
#define BEHAVIOR_EXT_PLUGINS_HEIGHT_CONTROL_ACTION_HPP_

#include "behaviortree_cpp_v3/behavior_tree.h"
#include "behaviortree_cpp_v3/bt_factory.h"
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"

namespace behavior_ext_plugins
{

class HeightControlAction : public BT::StatefulActionNode
{
public:
  HeightControlAction(
    const std::string & xml_tag_name,
    const BT::NodeConfiguration & conf);

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<double>("target_height", "目标高度（米）"),
      BT::OutputPort<bool>("height_reached", "是否到达目标高度")
    };
  }

private:
  void heightCallback(const nav_msgs::msg::Odometry::SharedPtr msg);

  rclcpp::Node::SharedPtr node_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr height_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
  
  double height_tolerance_;   // 高度容差
  double lift_speed_;         // 升降速度
  double height_offset_;      // 高度偏移
  double current_height_;     // 当前高度
  double target_height_;      // 目标高度
  bool first_height_received_; // 新增：标记是否首次接收高度数据
};

}  // namespace behavior_ext_plugins

#endif  // BEHAVIOR_EXT_PLUGINS_HEIGHT_CONTROL_ACTION_HPP_
