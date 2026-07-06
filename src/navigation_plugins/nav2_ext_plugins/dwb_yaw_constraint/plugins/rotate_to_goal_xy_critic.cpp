/*
 * RotateToGoalXY — axis-aligned x/y window (matches SimpleGoalCheckerXY).
 */

#include "dwb_yaw_constraint/rotate_to_goal_xy_critic.hpp"

#include <cmath>
#include "angles/angles.h"
#include "dwb_core/exceptions.hpp"
#include "dwb_core/trajectory_utils.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

namespace
{
inline double hypot_sq(double dx, double dy)
{
  return dx * dx + dy * dy;
}
}  // namespace

void RotateToGoalXYCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("RotateToGoalXYCritic: failed to lock node");
  }

  const std::string prefix = dwb_plugin_name_ + ".";
  nav2_util::declare_parameter_if_not_declared(
    node, prefix + "xy_goal_tolerance", rclcpp::ParameterValue(0.10));
  nav2_util::declare_parameter_if_not_declared(
    node, prefix + "x_goal_tolerance", rclcpp::ParameterValue(-1.0));
  nav2_util::declare_parameter_if_not_declared(
    node, prefix + "y_goal_tolerance", rclcpp::ParameterValue(-1.0));
  nav2_util::declare_parameter_if_not_declared(
    node, prefix + "trans_stopped_velocity", rclcpp::ParameterValue(0.08));

  nav2_util::declare_parameter_if_not_declared(
    node, prefix + name_ + ".slowing_factor", rclcpp::ParameterValue(5.0));
  nav2_util::declare_parameter_if_not_declared(
    node, prefix + name_ + ".lookahead_time", rclcpp::ParameterValue(-1.0));

  refreshTolerances();

  double stopped_xy_velocity = 0.08;
  node->get_parameter(prefix + "trans_stopped_velocity", stopped_xy_velocity);
  stopped_xy_velocity_sq_ = stopped_xy_velocity * stopped_xy_velocity;

  node->get_parameter(prefix + name_ + ".slowing_factor", slowing_factor_);
  node->get_parameter(prefix + name_ + ".lookahead_time", lookahead_time_);

  RCLCPP_INFO(
    node->get_logger(),
    "RotateToGoalXY [%s] x_tol=%.3f m, y_tol=%.3f m, slowing_factor=%.1f",
    name_.c_str(), x_goal_tolerance_, y_goal_tolerance_, slowing_factor_);

  reset();
}

void RotateToGoalXYCritic::refreshTolerances()
{
  auto node = node_.lock();
  if (!node) {
    return;
  }

  const std::string prefix = dwb_plugin_name_ + ".";
  node->get_parameter(prefix + "xy_goal_tolerance", xy_goal_tolerance_);
  node->get_parameter(prefix + "x_goal_tolerance", x_goal_tolerance_);
  node->get_parameter(prefix + "y_goal_tolerance", y_goal_tolerance_);

  if (x_goal_tolerance_ < 0.0) {
    x_goal_tolerance_ = xy_goal_tolerance_;
  }
  if (y_goal_tolerance_ < 0.0) {
    y_goal_tolerance_ = xy_goal_tolerance_;
  }
}

void RotateToGoalXYCritic::reset()
{
  in_window_ = false;
  rotating_ = false;
}

bool RotateToGoalXYCritic::prepare(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Twist2D & vel,
  const geometry_msgs::msg::Pose2D & goal,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  refreshTolerances();

  const double dx = pose.x - goal.x;
  const double dy = pose.y - goal.y;
  const bool inside_box =
    std::fabs(dx) <= x_goal_tolerance_ && std::fabs(dy) <= y_goal_tolerance_;

  in_window_ = in_window_ || inside_box;
  current_xy_speed_sq_ = hypot_sq(vel.x, vel.y);
  rotating_ = rotating_ || (in_window_ && current_xy_speed_sq_ <= stopped_xy_velocity_sq_);
  goal_yaw_ = goal.theta;
  return true;
}

double RotateToGoalXYCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (!in_window_) {
    return 0.0;
  }

  if (!rotating_) {
    const double speed_sq = hypot_sq(traj.velocity.x, traj.velocity.y);
    if (speed_sq >= current_xy_speed_sq_) {
      throw dwb_core::IllegalTrajectoryException(name_, "Not slowing down near goal.");
    }
    return speed_sq * slowing_factor_ + scoreRotation(traj);
  }

  if (std::fabs(traj.velocity.x) > 0.0 || std::fabs(traj.velocity.y) > 0.0) {
    throw dwb_core::IllegalTrajectoryException(name_, "Nonrotation command near goal.");
  }

  return scoreRotation(traj);
}

double RotateToGoalXYCritic::scoreRotation(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (traj.poses.empty()) {
    throw dwb_core::IllegalTrajectoryException(name_, "Empty trajectory.");
  }

  double end_yaw;
  if (lookahead_time_ >= 0.0) {
    const geometry_msgs::msg::Pose2D eval_pose =
      dwb_core::projectPose(traj, lookahead_time_);
    end_yaw = eval_pose.theta;
  } else {
    end_yaw = traj.poses.back().theta;
  }

  return std::fabs(angles::shortest_angular_distance(end_yaw, goal_yaw_));
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::RotateToGoalXYCritic, dwb_core::TrajectoryCritic)
