/*
 * RotateToPath — use Nav2PoseNode start→goal bearing for the whole nav step.
 */

#include "dwb_yaw_constraint/rotate_to_path_critic.hpp"

#include <cmath>
#include "angles/angles.h"
#include "dwb_core/exceptions.hpp"
#include "dwb_core/trajectory_utils.hpp"
#include "dwb_yaw_constraint/critic_dynamic_scale.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

void RotateToPathCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("RotateToPathCritic: Failed to lock lifecycle node");
  }

  const std::string prefix = dwb_plugin_name_ + ".";
  const std::string ns = prefix + name_ + ".";

  nav2_util::declare_parameter_if_not_declared(
    node, ns + "use_segment_yaw", rclcpp::ParameterValue(true));
  nav2_util::declare_parameter_if_not_declared(
    node, ns + "nav_segment_yaw_topic", rclcpp::ParameterValue("/mission_bt/nav_segment_yaw"));
  nav2_util::declare_parameter_if_not_declared(
    node, ns + "lookahead_time", rclcpp::ParameterValue(-1.0));
  nav2_util::declare_parameter_if_not_declared(
    node, ns + "yaw_error_threshold", rclcpp::ParameterValue(0.087));

  node->get_parameter(ns + "use_segment_yaw", use_segment_yaw_);
  node->get_parameter(ns + "nav_segment_yaw_topic", nav_segment_yaw_topic_);
  node->get_parameter(ns + "lookahead_time", lookahead_time_);
  node->get_parameter(ns + "yaw_error_threshold", yaw_error_threshold_);

  if (use_segment_yaw_) {
    segment_yaw_sub_ = node->create_subscription<std_msgs::msg::Float64>(
      nav_segment_yaw_topic_,
      rclcpp::QoS(rclcpp::KeepLast(1)).transient_local().reliable(),
      std::bind(&RotateToPathCritic::navSegmentYawCallback, this, std::placeholders::_1));
  }

  RCLCPP_INFO(
    node->get_logger(),
    "RotateToPath [%s] scale=%.1f, use_segment_yaw=%s, topic=%s, yaw_thresh=%.2f rad",
    name_.c_str(), scale_, use_segment_yaw_ ? "true" : "false",
    nav_segment_yaw_topic_.c_str(), yaw_error_threshold_);

  tangent_valid_ = false;
  target_yaw_ = 0.0;
  segment_yaw_valid_ = false;

  const std::string scale_param = prefix + name_ + ".scale";
  registerScaleDynamicCallback(
    node, scale_param, [this](double s) { setScale(s); }, dyn_params_handler_);
}

void RotateToPathCritic::navSegmentYawCallback(
  const std_msgs::msg::Float64::SharedPtr msg)
{
  segment_yaw_ = msg->data;
  segment_yaw_valid_ = true;
}

double RotateToPathCritic::computeGoalBearingYaw(
  const geometry_msgs::msg::Pose2D & pose,
  const geometry_msgs::msg::Pose2D & goal) const
{
  const double dx = goal.x - pose.x;
  const double dy = goal.y - pose.y;
  if (std::hypot(dx, dy) < 0.05) {
    return goal.theta;
  }
  return std::atan2(dy, dx);
}

bool RotateToPathCritic::prepare(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & goal,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  tangent_valid_ = false;

  if (use_segment_yaw_ && segment_yaw_valid_) {
    target_yaw_ = segment_yaw_;
  } else {
    target_yaw_ = computeGoalBearingYaw(pose, goal);
  }

  tangent_valid_ = true;
  return true;
}

double RotateToPathCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (!tangent_valid_ || traj.poses.empty()) {
    return 0.0;
  }

  double eval_yaw;
  if (lookahead_time_ >= 0.0) {
    const geometry_msgs::msg::Pose2D eval_pose =
      dwb_core::projectPose(traj, lookahead_time_);
    eval_yaw = eval_pose.theta;
  } else {
    eval_yaw = traj.poses.back().theta;
  }

  double yaw_error = angles::shortest_angular_distance(eval_yaw, target_yaw_);

  if (scale_ > 0.0 && std::fabs(yaw_error) > yaw_error_threshold_) {
    double linear_speed = std::hypot(traj.velocity.x, traj.velocity.y);
    if (linear_speed > 0.05) {
      throw dwb_core::IllegalTrajectoryException(
        name_, "Must rotate to segment direction before translating.");
    }
  }

  return scale_ * std::fabs(yaw_error);
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::RotateToPathCritic,
  dwb_core::TrajectoryCritic)
