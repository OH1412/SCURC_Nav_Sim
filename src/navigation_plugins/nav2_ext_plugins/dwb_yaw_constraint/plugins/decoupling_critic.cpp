/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#include "dwb_yaw_constraint/decoupling_critic.hpp"
#include <algorithm>
#include <cmath>
#include "dwb_yaw_constraint/critic_dynamic_scale.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

void DecouplingCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("DecouplingCritic: Failed to lock lifecycle node");
  }

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".max_vx",
    rclcpp::ParameterValue(1.0));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".max_vx", max_vx_);

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".max_vy",
    rclcpp::ParameterValue(1.0));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".max_vy", max_vy_);

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".max_vtheta",
    rclcpp::ParameterValue(5.0));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".max_vtheta", max_vtheta_);

  const std::string scale_param = dwb_plugin_name_ + "." + name_ + ".scale";
  registerScaleDynamicCallback(
    node, scale_param, [this](double s) { setScale(s); }, dyn_params_handler_);
}

bool DecouplingCritic::prepare(
  const geometry_msgs::msg::Pose2D & /*pose*/,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & /*goal*/,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  // No per-cycle preparation needed
  return true;
}

double DecouplingCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  // Normalize each velocity component by its max to make them comparable
  double nx = std::fabs(traj.velocity.x) / std::max(max_vx_, 1e-6);
  double ny = std::fabs(traj.velocity.y) / std::max(max_vy_, 1e-6);
  double nt = std::fabs(traj.velocity.theta) / std::max(max_vtheta_, 1e-6);

  // Find the second-largest normalized component.
  // If only one axis is active, the second-largest is near zero → no penalty.
  // If two or more axes are active, penalty ≈ scale * second_largest.
  double a = std::max({nx, ny, nt});
  double c = std::min({nx, ny, nt});
  double b = nx + ny + nt - a - c;  // middle value = second largest

  // Penalty proportional to secondary axis magnitude.
  // Small mixing → small penalty; heavy mixing → large penalty.
  return scale_ * b;
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::DecouplingCritic,
  dwb_core::TrajectoryCritic)
