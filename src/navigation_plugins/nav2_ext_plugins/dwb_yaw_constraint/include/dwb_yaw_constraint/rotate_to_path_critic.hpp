/*
 * RotateToPath — align yaw to the start→goal bearing published by Nav2PoseNode
 * for the current navigation step (direct walk to waypoint).
 */

#ifndef DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_
#define DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_

#include <memory>
#include <string>
#include "dwb_core/trajectory_critic.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"

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
  void navSegmentYawCallback(const std_msgs::msg::Float64::SharedPtr msg);

  /// Fallback when no segment yaw message is available yet.
  double computeGoalBearingYaw(
    const geometry_msgs::msg::Pose2D & pose,
    const geometry_msgs::msg::Pose2D & goal) const;

  double target_yaw_{0.0};
  bool tangent_valid_{false};

  bool use_segment_yaw_{true};
  std::string nav_segment_yaw_topic_{"/mission_bt/nav_segment_yaw"};
  double segment_yaw_{0.0};
  bool segment_yaw_valid_{false};
  rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr segment_yaw_sub_;

  double lookahead_time_{-1.0};
  double yaw_error_threshold_{0.5236};  // ~30 degrees
  std::string scale_param_name_;

  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr dyn_params_handler_;
};

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__ROTATE_TO_PATH_CRITIC_HPP_
