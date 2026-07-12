/*
 * GoalYAlignCritic — penalizes Y deviation from goal Y throughout navigation.
 * Designed for mp=0 corridor transit: keeps robot Y aligned to target Y
 * continuously, independent of the global path.
 */

#ifndef DWB_YAW_CONSTRAINT__GOAL_Y_ALIGN_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__GOAL_Y_ALIGN_CRITIC_HPP_

#include <memory>
#include <string>
#include "dwb_core/trajectory_critic.hpp"
#include "rclcpp/rclcpp.hpp"

namespace dwb_yaw_constraint
{

/**
 * @class GoalYAlignCritic
 * @brief Scores trajectories by how close the final pose Y is to the goal Y.
 *
 * Unlike PathDist (which tracks the global path), this critic directly penalizes
 * |traj_y - goal_y| at every control cycle. This provides continuous Y tracking
 * even when the global path has lateral deviations.
 *
 * Parameters:
 *   - scale (double, via dynamic callback): Critic weight (0.0 = disabled).
 */
class GoalYAlignCritic : public dwb_core::TrajectoryCritic
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
  /// Goal Y position [m] in costmap frame, set in prepare()
  double goal_y_{0.0};

  /// Whether goal_y_ is valid
  bool goal_valid_{false};

  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr dyn_params_handler_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__GOAL_Y_ALIGN_CRITIC_HPP_
