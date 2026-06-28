/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#include "dwb_yaw_constraint/maintain_vy_critic.hpp"
#include <cmath>
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

void MaintainVyCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("MaintainVyCritic: Failed to lock lifecycle node");
  }

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".target_vy",
    rclcpp::ParameterValue(0.0));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".target_vy", target_vy_);
}

bool MaintainVyCritic::prepare(
  const geometry_msgs::msg::Pose2D & /*pose*/,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & /*goal*/,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  // No per-cycle preparation needed — vy is in body frame, no TF required.
  return true;
}

double MaintainVyCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  // Penalize lateral velocity in the commanded twist.
  // With scale=5000, vy=0.5 m/s → cost=2500, which dominates typical
  // PathDist (~100-300) and GoalDist (~tens to hundreds) costs.
  return scale_ * std::fabs(traj.velocity.y - target_vy_);
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::MaintainVyCritic,
  dwb_core::TrajectoryCritic)
