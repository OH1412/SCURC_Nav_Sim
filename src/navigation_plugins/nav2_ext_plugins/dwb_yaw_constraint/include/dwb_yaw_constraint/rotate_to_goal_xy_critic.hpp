/*
 * RotateToGoalXY — DWB critic with independent x/y goal window (axis-aligned box).
 * Drop-in replacement for dwb_critics::RotateToGoalCritic when using
 * behavior_ext_plugins::SimpleGoalCheckerXY.
 */

#ifndef DWB_YAW_CONSTRAINT__ROTATE_TO_GOAL_XY_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__ROTATE_TO_GOAL_XY_CRITIC_HPP_

#include <memory>
#include <string>
#include "dwb_core/trajectory_critic.hpp"
#include "rclcpp/rclcpp.hpp"

namespace dwb_yaw_constraint
{

class RotateToGoalXYCritic : public dwb_core::TrajectoryCritic
{
public:
  void onInit() override;
  void reset() override;
  bool prepare(
    const geometry_msgs::msg::Pose2D & pose,
    const nav_2d_msgs::msg::Twist2D & vel,
    const geometry_msgs::msg::Pose2D & goal,
    const nav_2d_msgs::msg::Path2D & global_plan) override;
  double scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj) override;

protected:
  virtual double scoreRotation(const dwb_msgs::msg::Trajectory2D & traj);
  void refreshTolerances();

  bool in_window_{false};
  bool rotating_{false};
  double goal_yaw_{0.0};
  double x_goal_tolerance_{0.10};
  double y_goal_tolerance_{0.10};
  double xy_goal_tolerance_{0.10};
  double current_xy_speed_sq_{0.0};
  double stopped_xy_velocity_sq_{0.0};
  double slowing_factor_{5.0};
  double lookahead_time_{-1.0};
  std::string scale_param_name_;

  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr dyn_params_handler_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__ROTATE_TO_GOAL_XY_CRITIC_HPP_
