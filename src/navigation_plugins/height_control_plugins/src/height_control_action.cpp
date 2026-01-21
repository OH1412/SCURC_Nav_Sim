#include "height_control_plugins/height_control_action.hpp"
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "behaviortree_cpp_v3/bt_factory.h"

namespace height_control_plugins
{

//==============================
// 1. 声明 BT 所需端口（关键补充）
//==============================
BT::PortsList HeightControlAction::providedPorts()
{
  return {
    BT::InputPort<double>("target_height"),
    BT::OutputPort<bool>("height_reached")
  };
}

//==============================
// 2. 构造函数
//==============================
HeightControlAction::HeightControlAction(
  const std::string & xml_tag_name,
  const BT::NodeConfiguration & conf)
: BT::StatefulActionNode(xml_tag_name, conf),
  height_offset_(0.0035),
  first_height_received_(false),
  current_height_(0.0)
{
  if (!config().blackboard->get<rclcpp::Node::SharedPtr>("node", node_)) {
    throw std::runtime_error("无法从黑板中获取ROS节点！");
  }

  // 读取参数
  node_->declare_parameter("height_tolerance", 0.05);
  node_->declare_parameter("lift_speed", 0.10);
  node_->declare_parameter("height_offset", 0.0035);

  node_->get_parameter("height_tolerance", height_tolerance_);
  node_->get_parameter("lift_speed", lift_speed_);
  node_->get_parameter("height_offset", height_offset_);

  // 订阅 /state_estimation
  height_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
    "/state_estimation", 10,
    std::bind(&HeightControlAction::heightCallback, this, std::placeholders::_1));

  // 发布 /cmd_vel（Z轴控制）
  vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);

  RCLCPP_INFO(node_->get_logger(),
    "高度控制插件已加载 | 偏移=%.4f | 容差=%.3f | 速度=%.2f | 监听=/state_estimation",
    height_offset_, height_tolerance_, lift_speed_);
}

//==============================
// 3. 高度订阅回调
//==============================
void HeightControlAction::heightCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
  double raw = msg->pose.pose.position.z;
  current_height_ = raw + height_offset_;

  if (!first_height_received_) {
    first_height_received_ = true;
    RCLCPP_INFO(node_->get_logger(),
      "首次接收到高度: 原始=%.4f 修正=%.4f",
      raw, current_height_);
  }

  RCLCPP_DEBUG(node_->get_logger(),
    "高度更新 | raw=%.4f corrected=%.4f",
    raw, current_height_);
}

//==============================
// 4. 行为树 onStart()
//==============================
BT::NodeStatus HeightControlAction::onStart()
{
  if (!getInput<double>("target_height", target_height_)) {
    RCLCPP_ERROR(node_->get_logger(),
      "行为树未提供必须输入端口 target_height！");
    return BT::NodeStatus::FAILURE;
  }

  RCLCPP_INFO(node_->get_logger(),
    "开始高度控制：目标=%.3f | 当前=%.3f",
    target_height_, current_height_);

  return BT::NodeStatus::RUNNING;
}

//==============================
// 5. 行为树 onRunning()
//==============================
BT::NodeStatus HeightControlAction::onRunning()
{
  if (!first_height_received_) {
    RCLCPP_WARN(node_->get_logger(),
      "尚未接收到 /state_estimation，高度无法控制，等待中...");
    return BT::NodeStatus::RUNNING;
  }

  double diff = target_height_ - current_height_;

  // 已达到目标高度
  if (std::abs(diff) <= height_tolerance_) {
    geometry_msgs::msg::Twist stop;
    stop.linear.z = 0.0;
    vel_pub_->publish(stop);

    setOutput("height_reached", true);

    RCLCPP_INFO(node_->get_logger(),
      "达到目标高度！当前=%.3f 目标=%.3f 误差=%.3f",
      current_height_, target_height_, diff);

    return BT::NodeStatus::SUCCESS;
  }

  // 未达到目标 -> 发布控制速度
  geometry_msgs::msg::Twist cmd;
  // 使用更温和的控制策略，避免过度反应
  double control_effort = std::min(std::abs(diff) * 2.0, lift_speed_); // 比例控制
  cmd.linear.z = (diff > 0) ? control_effort : -control_effort;
  
  // 只控制Z轴，保持其他轴为0
  cmd.linear.x = 0.0;
  cmd.linear.y = 0.0;
  cmd.angular.x = 0.0;
  cmd.angular.y = 0.0;
  cmd.angular.z = 0.0;
  
  vel_pub_->publish(cmd);

  RCLCPP_DEBUG(node_->get_logger(),
    "高度控制中: current=%.3f target=%.3f diff=%.3f vel_z=%.3f",
    current_height_, target_height_, diff, cmd.linear.z);

  return BT::NodeStatus::RUNNING;
}

//==============================
// 6. 行为树 onHalted()
//==============================
void HeightControlAction::onHalted()
{
  geometry_msgs::msg::Twist stop;
  stop.linear.z = 0.0;
  vel_pub_->publish(stop);

  RCLCPP_WARN(node_->get_logger(),
    "高度控制被强制终止，当前高度=%.3f", current_height_);
}

}  // namespace height_control_plugins



//==============================
// 7. 插件注册（必须有）
//==============================
#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default")))
void BT_RegisterNodesFromPlugin(BT::BehaviorTreeFactory & factory)
{
  factory.registerNodeType<height_control_plugins::HeightControlAction>("HeightControlAction");
}

#ifdef __cplusplus
}
#endif
