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

#include <string>
#include "dwb_core/trajectory_critic.hpp"

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
 * Parameters:
 *   - desired_yaw (double, default 0.0): Desired yaw in reference_frame [rad].
 *   - reference_frame (string, default "map"): Frame in which desired_yaw is defined.
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

  /// Computed target yaw in the costmap frame [rad]
  double target_yaw_;

  /// Whether target_yaw_ was successfully computed from TF
  bool target_valid_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__MAINTAIN_YAW_CRITIC_HPP_
