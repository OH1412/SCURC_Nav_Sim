/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *   * Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 */

#ifndef DWB_YAW_CONSTRAINT__MAINTAIN_YAW_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__MAINTAIN_YAW_CRITIC_HPP_

#include <memory>
#include <string>
#include "dwb_core/trajectory_critic.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"

namespace dwb_yaw_constraint
{

/**
 * @class MaintainYawCritic
 * @brief Penalizes trajectories whose final yaw deviates from a desired yaw.
 *
 * This critic is designed for omnidirectional robots that should maintain a
 * fixed yaw (e.g., always face the map's +x direction) regardless of the
 * path direction.
 *
 * The desired yaw is specified in a reference_frame (e.g., "map"), and the
 * critic uses TF (via the costmap's existing TF buffer) to compute the
 * corresponding target yaw in the costmap frame (typically "odom" for local
 * planning). This ensures yaw correction is properly integrated into DWB's
 * trajectory optimization.
 *
 * Two-phase behavior when current yaw error exceeds yaw_error_threshold:
 *   Phase 1 (correction): Heavily penalizes xy motion to force pure rotation
 *                         toward the target yaw.
 *   Phase 2 (normal):     Only penalizes yaw deviation, allowing free xy
 *                         motion while maintaining the target yaw.
 * This allows mid-navigation planner switches (e.g. edge→middle at 1m from
 * goal) without the robot trying to move sideways while the yaw is still
 * far from the desired orientation.
 *
 * Parameters:
 *   - desired_yaw (double, default 0.0): Desired yaw in reference_frame [rad].
 *   - reference_frame (string, default "map"): Frame in which desired_yaw is defined.
 *   - yaw_error_threshold (double, default 0.5236): Max yaw error [rad] before
 *     entering correction phase. Default ~30 degrees.
 *   - xy_penalty_factor (double, default 5.0): Multiplier for xy speed penalty
 *     during correction phase. Higher = more aggressive rotation-first behavior.
 */
class MaintainYawCritic : public dwb_core::TrajectoryCritic
{
public:
  void onInit() override;
  bool prepare(
    const geometry_msgs::msg::Pose2D & pose,
    const nav_2d_msgs::msg::Twist2D & vel,
    const geometry_msgs::msg::Pose2D & goal,
    const nav_2d_msgs::msg::Path2D & global_plan) override;
  double scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj) override;

private:
  /// Desired yaw in the reference frame [rad]
  double desired_yaw_;

  /// The frame in which desired_yaw is specified (e.g., "map")
  std::string reference_frame_;

  /// Callback for dynamic desired_yaw from segment yaw topic
  void navSegmentYawCallback(const std_msgs::msg::Float64::SharedPtr msg);

  /// Computed target yaw in the costmap frame [rad]
  double target_yaw_;

  /// Whether target_yaw_ was successfully computed from TF
  bool target_valid_;

  /// Current yaw error (pose.theta vs target_yaw_), computed in prepare()
  double current_yaw_error_{0.0};

  /// Threshold [rad] above which correction phase is active (default ~30°)
  double yaw_error_threshold_{0.5236};

  /// Multiplier for xy speed penalty during correction phase
  double xy_penalty_factor_{5.0};

  /// Whether to use nav_segment_yaw topic for dynamic desired_yaw
  bool use_segment_yaw_{false};
  /// Topic name for dynamic desired_yaw override
  std::string nav_segment_yaw_topic_{"/mission_bt/nav_segment_yaw"};
  /// Latest segment yaw from topic (NaN when not yet received)
  double segment_yaw_{0.0};
  /// Whether a segment yaw has been received
  bool segment_yaw_valid_{false};
  /// Subscriber for dynamic desired_yaw
  rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr segment_yaw_sub_;

  /// Cached parameter names for the dynamic callback
  std::string scale_param_name_;
  std::string threshold_param_name_;
  std::string xy_penalty_param_name_;

  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr dyn_params_handler_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__MAINTAIN_YAW_CRITIC_HPP_
