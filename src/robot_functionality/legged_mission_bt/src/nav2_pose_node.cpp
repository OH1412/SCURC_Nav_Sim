#include "legged_mission_bt/nav2_pose_node.hpp"

#include <cmath>
#include <sstream>
#include <iomanip>

#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <std_msgs/msg/float64.hpp>
#include "legged_bringup/mission_log.hpp"

using namespace std::chrono_literals;

namespace
{

double normalizeAngle(double yaw)
{
  while (yaw > M_PI) {
    yaw -= 2.0 * M_PI;
  }
  while (yaw < -M_PI) {
    yaw += 2.0 * M_PI;
  }
  return yaw;
}

}  // namespace

Nav2PoseNode::Nav2PoseNode(
  const std::string & name,
  const BT::NodeConfiguration & config,
  std::shared_ptr<rclcpp::Node> node,
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry)
: BT::StatefulActionNode(name, config),
  node_(std::move(node)),
  registry_(std::move(registry))
{
  if (!node_->has_parameter("waypoint_wait_timeout")) {
    node_->declare_parameter("waypoint_wait_timeout", 120.0);
  }
  waypoint_wait_timeout_ = node_->get_parameter("waypoint_wait_timeout").as_double();
  if (!node_->has_parameter("nav_reached_topic")) {
    node_->declare_parameter("nav_reached_topic", "/mission_bt/nav_reached");
  }
  const auto nav_reached_topic = node_->get_parameter("nav_reached_topic").as_string();
  nav_reached_pub_ = node_->create_publisher<legged_mission_bt::msg::NavReached>(
    nav_reached_topic, rclcpp::QoS(rclcpp::KeepLast(10)).reliable());
  if (!node_->has_parameter("nav_zone_topic")) {
    node_->declare_parameter("nav_zone_topic", "/mission_bt/nav_zone");
  }
  const auto nav_zone_topic = node_->get_parameter("nav_zone_topic").as_string();
  nav_zone_pub_ = node_->create_publisher<std_msgs::msg::String>(
    nav_zone_topic,
    rclcpp::QoS(rclcpp::KeepLast(1)).transient_local().reliable());
  if (!node_->has_parameter("nav_segment_yaw_topic")) {
    node_->declare_parameter("nav_segment_yaw_topic", "/mission_bt/nav_segment_yaw");
  }
  const auto nav_segment_yaw_topic =
    node_->get_parameter("nav_segment_yaw_topic").as_string();
  nav_segment_yaw_pub_ = node_->create_publisher<std_msgs::msg::Float64>(
    nav_segment_yaw_topic,
    rclcpp::QoS(rclcpp::KeepLast(1)).transient_local().reliable());
  client_ = rclcpp_action::create_client<NavigateToPose>(node_, "navigate_to_pose");

  if (!node_->has_parameter("odom_topic")) {
    node_->declare_parameter("odom_topic", "/state_estimation");
  }
  if (!node_->has_parameter("base_frame")) {
    node_->declare_parameter("base_frame", "base_link");
  }
  if (!node_->has_parameter("nav_progress_log_interval")) {
    node_->declare_parameter("nav_progress_log_interval", 5.0);
  }
  if (!node_->has_parameter("middle_zone_distance")) {
    node_->declare_parameter("middle_zone_distance", 1.0);
  }
  odom_topic_ = node_->get_parameter("odom_topic").as_string();
  base_frame_ = node_->get_parameter("base_frame").as_string();
  nav_progress_log_interval_ = node_->get_parameter("nav_progress_log_interval").as_double();
  middle_zone_distance_ = node_->get_parameter("middle_zone_distance").as_double();

  if (!node_->has_parameter("corridor_entry_x")) {
    node_->declare_parameter("corridor_entry_x", 2.1695);
  }
  if (!node_->has_parameter("corridor_entry_y")) {
    node_->declare_parameter("corridor_entry_y", -1.7000);
  }
  if (!node_->has_parameter("corridor_exit_x")) {
    node_->declare_parameter("corridor_exit_x", 3.6615);
  }
  corridor_entry_x_ = node_->get_parameter("corridor_entry_x").as_double();
  corridor_entry_y_ = node_->get_parameter("corridor_entry_y").as_double();
  corridor_exit_x_ = node_->get_parameter("corridor_exit_x").as_double();

  tf_buffer_ = std::make_shared<tf2_ros::Buffer>(node_->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_, node_, false);
  odom_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
    odom_topic_, rclcpp::QoS(rclcpp::KeepLast(10)),
    [this](const nav_msgs::msg::Odometry::SharedPtr msg) {
      latest_odom_ = msg;
    });
}

BT::PortsList Nav2PoseNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("wp_id", "", "Nav waypoint id (from external topic or YAML seed)"),
    BT::InputPort<std::string>("frame_id", "map", "Goal frame (inline mode)"),
    BT::InputPort<double>("x", "Goal X (inline mode)"),
    BT::InputPort<double>("y", "Goal Y (inline mode)"),
    BT::InputPort<double>("yaw", 0.0, "Yaw in radians (inline mode)"),
    BT::InputPort<int>("motion_planner", 0, "0=always middle, 1=edge front-tangent, 2=edge rear-tangent"),
  };
}

bool Nav2PoseNode::ensureClient()
{
  if (!client_) {
    return false;
  }
  if (!client_->action_server_is_ready()) {
    RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: waiting for navigate_to_pose (up to 60s)...");
    if (!client_->wait_for_action_server(60s)) {
      RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: navigate_to_pose not available after 60s");
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: navigate_to_pose ready");
  }
  return true;
}

geometry_msgs::msg::PoseStamped Nav2PoseNode::makePose(
  const std::string & frame_id, double x, double y, double yaw)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = frame_id;
  pose.header.stamp = node_->now();
  pose.pose.position.x = x;
  pose.pose.position.y = y;
  pose.pose.position.z = 0.0;

  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, yaw);
  pose.pose.orientation = tf2::toMsg(q);
  return pose;
}

bool Nav2PoseNode::resolveGoal(std::string & frame_id, double & x, double & y, double & yaw)
{
  getInput("wp_id", wp_id_);

  if (!wp_id_.empty()) {
    legged_mission_bt::NavWaypoint wp;
    if (registry_ && registry_->tryGetNav(wp_id_, wp)) {
      frame_id = wp.frame_id;
      x = wp.x;
      y = wp.y;
      yaw = wp.yaw;
      resolved_nav_id_ = wp_id_;
      resolved_frame_id_ = frame_id;
      resolved_x_ = x;
      resolved_y_ = y;
      resolved_yaw_ = yaw;
      RCLCPP_INFO(
        node_->get_logger(),
        "Nav2PoseNode: resolved wp_id='%s' → frame=%s (%.3f, %.3f, yaw=%.3f)",
        wp_id_.c_str(), frame_id.c_str(), x, y, yaw);
      return true;
    }
    return false;
  }

  if (!getInput("x", x) || !getInput("y", y)) {
    RCLCPP_ERROR(
      node_->get_logger(),
      "Nav2PoseNode: provide wp_id or inline x/y");
    return false;
  }
  getInput("frame_id", frame_id);
  getInput("yaw", yaw);
  resolved_nav_id_ = wp_id_;
  resolved_frame_id_ = frame_id;
  resolved_x_ = x;
  resolved_y_ = y;
  resolved_yaw_ = yaw;
  return true;
}

void Nav2PoseNode::publishNavReached(const std::string & nav_id)
{
  legged_mission_bt::msg::NavReached msg;
  msg.nav_id = nav_id;
  nav_reached_pub_->publish(msg);
  legged_bringup::mission_log::publish(
    *node_, "Nav2PoseNode", "NAV_REACHED_PUBLISHED", "INFO", "导航点=" + nav_id);
}

void Nav2PoseNode::publishNavZone(const std::string & zone, const std::string & reason)
{
  std_msgs::msg::String msg;
  msg.data = zone;
  nav_zone_pub_->publish(msg);
  RCLCPP_INFO(node_->get_logger(),
    "Nav2PoseNode: published nav_zone='%s' for wp_id='%s' (motion_planner=%d, reason=%s)",
    zone.c_str(), wp_id_.c_str(), motion_planner_, reason.c_str());
  legged_bringup::mission_log::publish(
    *node_, "Nav2PoseNode", "NAV_ZONE_PUBLISHED", "INFO",
    "区域=" + zone + " 导航点=" + wp_id_ +
    " motion_planner=" + std::to_string(motion_planner_) +
    " 原因=" + reason);
}

void Nav2PoseNode::publishNavSegmentYaw(
  const std::string & frame_id, double goal_x, double goal_y, double goal_yaw)
{
  resolved_frame_id_ = frame_id;

  double start_x = 0.0;
  double start_y = 0.0;
  double start_yaw = 0.0;
  double vx = 0.0;
  double vy = 0.0;
  double wz = 0.0;

  double segment_yaw = goal_yaw;
  if (getCurrentStateInGoalFrame(start_x, start_y, start_yaw, vx, vy, wz)) {
    const double dx = goal_x - start_x;
    const double dy = goal_y - start_y;
    if (std::hypot(dx, dy) >= 0.05) {
      segment_yaw = std::atan2(dy, dx);
    }
  }

  // motion_planner=2: rear of vehicle tracks segment direction (yaw + 180°)
  if (motion_planner_ == 2) {
    segment_yaw = normalizeAngle(segment_yaw + M_PI);
  }

  std_msgs::msg::Float64 msg;
  msg.data = segment_yaw;
  nav_segment_yaw_pub_->publish(msg);

  RCLCPP_INFO(
    node_->get_logger(),
    "Nav2PoseNode: published nav_segment_yaw=%.3f rad (%s bearing) "
    "for wp_id='%s' start=(%.3f,%.3f) goal=(%.3f,%.3f)",
    segment_yaw, motion_planner_ == 2 ? "rear" : "front",
    wp_id_.c_str(), start_x, start_y, goal_x, goal_y);

  std::ostringstream detail;
  detail << "航段方位=" << segment_yaw << "弧度"
         << " 朝向=" << (motion_planner_ == 2 ? "车尾" : "车头")
         << " 起点=(" << start_x << ',' << start_y << ")"
         << " 终点=(" << goal_x << ',' << goal_y << ")";
  if (!resolved_nav_id_.empty()) {
    detail << " 导航点=" << resolved_nav_id_;
  }
  legged_bringup::mission_log::publish(
    *node_, "Nav2PoseNode", "NAV_SEGMENT_YAW_PUBLISHED", "INFO", detail.str());
}

bool Nav2PoseNode::sendGoal(const std::string & frame_id, double x, double y, double yaw)
{
  NavigateToPose::Goal goal;
  goal.pose = makePose(frame_id, x, y, yaw);

  goal_sent_ = false;
  result_ready_ = false;

  auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};
  const int my_seq = ++goal_sequence_;
  send_goal_options.result_callback =
    [this, my_seq](const GoalHandle::WrappedResult & result) {
      if (my_seq == goal_sequence_) {
        result_ = result;
        result_ready_ = true;
      }
    };

  RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: sending goal (%.3f, %.3f, yaw=%.3f)", x, y, yaw);
  std::ostringstream detail;
  detail << "坐标系=" << frame_id << " x=" << x << " y=" << y << " 航向=" << yaw << "弧度";
  if (!resolved_nav_id_.empty()) {
    detail << " 导航点=" << resolved_nav_id_;
  }
  legged_bringup::mission_log::publish(
    *node_, "Nav2PoseNode", "NAV_GOAL_SENT", "INFO", detail.str());

  publishNavSegmentYaw(frame_id, x, y, yaw);

  auto future_goal_handle = client_->async_send_goal(goal, send_goal_options);
  if (rclcpp::spin_until_future_complete(node_, future_goal_handle, 5s) !=
    rclcpp::FutureReturnCode::SUCCESS)
  {
    RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: failed to send goal");
    legged_bringup::mission_log::publish(
      *node_, "Nav2PoseNode", "NAV_GOAL_SEND_FAILED", "ERROR", detail.str());
    return false;
  }

  goal_handle_ = future_goal_handle.get();
  if (!goal_handle_) {
    RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: goal rejected");
    legged_bringup::mission_log::publish(
      *node_, "Nav2PoseNode", "NAV_GOAL_REJECTED", "ERROR", detail.str());
    return false;
  }

  goal_sent_ = true;
  resetNavProgressLogSchedule();
  return true;
}

void Nav2PoseNode::resetNavProgressLogSchedule()
{
  if (nav_progress_log_interval_ > 0.0) {
    nav_progress_start_ = node_->now();
    next_progress_log_time_ =
      nav_progress_start_ + rclcpp::Duration::from_seconds(nav_progress_log_interval_);
  }
}

bool Nav2PoseNode::getCurrentStateInGoalFrame(
  double & x, double & y, double & yaw, double & vx, double & vy, double & wz) const
{
  vx = 0.0;
  vy = 0.0;
  wz = 0.0;
  if (latest_odom_) {
    vx = latest_odom_->twist.twist.linear.x;
    vy = latest_odom_->twist.twist.linear.y;
    wz = latest_odom_->twist.twist.angular.z;
  }

  if (tf_buffer_ && tf_buffer_->canTransform(
      resolved_frame_id_, base_frame_, tf2::TimePointZero))
  {
    try {
      const auto tf = tf_buffer_->lookupTransform(
        resolved_frame_id_, base_frame_, tf2::TimePointZero);
      x = tf.transform.translation.x;
      y = tf.transform.translation.y;
      tf2::Quaternion q(
        tf.transform.rotation.x,
        tf.transform.rotation.y,
        tf.transform.rotation.z,
        tf.transform.rotation.w);
      double roll = 0.0;
      double pitch = 0.0;
      tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);
      return true;
    } catch (const tf2::TransformException &) {
      // fall through to odometry pose
    }
  }

  if (!latest_odom_) {
    return false;
  }
  if (latest_odom_->header.frame_id != resolved_frame_id_) {
    return false;
  }

  x = latest_odom_->pose.pose.position.x;
  y = latest_odom_->pose.pose.position.y;
  tf2::Quaternion q(
    latest_odom_->pose.pose.orientation.x,
    latest_odom_->pose.pose.orientation.y,
    latest_odom_->pose.pose.orientation.z,
    latest_odom_->pose.pose.orientation.w);
  double roll = 0.0;
  double pitch = 0.0;
  tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);
  return true;
}

void Nav2PoseNode::maybeLogNavProgress()
{
  if (nav_progress_log_interval_ <= 0.0 || !goal_sent_ || result_ready_) {
    return;
  }
  if (node_->now() < next_progress_log_time_) {
    return;
  }

  double cur_x = 0.0;
  double cur_y = 0.0;
  double cur_yaw = 0.0;
  double vx = 0.0;
  double vy = 0.0;
  double wz = 0.0;
  if (getCurrentStateInGoalFrame(cur_x, cur_y, cur_yaw, vx, vy, wz)) {
    const double dx = resolved_x_ - cur_x;
    const double dy = resolved_y_ - cur_y;
    const double dist_err = std::hypot(dx, dy);
    const double yaw_err = normalizeAngle(resolved_yaw_ - cur_yaw);
    const double elapsed = (node_->now() - nav_progress_start_).seconds();

    std::ostringstream detail;
    detail << "耗时=" << std::fixed << std::setprecision(1) << elapsed << "秒"
           << " 坐标系=" << resolved_frame_id_
           << " 当前位置=(" << cur_x << ',' << cur_y << ",航向=" << cur_yaw << "弧度)"
           << " 当前速度=(" << vx << ',' << vy << ",角速度=" << wz << "弧度/秒)"
           << " 目标位置=(" << resolved_x_ << ',' << resolved_y_
           << ",航向=" << resolved_yaw_ << "弧度)"
           << " 距离误差=" << dist_err << "米 航向误差=" << yaw_err << "弧度";
    if (!resolved_nav_id_.empty()) {
      detail << " 导航点=" << resolved_nav_id_;
    }

    RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: 导航进度 %s", detail.str().c_str());
    legged_bringup::mission_log::publish(
      *node_, "Nav2PoseNode", "NAV_PROGRESS", "INFO", detail.str());
  }

  next_progress_log_time_ += rclcpp::Duration::from_seconds(nav_progress_log_interval_);
}

BT::NodeStatus Nav2PoseNode::onStart()
{
  if (!ensureClient()) {
    return BT::NodeStatus::FAILURE;
  }

  std::string frame_id = "map";
  double x = 0.0;
  double y = 0.0;
  double yaw = 0.0;

  waiting_for_wp_ = false;
  goal_sent_ = false;
  result_ready_ = false;

  getInput("motion_planner", motion_planner_);

  if (resolveGoal(frame_id, x, y, yaw)) {
    // ── Determine zone / multi-phase mode from resolved goal coordinates ──
    limit_yaw_ = (motion_planner_ == 0);
    corridor_phase_active_ = false;
    corridor_aligning_ = false;
    corridor_phase_ = CorridorPhase::APPROACH;
    middle_zone_applied_ = false;

    // Save original final goal (may be overridden for multi-phase corridor)
    original_goal_x_ = x;
    original_goal_y_ = y;
    original_goal_yaw_ = yaw;

    if (motion_planner_ == 0 && x >= corridor_entry_x_) {
      // Multi-phase corridor navigation — start by going to corridor entry
      corridor_phase_active_ = true;
      publishNavZone("edge", "corridor_approach(mp=0)");
      // Override effective goal to corridor entry
      x = corridor_entry_x_;
      y = corridor_entry_y_;
      yaw = 0.0;
      resolved_x_ = x;
      resolved_y_ = y;
      resolved_yaw_ = yaw;
    } else if (motion_planner_ == 0) {
      // Target before corridor → original always-middle behaviour
      middle_zone_applied_ = true;
      publishNavZone("middle", "always_middle(mp=0)");
    } else {
      publishNavZone("edge", "startup(mp=" + std::to_string(motion_planner_) + ")");
    }

    const std::string zone = corridor_phase_active_ ? "edge"
                           : (middle_zone_applied_ ? "middle" : "edge");

    std::ostringstream detail;
    detail << "导航点=" << wp_id_ << " 坐标系=" << frame_id
           << " x=" << x << " y=" << y << " 航向=" << yaw << "弧度"
           << " motion_planner=" << motion_planner_
           << " zone=" << zone;
    if (corridor_phase_active_) {
      detail << " original_goal=(" << original_goal_x_ << ','
             << original_goal_y_ << ',' << original_goal_yaw_ << ')';
    }
    legged_bringup::mission_log::publish(
      *node_, "Nav2PoseNode", "NAV_STEP_START", "INFO", detail.str());
    return sendGoal(frame_id, x, y, yaw) ? BT::NodeStatus::RUNNING : BT::NodeStatus::FAILURE;
  }

  if (wp_id_.empty()) {
    return BT::NodeStatus::FAILURE;
  }

  waiting_for_wp_ = true;
  resolve_start_ = node_->now();
  RCLCPP_INFO(
    node_->get_logger(),
    "Nav2PoseNode: waiting for nav wp_id='%s' on /mission_bt/nav_waypoint (up to %.0fs)...",
    wp_id_.c_str(), waypoint_wait_timeout_);
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus Nav2PoseNode::onRunning()
{
  if (waiting_for_wp_) {
    rclcpp::spin_some(node_);

    std::string frame_id = "map";
    double x = 0.0;
    double y = 0.0;
    double yaw = 0.0;
    if (resolveGoal(frame_id, x, y, yaw)) {
      waiting_for_wp_ = false;
      getInput("motion_planner", motion_planner_);
      limit_yaw_ = (motion_planner_ == 0);
      corridor_phase_active_ = false;
      corridor_phase_ = CorridorPhase::APPROACH;
      middle_zone_applied_ = false;

      // Save original final goal
      original_goal_x_ = x;
      original_goal_y_ = y;
      original_goal_yaw_ = yaw;

      if (motion_planner_ == 0 && resolved_x_ >= corridor_entry_x_) {
        corridor_phase_active_ = true;
        publishNavZone("edge", "corridor_approach(mp=0)");
        x = corridor_entry_x_;
        y = corridor_entry_y_;
        yaw = 0.0;
        resolved_x_ = x;
        resolved_y_ = y;
        resolved_yaw_ = yaw;
      } else if (motion_planner_ == 0) {
        middle_zone_applied_ = true;
        publishNavZone("middle", "always_middle(mp=0)");
      } else {
        publishNavZone("edge", "startup(mp=" + std::to_string(motion_planner_) + ")");
      }
      const std::string zone = corridor_phase_active_ ? "edge" : (middle_zone_applied_ ? "middle" : "edge");
      std::ostringstream detail;
      detail << "导航点=" << wp_id_ << " 坐标系=" << frame_id
             << " x=" << x << " y=" << y << " 航向=" << yaw << "弧度"
             << " motion_planner=" << motion_planner_
             << " zone=" << zone;
      if (corridor_phase_active_) {
        detail << " original_goal=(" << original_goal_x_ << ','
               << original_goal_y_ << ',' << original_goal_yaw_ << ')';
      }
      legged_bringup::mission_log::publish(
        *node_, "Nav2PoseNode", "NAV_STEP_START", "INFO", detail.str());
      return sendGoal(frame_id, x, y, yaw) ? BT::NodeStatus::RUNNING : BT::NodeStatus::FAILURE;
    }

    const double elapsed = (node_->now() - resolve_start_).seconds();
    if (elapsed > waypoint_wait_timeout_) {
      RCLCPP_ERROR(
        node_->get_logger(),
        "Nav2PoseNode: timeout waiting for nav wp_id='%s' (%.0fs)",
        wp_id_.c_str(), waypoint_wait_timeout_);
      legged_bringup::mission_log::publish(
        *node_, "Nav2PoseNode", "NAV_WAYPOINT_TIMEOUT", "ERROR",
        "导航点=" + wp_id_ + " 超时=" +
        std::to_string(static_cast<int>(waypoint_wait_timeout_)) + "秒");
      return BT::NodeStatus::FAILURE;
    }
    return BT::NodeStatus::RUNNING;
  }

  if (!goal_sent_) {
    return BT::NodeStatus::FAILURE;
  }
  if (!result_ready_) {
    rclcpp::spin_some(node_);
    maybeLogNavProgress();

    // ── Multi-phase corridor navigation (motion_planner_ == 0) ──────────
    if (corridor_phase_active_) {
      updateCorridorPhase();

      // ── Yaw alignment monitoring between phases ───────────────────
      if (corridor_aligning_) {
        double cur_x = 0.0, cur_y = 0.0, cur_yaw = 0.0, vx = 0.0, vy = 0.0, wz = 0.0;
        if (getCurrentStateInGoalFrame(cur_x, cur_y, cur_yaw, vx, vy, wz)) {
          const double yaw_err = std::abs(normalizeAngle(cur_yaw - corridor_align_yaw_));
          if (yaw_err < M_PI / 6.0) {  // Within 30 degrees
            RCLCPP_INFO(node_->get_logger(),
              "Nav2PoseNode: corridor yaw aligned (err=%.1f°), sending position goal",
              yaw_err * 180.0 / M_PI);
            corridor_aligning_ = false;
            // Restore actual position goal and send it
            resolved_x_ = corridor_pending_x_;
            resolved_y_ = corridor_pending_y_;
            resolved_yaw_ = corridor_pending_yaw_;
            resendNavGoal();
          }
        }
      }
    }

    // Distance-based zone switching: when starting from EDGE mode and approaching
    // within middle_zone_distance_ of the goal, switch to MIDDLE for final approach.
    // Only active when multi-phase corridor logic is NOT running.
    if (!corridor_phase_active_ && !middle_zone_applied_) {
      double cur_x = 0.0, cur_y = 0.0, cur_yaw = 0.0, vx = 0.0, vy = 0.0, wz = 0.0;
      if (getCurrentStateInGoalFrame(cur_x, cur_y, cur_yaw, vx, vy, wz)) {
        const double dx = resolved_x_ - cur_x;
        const double dy = resolved_y_ - cur_y;
        const double dist = std::hypot(dx, dy);
        if (dist < middle_zone_distance_) {
          middle_zone_applied_ = true;
          publishNavZone("middle", "dist=" + std::to_string(static_cast<int>(dist * 100) / 100.0) + "m < " + std::to_string(middle_zone_distance_) + "m");
        }
      }
    }

    return BT::NodeStatus::RUNNING;
  }

  switch (result_.code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      // ── Yaw alignment goal completed ──────────────────────────────────
      if (corridor_aligning_) {
        double cur_x = 0.0, cur_y = 0.0, cur_yaw = 0.0, vx = 0.0, vy = 0.0, wz = 0.0;
        if (getCurrentStateInGoalFrame(cur_x, cur_y, cur_yaw, vx, vy, wz)) {
          const double yaw_err = std::abs(normalizeAngle(cur_yaw - corridor_align_yaw_));
          if (yaw_err < M_PI / 6.0) {
            RCLCPP_INFO(node_->get_logger(),
              "Nav2PoseNode: corridor alignment goal succeeded (yaw_err=%.1f°), sending position goal",
              yaw_err * 180.0 / M_PI);
            corridor_aligning_ = false;
            resolved_x_ = corridor_pending_x_;
            resolved_y_ = corridor_pending_y_;
            resolved_yaw_ = corridor_pending_yaw_;
            resendNavGoal();
            result_ready_ = false;
            return BT::NodeStatus::RUNNING;
          }
        }
        // Yaw still not aligned, re-send rotation goal
        resendNavGoal();
        result_ready_ = false;
        return BT::NodeStatus::RUNNING;
      }

      // ── Multi-phase corridor: intermediate goal reached → advance phase ──
      if (corridor_phase_active_ && corridor_phase_ != CorridorPhase::FINAL) {
        RCLCPP_INFO(node_->get_logger(),
          "Nav2PoseNode: intermediate goal reached in phase=%d, advancing",
          static_cast<int>(corridor_phase_));
        // Determine next phase from current position and re-send
        if (updateCorridorPhase()) {
          // Phase changed and new goal sent — continue running
          result_ready_ = false;
          return BT::NodeStatus::RUNNING;
        }
        // If phase didn't change, force-resend for current phase
        resendNavGoal();
        result_ready_ = false;
        return BT::NodeStatus::RUNNING;
      }

      if (!resolved_nav_id_.empty()) {
        publishNavReached(resolved_nav_id_);
      }
      RCLCPP_INFO(node_->get_logger(), "Nav2PoseNode: navigation succeeded");
      legged_bringup::mission_log::publish(
        *node_, "Nav2PoseNode", "NAV_SUCCEEDED", "INFO",
        resolved_nav_id_.empty() ? "内联目标" : "导航点=" + resolved_nav_id_);
      return BT::NodeStatus::SUCCESS;
    case rclcpp_action::ResultCode::ABORTED:
      RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: navigation aborted");
      legged_bringup::mission_log::publish(
        *node_, "Nav2PoseNode", "NAV_ABORTED", "ERROR",
        resolved_nav_id_.empty() ? "内联目标" : "导航点=" + resolved_nav_id_);
      return BT::NodeStatus::FAILURE;
    case rclcpp_action::ResultCode::CANCELED:
      RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: navigation canceled");
      legged_bringup::mission_log::publish(
        *node_, "Nav2PoseNode", "NAV_CANCELED", "ERROR",
        resolved_nav_id_.empty() ? "内联目标" : "导航点=" + resolved_nav_id_);
      return BT::NodeStatus::FAILURE;
    default:
      RCLCPP_ERROR(node_->get_logger(), "Nav2PoseNode: unknown result code");
      return BT::NodeStatus::FAILURE;
  }
}

void Nav2PoseNode::onHalted()
{
  if (goal_handle_) {
    RCLCPP_WARN(node_->get_logger(), "Nav2PoseNode: halted, cancel goal");
    client_->async_cancel_goal(goal_handle_);
  }
  goal_sent_ = false;
  result_ready_ = false;
  waiting_for_wp_ = false;
}

bool Nav2PoseNode::updateCorridorPhase()
{
  if (!corridor_phase_active_) {
    return false;
  }

  double cur_x = 0.0, cur_y = 0.0, cur_yaw = 0.0, vx = 0.0, vy = 0.0, wz = 0.0;
  if (!getCurrentStateInGoalFrame(cur_x, cur_y, cur_yaw, vx, vy, wz)) {
    return false;
  }

  // Distance to *final* goal (original), for EXIT→FINAL determination
  const double dx_final = original_goal_x_ - cur_x;
  const double dy_final = original_goal_y_ - cur_y;
  const double dist_to_final = std::hypot(dx_final, dy_final);

  // ── One-directional phase transitions (never go backward) ──────────
  CorridorPhase new_phase = corridor_phase_;

  switch (corridor_phase_) {
    case CorridorPhase::APPROACH:
      // 向 (corridor_entry_x_, corridor_entry_y_) 走
      // 第一次 x>=入口x 且 y<=入口y → 切入 CORRIDOR
      if (cur_x >= corridor_entry_x_ && cur_y <= corridor_entry_y_) {
        new_phase = CorridorPhase::CORRIDOR;
      }
      break;

    case CorridorPhase::CORRIDOR:
      // 向 (corridor_exit_x_, corridor_entry_y_) 走
      // 第一次 x>=出口x → 切入 EXIT
      if (cur_x >= corridor_exit_x_) {
        new_phase = CorridorPhase::EXIT;
      }
      break;

    case CorridorPhase::EXIT:
      // 向原始最终目标走
      // 第一次 距目标 < middle_zone_distance → 切入 FINAL
      if (dist_to_final < middle_zone_distance_) {
        new_phase = CorridorPhase::FINAL;
      }
      break;

    case CorridorPhase::FINAL:
      // 保持在 FINAL，不再切换
      break;
  }

  if (new_phase == corridor_phase_) {
    return false;  // No change
  }

  // ── Phase transition: cancel old goal, send new one ──────────────────
  const char* old_name = "UNKNOWN";
  switch (corridor_phase_) {
    case CorridorPhase::APPROACH: old_name = "APPROACH"; break;
    case CorridorPhase::CORRIDOR: old_name = "CORRIDOR"; break;
    case CorridorPhase::EXIT:     old_name = "EXIT";     break;
    case CorridorPhase::FINAL:    old_name = "FINAL";    break;
  }
  const char* new_name = "UNKNOWN";
  switch (new_phase) {
    case CorridorPhase::APPROACH: new_name = "APPROACH"; break;
    case CorridorPhase::CORRIDOR: new_name = "CORRIDOR"; break;
    case CorridorPhase::EXIT:     new_name = "EXIT";     break;
    case CorridorPhase::FINAL:    new_name = "FINAL";    break;
  }

  corridor_phase_ = new_phase;

  // Publish zone for the new phase
  switch (new_phase) {
    case CorridorPhase::APPROACH:
      publishNavZone("edge", "phase=APPROACH");
      // Set effective goal to corridor entry
      resolved_x_ = corridor_entry_x_;
      resolved_y_ = corridor_entry_y_;
      resolved_yaw_ = 0.0;
      break;

    case CorridorPhase::CORRIDOR:
      publishNavZone("middle", "phase=CORRIDOR");
      // Set effective goal to corridor exit
      resolved_x_ = corridor_exit_x_;
      resolved_y_ = corridor_entry_y_;
      resolved_yaw_ = 0.0;
      break;

    case CorridorPhase::EXIT:
      publishNavZone("edge", "phase=EXIT");
      // Restore original final goal
      resolved_x_ = original_goal_x_;
      resolved_y_ = original_goal_y_;
      resolved_yaw_ = original_goal_yaw_;
      break;

    case CorridorPhase::FINAL:
      publishNavZone("middle", "phase=FINAL dist=" +
                     std::to_string(static_cast<int>(dist_to_final * 100) / 100.0));
      // Keep original final goal (should already be set from EXIT or CORRIDOR exit)
      break;
  }

  // ── Enter yaw alignment: stop → rotate yaw → then send position goal ──
  // Compute target yaw: segment-tangent direction from current to new goal
  double align_yaw = resolved_yaw_;
  {
    const double seg_dx = resolved_x_ - cur_x;
    const double seg_dy = resolved_y_ - cur_y;
    if (std::hypot(seg_dx, seg_dy) >= 0.05) {
      align_yaw = std::atan2(seg_dy, seg_dx);
    }
    // motion_planner=0 → no rear-bearing flip (unlike mp=2)
  }

  const double yaw_err = std::abs(normalizeAngle(cur_yaw - align_yaw));
  if (yaw_err < M_PI / 6.0) {
    // Already within 30° — send position goal directly, no alignment needed
    resendNavGoal();
  } else {
    // Need yaw alignment first: send rotation-only goal at current position
    RCLCPP_INFO(node_->get_logger(),
      "Nav2PoseNode: corridor phase %s → %s, yaw_err=%.1f°, entering alignment (target=%.2f°)",
      old_name, new_name, yaw_err * 180.0 / M_PI, align_yaw * 180.0 / M_PI);

    corridor_aligning_ = true;
    corridor_align_yaw_ = align_yaw;
    // Save the actual position goal for after alignment completes
    corridor_pending_x_ = resolved_x_;
    corridor_pending_y_ = resolved_y_;
    corridor_pending_yaw_ = resolved_yaw_;
    // Override to current position (rotation only, no linear motion)
    resolved_x_ = cur_x;
    resolved_y_ = cur_y;
    resolved_yaw_ = align_yaw;
    resendNavGoal();
  }

  RCLCPP_INFO(node_->get_logger(),
    "Nav2PoseNode: corridor phase %s → %s (pos=%.3f,%.3f newGoal=%.3f,%.3f distToFinal=%.2f)",
    old_name, new_name, cur_x, cur_y, resolved_x_, resolved_y_, dist_to_final);

  std::ostringstream detail;
  detail << "阶段=" << new_name << " (原=" << old_name << ")"
         << " 位置=(" << cur_x << ',' << cur_y << ")"
         << " 新目标=(" << resolved_x_ << ',' << resolved_y_ << ")"
         << " 距终点=" << dist_to_final << "米";
  if (!resolved_nav_id_.empty()) {
    detail << " 导航点=" << resolved_nav_id_;
  }
  legged_bringup::mission_log::publish(
    *node_, "Nav2PoseNode", "CORRIDOR_PHASE_CHANGE", "INFO", detail.str());

  return true;
}

bool Nav2PoseNode::resendNavGoal()
{
  if (goal_handle_) {
    RCLCPP_INFO(node_->get_logger(),
      "Nav2PoseNode: canceling current goal to switch sub-target");
    client_->async_cancel_goal(goal_handle_);
    goal_handle_.reset();
  }

  goal_sent_ = false;
  result_ready_ = false;

  return sendGoal(resolved_frame_id_, resolved_x_, resolved_y_, resolved_yaw_);
}
