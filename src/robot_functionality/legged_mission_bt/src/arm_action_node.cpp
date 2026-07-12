#include "legged_mission_bt/arm_action_node.hpp"

#include <chrono>
#include <sstream>
#include <stdexcept>
#include <thread>

#include "legged_bringup/mission_log.hpp"

using namespace std::chrono_literals;

namespace legged_mission_bt
{

ArmActionNode::ArmActionNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node,
  std::shared_ptr<WaypointRegistry> registry,
  uint8_t action_code,
  uint8_t expected_ack_state)
: BT::StatefulActionNode(name, config),
  node_(std::move(node)),
  registry_(std::move(registry)),
  action_code_(action_code),
  expected_ack_state_(expected_ack_state)
{
  if (!node_->has_parameter("arm_command_topic")) {
    node_->declare_parameter("arm_command_topic", "/arm_command");
  }
  if (!node_->has_parameter("arm_status_topic")) {
    node_->declare_parameter("arm_status_topic", "/arm_status");
  }
  if (!node_->has_parameter("arm_serial_ack_topic")) {
    node_->declare_parameter("arm_serial_ack_topic", "/arm_serial_ack");
  }
  if (!node_->has_parameter("waypoint_wait_timeout")) {
    node_->declare_parameter("waypoint_wait_timeout", 120.0);
  }
  if (!node_->has_parameter("arm_republish_interval")) {
    node_->declare_parameter("arm_republish_interval", 0.01);
  }
  arm_command_topic_ = node_->get_parameter("arm_command_topic").as_string();
  arm_status_topic_ = node_->get_parameter("arm_status_topic").as_string();
  arm_serial_ack_topic_ = node_->get_parameter("arm_serial_ack_topic").as_string();
  waypoint_wait_timeout_ = node_->get_parameter("waypoint_wait_timeout").as_double();
  arm_republish_interval_ = node_->get_parameter("arm_republish_interval").as_double();
  if (!node_->has_parameter("arm_pose_request_topic")) {
    node_->declare_parameter("arm_pose_request_topic", "/mission_bt/arm_pose_request");
  }
  const auto arm_request_topic = node_->get_parameter("arm_pose_request_topic").as_string();

  auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();
  cmd_pub_ = node_->create_publisher<std_msgs::msg::Float64MultiArray>(arm_command_topic_, qos);
  arm_request_pub_ = node_->create_publisher<legged_mission_bt::msg::ArmPoseRequest>(
    arm_request_topic, qos);
  // Serial ACK: state=0x03 = serial port confirmed receipt → stops republishing
  serial_ack_sub_ = node_->create_subscription<std_msgs::msg::UInt8MultiArray>(
    arm_serial_ack_topic_, qos,
    std::bind(&ArmActionNode::onSerialAck, this, std::placeholders::_1));
  // Arm behavior ACK: state=0x01/0x02 = arm completed action → BT SUCCESS
  status_sub_ = node_->create_subscription<std_msgs::msg::UInt8MultiArray>(
    arm_status_topic_, qos,
    std::bind(&ArmActionNode::onArmStatus, this, std::placeholders::_1));
}

BT::PortsList ArmActionNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("wp_id", "", "Arm slot id (deprecated: use arm_point_id)"),
    BT::InputPort<std::string>("arm_point_id", "", "Arm slot: 0~7 pick, 8~15 place"),
    BT::InputPort<std::string>("nav_ref_id", "", "Associated nav wp_id"),
    BT::InputPort<double>("x", "Arm X in mm (inline mode)"),
    BT::InputPort<double>("y", "Arm Y in mm (inline mode)"),
    BT::InputPort<double>("z", "Arm Z in mm (inline mode)"),
    BT::InputPort<double>("yaw", 0.0, "Arm yaw in radians"),
    BT::InputPort<double>("timeout", 30.0, "ACK wait timeout in seconds"),
  };
}

bool ArmActionNode::resolveCoords()
{
  std::string arm_point_id_str;
  getInput("arm_point_id", arm_point_id_str);
  if (!arm_point_id_str.empty()) {
    wp_id_ = arm_point_id_str;
    try {
      const unsigned long slot = std::stoul(arm_point_id_str);
      arm_point_id_ = (slot <= 255) ? static_cast<uint8_t>(slot) : 0;
    } catch (const std::exception &) {
      arm_point_id_ = 0;
    }
  } else {
    getInput("wp_id", wp_id_);
    arm_point_id_ = 0;
  }

  getInput("nav_ref_id", nav_ref_id_);

  if (!wp_id_.empty()) {
    ArmWaypoint wp;
    if (registry_ && registry_->tryGetArm(wp_id_, wp)) {
      x_mm_ = wp.x;
      y_mm_ = wp.y;
      z_mm_ = wp.z;
      yaw_ = wp.yaw;
      RCLCPP_INFO(
        node_->get_logger(),
        "%s: resolved wp_id='%s' → (%.1f, %.1f, %.1f, yaw=%.3f)",
        name().c_str(), wp_id_.c_str(), x_mm_, y_mm_, z_mm_, yaw_);
      return true;
    }
    return false;
  }

  if (!getInput("x", x_mm_) ||
    !getInput("y", y_mm_) ||
    !getInput("z", z_mm_))
  {
    RCLCPP_ERROR(
      node_->get_logger(), "%s: provide wp_id or inline x/y/z", name().c_str());
    return false;
  }
  getInput("yaw", yaw_);
  return true;
}

void ArmActionNode::publishArmPoseRequest()
{
  getInput("nav_ref_id", nav_ref_id_);

  uint8_t point_id = arm_point_id_;
  if (point_id == 0 && !wp_id_.empty()) {
    try {
      const unsigned long slot = std::stoul(wp_id_);
      if (slot <= 255) {
        point_id = static_cast<uint8_t>(slot);
      }
    } catch (const std::exception &) {
      point_id = 0;
    }
  }

  legged_mission_bt::msg::ArmPoseRequest msg;
  msg.arm_point_id = point_id;
  msg.nav_id = nav_ref_id_;

  arm_request_pub_->publish(msg);
  std::ostringstream detail;
  detail << "节点=" << name() << " 机械臂点位=" << static_cast<unsigned>(msg.arm_point_id)
         << " 关联导航点=" << msg.nav_id;
  legged_bringup::mission_log::publish(
    *node_, "ArmActionNode", "ARM_POSE_REQUEST_PUBLISHED", "INFO", detail.str());
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: published arm_pose_request arm_point=%u nav_id='%s'",
    name().c_str(), msg.arm_point_id, msg.nav_id.c_str());
}

BT::NodeStatus ArmActionNode::onStart()
{
  waiting_for_wp_ = false;
  getInput("timeout", timeout_sec_);

  const char * step_name = (action_code_ == 1) ? "抓取" : "放置";
  std::ostringstream start_detail;
  start_detail << "节点=" << name() << " 步骤=" << step_name
               << " 超时=" << timeout_sec_ << "秒";

  // Resolve arm_point_id / wp_id first (need wp_id_ for mode decision)
  {
    std::string arm_point_id_str;
    getInput("arm_point_id", arm_point_id_str);
    if (!arm_point_id_str.empty()) {
      wp_id_ = arm_point_id_str;
      try {
        const unsigned long slot = std::stoul(arm_point_id_str);
        arm_point_id_ = (slot <= 255) ? static_cast<uint8_t>(slot) : 0;
      } catch (const std::exception &) {
        arm_point_id_ = 0;
      }
    } else {
      getInput("wp_id", wp_id_);
      arm_point_id_ = 0;
    }
    getInput("nav_ref_id", nav_ref_id_);
  }

  start_detail << " 机械臂点位=" << wp_id_ << " 关联导航点=" << nav_ref_id_;
  legged_bringup::mission_log::publish(
    *node_, "ArmActionNode", "ARM_STEP_START", "INFO", start_detail.str());

  // ── inline mode (x/y/z ports, no wp_id) ──
  if (wp_id_.empty()) {
    if (!getInput("x", x_mm_) ||
        !getInput("y", y_mm_) ||
        !getInput("z", z_mm_)) {
      RCLCPP_ERROR(
        node_->get_logger(), "%s: provide wp_id or inline x/y/z", name().c_str());
      return BT::NodeStatus::FAILURE;
    }
    getInput("yaw", yaw_);

    serial_ack_received_.store(false);
    ack_received_.store(false);
    ack_success_.store(false);
    start_time_ = node_->now();

    if (!waitForCommandSubscriber(5.0)) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "%s: no subscriber on %s after 5s (count=%zu). Is serial_cmd_sender running?",
        name().c_str(), arm_command_topic_.c_str(), cmd_pub_->get_subscription_count());
      legged_bringup::mission_log::publish(
        *node_, "ArmActionNode", "ARM_COMMAND_NO_SUBSCRIBER", "ERROR",
        std::string("话题=") + arm_command_topic_ + " 无订阅者");
      return BT::NodeStatus::FAILURE;
    }

    publishCommand();
    return BT::NodeStatus::RUNNING;
  }

  // ── wp_id mode: always clear cache and request FRESH coords from broadcaster ──
  waiting_for_wp_ = true;
  arm_request_sent_ = false;
  resolve_start_ = node_->now();
  if (registry_) {
    registry_->clearArm(wp_id_);
  }
  publishArmPoseRequest();
  arm_request_sent_ = true;
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: waiting for arm wp_id='%s' on /mission_bt/arm_waypoint (up to %.0fs)...",
    name().c_str(), wp_id_.c_str(), waypoint_wait_timeout_);
  return BT::NodeStatus::RUNNING;
}

bool ArmActionNode::waitForCommandSubscriber(double max_wait_sec)
{
  const auto deadline = node_->now() + rclcpp::Duration::from_seconds(max_wait_sec);
  while (rclcpp::ok() && node_->now() < deadline) {
    rclcpp::spin_some(node_);
    if (cmd_pub_->get_subscription_count() > 0) {
      return true;
    }
    std::this_thread::sleep_for(50ms);
  }
  rclcpp::spin_some(node_);
  return cmd_pub_->get_subscription_count() > 0;
}

void ArmActionNode::publishCommand()
{
  const double serial_x = x_mm_;
  const double serial_y = y_mm_;

  std_msgs::msg::Float64MultiArray msg;
  msg.data = {serial_x, serial_y, z_mm_, yaw_, static_cast<double>(action_code_)};
  cmd_pub_->publish(msg);
  last_publish_time_ = node_->now();

  const char * action_name = (action_code_ == 1) ? "抓取" : "放置";
  std::ostringstream detail;
  detail << "节点=" << name() << " 动作=" << action_name
         << " 话题=" << arm_command_topic_
         << " 行为树坐标(mm)=(" << x_mm_ << ',' << y_mm_ << ',' << z_mm_ << ",航向=" << yaw_ << "弧度)"
         << " 串口坐标(mm)=(" << serial_x << ',' << serial_y << ',' << z_mm_ << ",航向=" << yaw_
         << ",动作码=" << static_cast<int>(action_code_) << ')';
  legged_bringup::mission_log::publish(
    *node_, "ArmActionNode", "ARM_COMMAND_SENT", "INFO", detail.str());
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: sent %s to %s (subs=%zu): BT(x=%.1f, y=%.1f) → serial(x=%.1f, y=%.1f, z=%.1f, yaw=%.3f, action=%.0f)",
    name().c_str(), action_name, arm_command_topic_.c_str(),
    cmd_pub_->get_subscription_count(),
    x_mm_, y_mm_, serial_x, serial_y, z_mm_, yaw_, static_cast<double>(action_code_));
}

BT::NodeStatus ArmActionNode::onRunning()
{
  rclcpp::spin_some(node_);

  if (waiting_for_wp_) {
    if (!arm_request_sent_) {
      if (registry_) {
        registry_->clearArm(wp_id_);
      }
      publishArmPoseRequest();
      arm_request_sent_ = true;
    }
    if (resolveCoords()) {
      waiting_for_wp_ = false;
      serial_ack_received_.store(false);
      ack_received_.store(false);
      ack_success_.store(false);
      start_time_ = node_->now();

      if (!waitForCommandSubscriber(5.0)) {
        RCLCPP_ERROR(
          node_->get_logger(),
          "%s: no subscriber on %s after 5s",
          name().c_str(), arm_command_topic_.c_str());
        legged_bringup::mission_log::publish(
          *node_, "ArmActionNode", "ARM_COMMAND_NO_SUBSCRIBER", "ERROR",
          std::string("话题=") + arm_command_topic_ + " 无订阅者");
        return BT::NodeStatus::FAILURE;
      }

      publishCommand();
    } else {
      const double elapsed = (node_->now() - resolve_start_).seconds();
      if (elapsed > waypoint_wait_timeout_) {
        RCLCPP_ERROR(
          node_->get_logger(),
          "%s: timeout waiting for arm wp_id='%s' (%.0fs)",
          name().c_str(), wp_id_.c_str(), waypoint_wait_timeout_);
        legged_bringup::mission_log::publish(
          *node_, "ArmActionNode", "ARM_WAYPOINT_TIMEOUT", "ERROR",
          "机械臂点位=" + wp_id_ + " 超时=" +
          std::to_string(static_cast<int>(waypoint_wait_timeout_)) + "秒");
        return BT::NodeStatus::FAILURE;
      }
      return BT::NodeStatus::RUNNING;
    }
  }

  // ── Periodic republish: keep sending until serial ACK (state=0x03) ──
  if (!serial_ack_received_.load()) {
    const double since_last_publish = (node_->now() - last_publish_time_).seconds();
    if (since_last_publish >= arm_republish_interval_) {
      if (cmd_pub_->get_subscription_count() > 0) {
        publishCommand();
        RCLCPP_DEBUG(
          node_->get_logger(),
          "%s: republished command (%.1fs since last publish, waiting for ACK)",
          name().c_str(), since_last_publish);
      } else {
        RCLCPP_WARN_THROTTLE(
          node_->get_logger(), *node_->get_clock(), 2000,
          "%s: cannot republish — no subscriber on %s",
          name().c_str(), arm_command_topic_.c_str());
      }
    }
  }

  if (ack_received_.load()) {
    if (ack_success_.load()) {
      RCLCPP_INFO(node_->get_logger(), "%s: ACK success", name().c_str());
      legged_bringup::mission_log::publish(
        *node_, "ArmActionNode", "ARM_ACK_SUCCESS", "INFO", "节点=" + name());
      return BT::NodeStatus::SUCCESS;
    }
    RCLCPP_ERROR(node_->get_logger(), "%s: ACK reported failure", name().c_str());
    legged_bringup::mission_log::publish(
      *node_, "ArmActionNode", "ARM_ACK_FAILURE", "ERROR", "节点=" + name());
    return BT::NodeStatus::FAILURE;
  }

  const double elapsed = (node_->now() - start_time_).seconds();
  if (elapsed > timeout_sec_) {
    RCLCPP_ERROR(
      node_->get_logger(),
      "%s: ACK timeout after %.1fs (expected state=0x%02X on %s, cmd_subs=%zu)",
      name().c_str(), elapsed, expected_ack_state_, arm_status_topic_.c_str(),
      cmd_pub_->get_subscription_count());
    std::ostringstream detail;
    detail << "节点=" << name() << " 超时=" << elapsed << "秒 期望状态=0x"
           << std::hex << static_cast<int>(expected_ack_state_) << std::dec;
    legged_bringup::mission_log::publish(
      *node_, "ArmActionNode", "ARM_ACK_TIMEOUT", "ERROR", detail.str());
    return BT::NodeStatus::FAILURE;
  }

  return BT::NodeStatus::RUNNING;
}

void ArmActionNode::onHalted()
{
  RCLCPP_WARN(node_->get_logger(), "%s: halted", name().c_str());
  waiting_for_wp_ = false;
}

void ArmActionNode::onSerialAck(const std_msgs::msg::UInt8MultiArray::SharedPtr msg)
{
  if (msg->data.size() < 2) {
    return;
  }

  const uint8_t state = msg->data[0];

  // Only care about state=0x03 (Serial Done)
  if (state != 0x03) {
    return;
  }

  if (serial_ack_received_.load()) {
    return;
  }

  serial_ack_received_.store(true);
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: serial ACK received (0x03 Serial Done) — stopping republish",
    name().c_str());
  legged_bringup::mission_log::publish(
    *node_, "ArmActionNode", "ARM_SERIAL_ACK", "INFO",
    "节点=" + name() + " 串口接收完成，停止重发");
}

void ArmActionNode::onArmStatus(const std_msgs::msg::UInt8MultiArray::SharedPtr msg)
{
  if (msg->data.size() < 2) {
    return;
  }

  const uint8_t state = msg->data[0];
  const uint8_t result = msg->data[1];

  // Only care about expected behavior state (0x01 Pick / 0x02 Place)
  if (state != expected_ack_state_) {
    return;
  }

  if (ack_received_.load()) {
    return;
  }

  ack_received_.store(true);
  ack_success_.store(result == 0x00);

  const char * action_name = (expected_ack_state_ == 0x01) ? "抓取" : "放置";
  RCLCPP_INFO(
    node_->get_logger(),
    "%s: arm behavior ACK %s state=0x%02X result=0x%02X (%s)",
    name().c_str(), action_name, state, result, (result == 0x00) ? "OK" : "FAIL");
  legged_bringup::mission_log::publish(
    *node_, "ArmActionNode",
    (result == 0x00) ? "ARM_ACK_SUCCESS" : "ARM_ACK_FAILURE",
    (result == 0x00) ? "INFO" : "ERROR",
    std::string("节点=") + name() + " " + action_name + "完成");
}

}  // namespace legged_mission_bt
