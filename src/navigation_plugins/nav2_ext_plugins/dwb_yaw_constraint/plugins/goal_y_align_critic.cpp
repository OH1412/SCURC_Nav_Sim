/*
 * GoalYAlignCritic — direct Y-to-goal alignment.
 */

#include "dwb_yaw_constraint/goal_y_align_critic.hpp"

#include <cmath>
#include "dwb_yaw_constraint/critic_dynamic_scale.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

void GoalYAlignCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("GoalYAlignCritic: Failed to lock lifecycle node");
  }

  const std::string prefix = dwb_plugin_name_ + "." + name_ + ".";
  const std::string scale_param = dwb_plugin_name_ + "." + name_ + ".scale";

  nav2_util::declare_parameter_if_not_declared(
    node, scale_param, rclcpp::ParameterValue(0.0));

  registerScaleDynamicCallback(
    node, scale_param, [this](double s) { setScale(s); }, dyn_params_handler_);

  RCLCPP_INFO(
    node->get_logger(),
    "GoalYAlignCritic [%s]: scale=%.1f — direct Y→goal_Y alignment",
    name_.c_str(), scale_);
}

bool GoalYAlignCritic::prepare(
  const geometry_msgs::msg::Pose2D & /*pose*/,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & goal,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  goal_y_ = goal.y;
  goal_valid_ = true;
  return true;
}

double GoalYAlignCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (!goal_valid_ || traj.poses.empty()) {
    return 0.0;
  }

  const double final_y = traj.poses.back().y;
  const double y_error = std::fabs(final_y - goal_y_);

  return scale_ * y_error;
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::GoalYAlignCritic,
  dwb_core::TrajectoryCritic)
