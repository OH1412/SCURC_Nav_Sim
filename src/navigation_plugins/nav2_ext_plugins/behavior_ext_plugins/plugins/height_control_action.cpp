// #include "behavior_ext_plugins/height_control_action.hpp"
// #include "rclcpp/rclcpp.hpp"
// #include "rclcpp/logging.hpp"
// #include "std_msgs/msg/float64.hpp"
// #include "geometry_msgs/msg/twist.hpp"
// #include "nav_msgs/msg/odometry.hpp"  // 新增：Odometry消息头文件
// #include "behaviortree_cpp_v3/bt_factory.h"


// namespace behavior_ext_plugins
// {

// HeightControlAction::HeightControlAction(
//   const std::string & xml_tag_name,
//   const BT::NodeConfiguration & conf)
// : BT::StatefulActionNode(xml_tag_name, conf),
//   height_offset_(0.0035)  // 初始化高度偏移（修正初始z值为负的问题）
// {
//   if (!config().blackboard->get<rclcpp::Node::SharedPtr>("node", node_)) {
//     throw std::runtime_error("无法从黑板获取ROS节点指针！");
//   }

//   // 声明参数（新增height_offset可选参数）
//   node_->declare_parameter("height_tolerance", 0.05);
//   node_->declare_parameter("lift_speed", 0.1);
//   node_->declare_parameter("height_offset", 0.0035);  // 新增：高度偏移参数
//   node_->get_parameter("height_tolerance", height_tolerance_);
//   node_->get_parameter("lift_speed", lift_speed_);
//   node_->get_parameter("height_offset", height_offset_);  // 读取偏移参数

//   // 替换：订阅/state_estimation（Odometry类型），替代原/robot/height
//   height_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
//     "/state_estimation", 10,
//     std::bind(&HeightControlAction::heightCallback, this, std::placeholders::_1)
//   );

//   vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);

//   RCLCPP_INFO(
//     node_->get_logger(),
//     "高度控制节点初始化完成 | 高度偏移=%.4f米",
//     height_offset_
//   );
// }

// // 修改：回调函数参数改为Odometry，提取z轴高度
// void HeightControlAction::heightCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
// {
//   // 提取原始z轴高度 + 偏移修正（可选，根据实际需求调整）
//   current_height_ = msg->pose.pose.position.z + height_offset_;
  
//   // 可选调试日志（发布频率高时建议注释）
//   RCLCPP_DEBUG(
//     node_->get_logger(),
//     "原始z值=%.6f → 修正后高度=%.6f",
//     msg->pose.pose.position.z, current_height_
//   );
// }

// BT::NodeStatus HeightControlAction::onStart()
// {
//   if (!getInput<double>("target_height", target_height_)) {
//     RCLCPP_ERROR(node_->get_logger(), "行为树中未配置'target_height'！");
//     return BT::NodeStatus::FAILURE;
//   }

//   RCLCPP_INFO(
//     node_->get_logger(),
//     "开始高度控制：目标=%.2f米，容差=%.2f米，速度=%.2f米/秒",
//     target_height_, height_tolerance_, lift_speed_
//   );

//   return BT::NodeStatus::RUNNING;
// }

// BT::NodeStatus HeightControlAction::onRunning()
// {
//   double height_diff = target_height_ - current_height_;

//   if (std::abs(height_diff) <= height_tolerance_) {
//     geometry_msgs::msg::Twist vel_msg;
//     vel_msg.linear.z = 0.0;
//     vel_pub_->publish(vel_msg);

//     setOutput("height_reached", true);
//     RCLCPP_INFO(
//       node_->get_logger(),
//       "到达目标高度：当前=%.2f米，目标=%.2f米",
//       current_height_, target_height_
//     );
//     return BT::NodeStatus::SUCCESS;
//   }

//   geometry_msgs::msg::Twist vel_msg;
//   vel_msg.linear.z = (height_diff > 0) ? lift_speed_ : -lift_speed_;
//   vel_pub_->publish(vel_msg);

//   RCLCPP_DEBUG(
//     node_->get_logger(),
//     "高度控制中：当前=%.2f米，目标=%.2f米，差值=%.2f米",
//     current_height_, target_height_, height_diff
//   );

//   return BT::NodeStatus::RUNNING;
// }

// void HeightControlAction::onHalted()
// {
//   geometry_msgs::msg::Twist vel_msg;
//   vel_msg.linear.z = 0.0;
//   vel_pub_->publish(vel_msg);
//   RCLCPP_WARN(node_->get_logger(), "高度控制被终止");
// }

// // 声明成员变量（若头文件未声明，需补充）
// // （注：需确保height_control_action.hpp中包含以下成员变量声明）
// // rclcpp::Node::SharedPtr node_;
// // rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr height_sub_;  // 修改后的类型
// // rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
// // double height_tolerance_;
// // double lift_speed_;
// // double height_offset_;  // 新增：高度偏移
// // double current_height_;
// // double target_height_;

// }  // namespace behavior_ext_plugins


// #include "behaviortree_cpp_v3/loggers/bt_zmq_publisher.h"

// // 关键修改：添加符号可见性声明，确保函数被导出
// #ifdef __cplusplus
// extern "C" {
// #endif

// __attribute__((visibility("default")))
// void BT_RegisterNodesFromPlugin(BT::BehaviorTreeFactory& factory)
// {
//   factory.registerNodeType<behavior_ext_plugins::HeightControlAction>("HeightControlAction");
// }

// #ifdef __cplusplus
// }
// #endif


#include "behavior_ext_plugins/height_control_action.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp/logging.hpp"
#include "std_msgs/msg/float64.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"  // 新增：Odometry消息头文件
#include "behaviortree_cpp_v3/bt_factory.h"


namespace behavior_ext_plugins
{

HeightControlAction::HeightControlAction(
  const std::string & xml_tag_name,
  const BT::NodeConfiguration & conf)
: BT::StatefulActionNode(xml_tag_name, conf),
  height_offset_(0.0035),  // 初始化高度偏移（修正初始z值为负的问题）
  first_height_received_(false)  // 新增：标记是否首次接收高度
{
  if (!config().blackboard->get<rclcpp::Node::SharedPtr>("node", node_)) {
    throw std::runtime_error("无法从黑板获取ROS节点指针！");
  }

  // 声明参数（新增height_offset可选参数）
  node_->declare_parameter("height_tolerance", 0.05);
  node_->declare_parameter("lift_speed", 0.1);
  node_->declare_parameter("height_offset", 0.0035);  // 新增：高度偏移参数
  node_->get_parameter("height_tolerance", height_tolerance_);
  node_->get_parameter("lift_speed", lift_speed_);
  node_->get_parameter("height_offset", height_offset_);  // 读取偏移参数

  // 替换：订阅/state_estimation（Odometry类型），替代原/robot/height
  height_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
    "/state_estimation", 10,
    std::bind(&HeightControlAction::heightCallback, this, std::placeholders::_1)
  );

  vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);

  RCLCPP_INFO(
    node_->get_logger(),
    "高度控制节点初始化完成 | 高度偏移=%.4f米 | 监听话题=/state_estimation",
    height_offset_
  );
}

// 修改：回调函数中新增详细日志，输出接收到的z轴高度
void HeightControlAction::heightCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
  // 提取原始z轴高度（从/state_estimation直接读取）
  double raw_z = msg->pose.pose.position.z;
  // 修正后高度（偏移+原始值）
  current_height_ = raw_z + height_offset_;
  
  // 新增：首次接收高度时打印提示（避免日志刷屏）
  if (!first_height_received_) {
    RCLCPP_INFO(
      node_->get_logger(),
      "✅ 首次接收到z轴高度数据！\n"
      "   原始z值（/state_estimation）: %.6f 米\n"
      "   修正后高度（偏移+%.4f）: %.6f 米",
      raw_z, height_offset_, current_height_
    );
    first_height_received_ = true;
  }

  // 新增：持续打印高度数据（用DEBUG级别，可通过日志级别控制是否输出）
  RCLCPP_DEBUG(
    node_->get_logger(),
    "📌 接收z轴高度 | 原始值=%.6f | 修正后=%.6f 米",
    raw_z, current_height_
  );
}

BT::NodeStatus HeightControlAction::onStart()
{
  // 新增：检查是否接收到高度数据
  if (!first_height_received_) {
    RCLCPP_WARN(
      node_->get_logger(),
      "⚠️  尚未接收到/state_estimation的z轴高度数据！请检查话题是否发布"
    );
    // 可选：返回FAILURE或继续等待，这里选择继续等待
    // return BT::NodeStatus::FAILURE;
  }

  if (!getInput<double>("target_height", target_height_)) {
    RCLCPP_ERROR(node_->get_logger(), "行为树中未配置'target_height'！");
    return BT::NodeStatus::FAILURE;
  }

  RCLCPP_INFO(
    node_->get_logger(),
    "🚀 开始高度控制：\n"
    "   目标高度=%.2f米 | 容差=%.2f米 | 升降速度=%.2f米/秒\n"
    "   当前初始高度=%.6f米",
    target_height_, height_tolerance_, lift_speed_, current_height_
  );

  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus HeightControlAction::onRunning()
{
  // 新增：实时打印高度控制过程中的z轴数据
  double height_diff = target_height_ - current_height_;

  RCLCPP_INFO_THROTTLE(
    node_->get_logger(), *node_->get_clock(), 1000,  // 每1秒打印一次（避免刷屏）
    "📊 高度控制中 | 当前高度=%.6f米 | 目标=%.2f米 | 差值=%.6f米",
    current_height_, target_height_, height_diff
  );

  if (std::abs(height_diff) <= height_tolerance_) {
    geometry_msgs::msg::Twist vel_msg;
    vel_msg.linear.z = 0.0;
    vel_pub_->publish(vel_msg);

    setOutput("height_reached", true);
    RCLCPP_INFO(
      node_->get_logger(),
      "🎉 到达目标高度！\n"
      "   当前高度=%.6f米 | 目标=%.2f米 | 误差=%.6f米（≤容差%.2f米）",
      current_height_, target_height_, std::abs(height_diff), height_tolerance_
    );
    return BT::NodeStatus::SUCCESS;
  }

  geometry_msgs::msg::Twist vel_msg;
  vel_msg.linear.z = (height_diff > 0) ? lift_speed_ : -lift_speed_;
  vel_pub_->publish(vel_msg);

  RCLCPP_DEBUG(
    node_->get_logger(),
    "🔄 发布升降速度：linear.z=%.2f米/秒",
    vel_msg.linear.z
  );

  return BT::NodeStatus::RUNNING;
}

void HeightControlAction::onHalted()
{
  geometry_msgs::msg::Twist vel_msg;
  vel_msg.linear.z = 0.0;
  vel_pub_->publish(vel_msg);
  RCLCPP_WARN(
    node_->get_logger(),
    "🛑 高度控制被终止 | 最后接收的z轴高度=%.6f米",
    current_height_
  );
}

// 新增：补充成员变量声明（需同步到头文件）
// bool first_height_received_;  // 标记是否首次接收高度

}  // namespace behavior_ext_plugins


#include "behaviortree_cpp_v3/loggers/bt_zmq_publisher.h"

// 关键修改：添加符号可见性声明，确保函数被导出
#ifdef __cplusplus
extern "C" {
#endif

__attribute__((visibility("default")))
void BT_RegisterNodesFromPlugin(BT::BehaviorTreeFactory& factory)
{
  factory.registerNodeType<behavior_ext_plugins::HeightControlAction>("HeightControlAction");
}

#ifdef __cplusplus
}
#endif
