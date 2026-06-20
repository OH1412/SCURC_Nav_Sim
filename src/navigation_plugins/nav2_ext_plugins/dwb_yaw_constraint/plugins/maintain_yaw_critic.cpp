/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#include "dwb_yaw_constraint/maintain_yaw_critic.hpp"
#include <cmath>
#include "angles/angles.h"
#include "nav2_util/node_utils.hpp"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

void MaintainYawCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("MaintainYawCritic: Failed to lock lifecycle node");
  }

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".desired_yaw",
    rclcpp::ParameterValue(0.0));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".desired_yaw", desired_yaw_);

  nav2_util::declare_parameter_if_not_declared(
    node,
    dwb_plugin_name_ + "." + name_ + ".reference_frame",
    rclcpp::ParameterValue("map"));
  node->get_parameter(
    dwb_plugin_name_ + "." + name_ + ".reference_frame", reference_frame_);

  target_valid_ = false;
  target_yaw_ = 0.0;
}

bool MaintainYawCritic::prepare(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & /*goal*/,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  std::string costmap_frame = costmap_ros_->getGlobalFrameID();

  // If the costmap frame equals the reference frame, no transform is needed
  if (costmap_frame == reference_frame_) {
    target_yaw_ = desired_yaw_;
    target_valid_ = true;
    return true;
  }

  // Reuse the costmap's existing TF buffer (no need for a separate listener).
  auto tf_buffer = costmap_ros_->getTfBuffer();
  if (!tf_buffer) {
    RCLCPP_ERROR_THROTTLE(
      rclcpp::get_logger("maintain_yaw_critic"), *node_.lock(), 5000,
      "MaintainYawCritic: costmap TF buffer is null. "
      "Falling back to current yaw.");
    target_yaw_ = pose.theta;
    target_valid_ = false;
    return true;
  }

  // Look up the transform from costmap_frame to reference_frame.
  // The rotation tells us the yaw offset between frames.
  //   yaw_in_ref = yaw_in_costmap + yaw_of_transform
  // We want:     yaw_in_ref = desired_yaw_
  // Therefore:   target_yaw = desired_yaw_ - yaw_of_transform
  try {
    auto transform = tf_buffer->lookupTransform(
      reference_frame_,       // target frame
      costmap_frame,          // source frame
      tf2::TimePointZero,     // latest available
      tf2::Duration(std::chrono::milliseconds(300)));

    tf2::Quaternion q(
      transform.transform.rotation.x,
      transform.transform.rotation.y,
      transform.transform.rotation.z,
      transform.transform.rotation.w);
    double roll, pitch, yaw_offset;
    tf2::Matrix3x3(q).getRPY(roll, pitch, yaw_offset);

    target_yaw_ = angles::normalize_angle(desired_yaw_ - yaw_offset);
    target_valid_ = true;
  }
  catch (const tf2::TransformException & ex) {
    RCLCPP_WARN_THROTTLE(
      rclcpp::get_logger("maintain_yaw_critic"), *node_.lock(), 5000,
      "MaintainYawCritic: TF lookup failed from '%s' to '%s': %s. "
      "Falling back to current yaw.",
      costmap_frame.c_str(), reference_frame_.c_str(), ex.what());
    target_yaw_ = pose.theta;
    target_valid_ = false;
  }

  return true;
}

double MaintainYawCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (traj.poses.empty()) {
    return 0.0;
  }

  // Score the final pose's yaw deviation from the target.
  // Linear penalty so even small deviations produce meaningful cost.
  // With scale=5000, a 1° error gives ~87, which dominates over
  // PathDist (~100-300) and GoalDist (~tens to hundreds).
  double final_yaw = traj.poses.back().theta;
  double yaw_error = angles::shortest_angular_distance(final_yaw, target_yaw_);

  return scale_ * std::fabs(yaw_error);
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::MaintainYawCritic,
  dwb_core::TrajectoryCritic)
