/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#ifndef DWB_YAW_CONSTRAINT__MAINTAIN_VY_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__MAINTAIN_VY_CRITIC_HPP_

#include <string>
#include "dwb_core/trajectory_critic.hpp"

namespace dwb_yaw_constraint
{

/**
 * @class MaintainVyCritic
 * @brief Penalizes trajectories with non-zero lateral (Y) velocity.
 *
 * For omnidirectional robots navigating through narrow corridors, lateral
 * drift can be dangerous. This critic adds a cost proportional to the
 * absolute lateral velocity in the commanded twist, steering the optimizer
 * toward pure forward (X-only) motion when active.
 *
 * Unlike MaintainYawCritic, this critic operates purely in velocity space
 * and does not require TF transforms — vy is always in the robot body frame.
 *
 * Parameters:
 *   - target_vy (double, default 0.0): Desired lateral velocity [m/s].
 *     Set to 0.0 to lock out lateral motion entirely.
 */
class MaintainVyCritic : public dwb_core::TrajectoryCritic
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
  /// Desired lateral velocity [m/s], typically 0.0 to lock vy
  double target_vy_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__MAINTAIN_VY_CRITIC_HPP_
