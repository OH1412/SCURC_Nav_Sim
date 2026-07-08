/*
 * RotateToPath — DWB critic that penalizes trajectories whose heading deviates
 * from the path tangent direction at the robot's current position.
 *
 * When the robot is far from the path or approaching from an angle, this critic
 * strongly encourages rotating to face along the path before/while moving,
 * resulting in smoother, more natural motion along the planned route.
 */

#ifndef DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_

#include <string>
#include "dwb_core/trajectory_critic.hpp"

namespace dwb_yaw_constraint
{

class RotateToPathCritic : public dwb_core::TrajectoryCritic
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
  /// Compute path tangent yaw at the given pose
  double computeTangentYaw(
    const geometry_msgs::msg::Pose2D & pose,
    const nav_2d_msgs::msg::Path2D & global_plan);

  /// Target yaw from path tangent [rad]
  double target_yaw_{0.0};

  /// Whether a valid tangent was computed
  bool tangent_valid_{false};

  /// Distance along the path to look ahead for tangent computation [m]
  double path_lookahead_dist_{0.5};

  /// Which point along the trajectory to evaluate yaw (-1 = last pose)
  double lookahead_time_{-1.0};

  /// Yaw error threshold [rad] — above this, reject trajectories with
  /// significant linear velocity to force rotation before translation.
  double yaw_error_threshold_{0.087};  // 5 degrees
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_
