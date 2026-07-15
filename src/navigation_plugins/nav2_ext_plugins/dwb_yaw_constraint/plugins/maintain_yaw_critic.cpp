/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#include "dwb_yaw_constraint/maintain_yaw_critic.hpp"
#include "dwb_yaw_constraint/critic_dynamic_scale.hpp"
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

  const std::string prefix = dwb_plugin_name_ + "." + name_ + ".";

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

  // Optional: subscribe to nav_segment_yaw for dynamic desired_yaw
  nav2_util::declare_parameter_if_not_declared(
    node,
    prefix + "use_segment_yaw",
    rclcpp::ParameterValue(false));
  nav2_util::declare_parameter_if_not_declared(
    node,
    prefix + "nav_segment_yaw_topic",
    rclcpp::ParameterValue("/mission_bt/nav_segment_yaw"));
  node->get_parameter(prefix + "use_segment_yaw", use_segment_yaw_);
  node->get_parameter(prefix + "nav_segment_yaw_topic", nav_segment_yaw_topic_);

  if (use_segment_yaw_) {
    segment_yaw_sub_ = node->create_subscription<std_msgs::msg::Float64>(
      nav_segment_yaw_topic_,
      rclcpp::QoS(rclcpp::KeepLast(1)).transient_local().reliable(),
      std::bind(&MaintainYawCritic::navSegmentYawCallback, this, std::placeholders::_1));
  }

  nav2_util::declare_parameter_if_not_declared(
    node,
    prefix + "yaw_error_threshold",
    rclcpp::ParameterValue(0.5236));  // ~30 degrees
  node->get_parameter(prefix + "yaw_error_threshold", yaw_error_threshold_);

  nav2_util::declare_parameter_if_not_declared(
    node,
    prefix + "xy_penalty_factor",
    rclcpp::ParameterValue(5.0));
  node->get_parameter(prefix + "xy_penalty_factor", xy_penalty_factor_);

  target_valid_ = false;
  target_yaw_ = 0.0;

  // Cache parameter names for the combined dynamic callback
  scale_param_name_ = prefix + "scale";
  threshold_param_name_ = prefix + "yaw_error_threshold";
  xy_penalty_param_name_ = prefix + "xy_penalty_factor";
  desired_yaw_param_name_ = prefix + "desired_yaw";

  // Same suffix-tolerant matching as registerScaleDynamicCallback:
  // rclcpp may deliver relative or fully-qualified names.
  dyn_params_handler_ = node->add_on_set_parameters_callback(
    [this](const std::vector<rclcpp::Parameter> & parameters) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      for (const auto & param : parameters) {
        if (param.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE) {
          continue;
        }
        const auto & pname = param.get_name();
        if (matchParamName(pname, scale_param_name_)) {
          setScale(param.as_double());
          // RCLCPP_INFO(..., "CRITIC_SCALE_MEM_UPDATED ...");
        } else if (matchParamName(pname, threshold_param_name_)) {
          yaw_error_threshold_ = param.as_double();
          // RCLCPP_INFO(..., "CRITIC_PARAM_MEM_UPDATED ... yaw_error_threshold");
        } else if (matchParamName(pname, xy_penalty_param_name_)) {
          xy_penalty_factor_ = param.as_double();
          // RCLCPP_INFO(..., "CRITIC_PARAM_MEM_UPDATED ... xy_penalty_factor");
        } else if (matchParamName(pname, desired_yaw_param_name_)) {
          desired_yaw_ = param.as_double();
          // RCLCPP_INFO(..., "CRITIC_PARAM_MEM_UPDATED ... desired_yaw");
        }
      }
      return result;
    });

  RCLCPP_INFO(
    node->get_logger(),
    "MaintainYawCritic [%s]: desired_yaw=%.2f rad, ref_frame=%s, "
    "yaw_err_thresh=%.2f rad (%.0f deg), xy_penalty=%.1f, "
    "use_segment_yaw=%s",
    name_.c_str(), desired_yaw_, reference_frame_.c_str(),
    yaw_error_threshold_, yaw_error_threshold_ * 180.0 / M_PI,
    xy_penalty_factor_,
    use_segment_yaw_ ? "true" : "false");
}

bool MaintainYawCritic::prepare(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & /*goal*/,
  const nav_2d_msgs::msg::Path2D & /*global_plan*/)
{
  // Zone switcher writes the param store; keep memory in sync every cycle
  // (on_set_parameters callback often never fires for this plugin).
  if (auto node = node_.lock()) {
    const double before_scale = getScale();
    syncScaleFromParamStore(
      node, scale_param_name_, before_scale,
      [this](double s) { setScale(s); }, "MaintainYaw");
    double thr = yaw_error_threshold_;
    if (node->get_parameter(threshold_param_name_, thr) &&
      std::fabs(thr - yaw_error_threshold_) > 1e-9)
    {
      // RCLCPP_INFO(..., "CRITIC_PARAM_SYNC MaintainYaw yaw_error_threshold ...");
      yaw_error_threshold_ = thr;
    }
    double dy = desired_yaw_;
    if (node->get_parameter(desired_yaw_param_name_, dy) &&
      std::fabs(dy - desired_yaw_) > 1e-9)
    {
      // RCLCPP_INFO(..., "CRITIC_PARAM_SYNC MaintainYaw desired_yaw ...");
      desired_yaw_ = dy;
    }

    // Middle activation: scale 0→active arms one-shot phase-1 (pure yaw until
    // first time |err|≤threshold). Leaving middle (scale→0) clears the latch.
    const double after_scale = getScale();
    if (prev_scale_valid_ && prev_scale_ < 1.0 && after_scale >= 1.0) {
      phase1_pending_ = true;
      // RCLCPP_INFO(..., "MAINTAIN_YAW_PHASE1_ARM ...");
    } else if (after_scale < 1.0) {
      phase1_pending_ = false;
    }
    prev_scale_ = after_scale;
    prev_scale_valid_ = true;
  }

  std::string costmap_frame = costmap_ros_->getGlobalFrameID();

  // If use_segment_yaw_ and we have a valid segment yaw, override desired_yaw_
  double effective_desired_yaw = desired_yaw_;
  if (use_segment_yaw_ && segment_yaw_valid_) {
    effective_desired_yaw = segment_yaw_;
  }

  // If the costmap frame equals the reference frame, no transform is needed
  if (costmap_frame == reference_frame_) {
    target_yaw_ = effective_desired_yaw;
    target_valid_ = true;
    current_yaw_error_ = angles::shortest_angular_distance(pose.theta, target_yaw_);
    maybeFinishPhase1();
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
    current_yaw_error_ = 0.0;  // fallback: using current yaw as target
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

    target_yaw_ = angles::normalize_angle(effective_desired_yaw - yaw_offset);
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

  current_yaw_error_ = angles::shortest_angular_distance(pose.theta, target_yaw_);
  maybeFinishPhase1();
  return true;
}

void MaintainYawCritic::maybeFinishPhase1()
{
  if (!phase1_pending_) {
    return;
  }
  if (std::fabs(current_yaw_error_) > yaw_error_threshold_) {
    return;
  }
  phase1_pending_ = false;
  // RCLCPP_INFO(..., "MAINTAIN_YAW_PHASE1_DONE ...");
}

double MaintainYawCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (traj.poses.empty()) {
    return 0.0;
  }

  double final_yaw = traj.poses.back().theta;
  double yaw_error = angles::shortest_angular_distance(final_yaw, target_yaw_);

  // Phase-1 only while latch armed AND still outside band. Once cleared, never
  // re-enter xy-block mode even if |err| grows above threshold again.
  if (phase1_pending_ && std::fabs(current_yaw_error_) > yaw_error_threshold_) {
    double xy_speed = std::hypot(traj.velocity.x, traj.velocity.y);
    return scale_ * (std::fabs(yaw_error) + xy_penalty_factor_ * xy_speed);
  }

  return scale_ * std::fabs(yaw_error);
}

void MaintainYawCritic::navSegmentYawCallback(
  const std_msgs::msg::Float64::SharedPtr msg)
{
  segment_yaw_ = msg->data;
  segment_yaw_valid_ = true;
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::MaintainYawCritic,
  dwb_core::TrajectoryCritic)
