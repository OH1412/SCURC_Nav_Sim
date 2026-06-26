/*
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2024, All rights reserved.
 */

#ifndef DWB_YAW_CONSTRAINT__DECOUPLING_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__DECOUPLING_CRITIC_HPP_

#include <string>
#include "dwb_core/trajectory_critic.hpp"

namespace dwb_yaw_constraint
{

/**
 * @class DecouplingCritic
 * @brief Penalizes trajectories that mix multiple velocity axes simultaneously.
 *
 * For omnidirectional robots, it is often preferable to issue velocity commands
 * that are "decoupled" — primarily one axis at a time (pure translation or
 * pure rotation). This critic adds a cost proportional to the second-largest
 * normalized velocity component, gently steering the optimizer toward
 * single-axis commands without hard restrictions.
 *
 * Small amounts of mixing are lightly penalized; heavy mixing is penalized
 * proportionally more.
 *
 * Parameters:
 *   - max_vx (double, default 1.0): max linear x velocity [m/s], for normalization.
 *   - max_vy (double, default 1.0): max linear y velocity [m/s], for normalization.
 *   - max_vtheta (double, default 5.0): max angular z velocity [rad/s], for normalization.
 */
class DecouplingCritic : public dwb_core::TrajectoryCritic
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
  double max_vx_;
  double max_vy_;
  double max_vtheta_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__DECOUPLING_CRITIC_HPP_
