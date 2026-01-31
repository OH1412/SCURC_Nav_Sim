#include "fly_step_mission/descend_node.hpp"

using namespace std::chrono_literals;

DescendNode::DescendNode(const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node
) : BT::StatefulActionNode(name, config),
  node_(std::move(node))

{
  // 垂直速度发布到 cmd_vel
  vel_pub_ = node_->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", 10);

  // TF buffer + listener，用来查 map -> base_link 的 z
  tf_buffer_ = std::make_shared<tf2_ros::Buffer>(node_->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
}

BT::PortsList DescendNode::providedPorts()
{
  return{
    BT::InputPort<double>("z_target"),
    BT::InputPort<double>("z_speed"),
    BT::InputPort<double>("max_duration"),
    BT::InputPort<std::string>("global_frame", "map"),
    BT::InputPort<std::string>("robot_frame","base_link")
  };
}

BT::NodeStatus DescendNode::onStart()
{
  // 读取必需的输入端口
  if (!getInput("z_target", z_target_) ||
      !getInput("z_speed", z_speed_) ||
      !getInput("max_duration", max_duration_))
  {
    RCLCPP_ERROR(node_->get_logger(), "DescendNode: missing required input ports");
    return BT::NodeStatus::FAILURE;
  }

  // 可选覆盖 frame 名
  getInput("global_frame", global_frame_);
  getInput("robot_frame", robot_frame_);

  start_time_ = node_->now();

  double z_now;
  if (!getCurrentZ(z_now)) {
    RCLCPP_ERROR(node_->get_logger(), "DescendNode: cannot read current Z");
    return BT::NodeStatus::FAILURE;
  }

  RCLCPP_INFO(node_->get_logger(),
    "DescendNode: start, z_now=%.3f, z_target=%.3f, z_speed=%.3f, max_duration=%.2f",
    z_now, z_target_, z_speed_, max_duration_);

  // 如果已经在目标之下，就直接成功
  if (z_now <= z_target_) {
    RCLCPP_INFO(node_->get_logger(), "DescendNode: already below target height");
    return BT::NodeStatus::SUCCESS;
  }

  publishZ(-z_speed_);
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus DescendNode::onRunning()
{
  // 1. 超时检查
  double elapsed = (node_->now() - start_time_).seconds();
  if (elapsed > max_duration_) {
    RCLCPP_WARN(node_->get_logger(),
      "DescendNode: timeout (elapsed=%.2f > max_duration=%.2f), stop and FAIL",
      elapsed, max_duration_);
    publishZ(0.0);
    return BT::NodeStatus::FAILURE;
  }

  // 2. 读取当前高度
  double z_now;
  if (!getCurrentZ(z_now)) {
    RCLCPP_ERROR(node_->get_logger(),
      "DescendNode: failed to read current Z during running, stop and FAIL");
    publishZ(0.0);
    return BT::NodeStatus::FAILURE;
  }

  // 3. 是否达到目标高度
  const double eps = 0.01;
  if (z_now <= z_target_ + eps) {
    RCLCPP_INFO(node_->get_logger(),
      "DescendNode: reached target height, z_now=%.3f, z_target=%.3f",
      z_now, z_target_);
    publishZ(0.0);
    return BT::NodeStatus::SUCCESS;
  }

  publishZ(-z_speed_);
  return BT::NodeStatus::RUNNING;
}

void DescendNode::onHalted()
{
  RCLCPP_WARN(node_->get_logger(), "DescendNode: halted, stop vertical motion");
  publishZ(0.0);
}

bool DescendNode::getCurrentZ(double & z_out)
{
  try {
    // 等待 TF 可用，最多等待 5 秒
    if (!tf_buffer_->canTransform(global_frame_, robot_frame_, tf2::TimePointZero, 5s)) {
      RCLCPP_WARN(node_->get_logger(),
        "DescendNode: TF not available after 5s (%s -> %s)",
        global_frame_.c_str(), robot_frame_.c_str());
      return false;
    }

    auto tf = tf_buffer_->lookupTransform(
      global_frame_, robot_frame_, tf2::TimePointZero);
    
    z_out = tf.transform.translation.z;
    return true;
  }
  catch (const tf2::TransformException & ex) {
    RCLCPP_WARN(node_->get_logger(),
      "DescendNode: TF lookup failed (%s -> %s): %s",
      global_frame_.c_str(), robot_frame_.c_str(), ex.what());
    return false;
  }
}

void DescendNode::publishZ(double z_vel)
{
  geometry_msgs::msg::Twist cmd;
  cmd.linear.z = z_vel;
  vel_pub_->publish(cmd);
}