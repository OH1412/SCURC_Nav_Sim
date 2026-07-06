// Copyright (c) 2026
//
// SimpleGoalCheckerXY — 支持独立 x/y 容差的目标检查器
//
// 与 nav2_controller::SimpleGoalChecker 的区别：
//   - 原版：xy_goal_tolerance 一个值同时约束 x 和 y（欧氏距离）
//   - 本版：x_goal_tolerance / y_goal_tolerance 分别独立约束
//   - 向后兼容：若未设置 x/y 容差，自动回退到 xy_goal_tolerance
//
// 使用方式（nav2_params.yaml）：
//   general_goal_checker:
//     plugin: "behavior_ext_plugins::SimpleGoalCheckerXY"
//     x_goal_tolerance: 0.10       # x 方向独立容差 (m)
//     y_goal_tolerance: 0.05       # y 方向独立容差 (m)
//     yaw_goal_tolerance: 0.17453  # 角度容差 (rad)

#ifndef BEHAVIOR_EXT_PLUGINS__SIMPLE_GOAL_CHECKER_XY_HPP_
#define BEHAVIOR_EXT_PLUGINS__SIMPLE_GOAL_CHECKER_XY_HPP_

#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "nav2_core/goal_checker.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"

namespace behavior_ext_plugins
{

/**
 * @class SimpleGoalCheckerXY
 * @brief Goal Checker plugin that checks x/y position independently
 *
 * Unlike nav2_controller::SimpleGoalChecker which uses a single xy_goal_tolerance
 * (Euclidean distance), this plugin checks |dx| and |dy| separately against
 * x_goal_tolerance and y_goal_tolerance. This allows asymmetric tolerances,
 * useful when the robot needs tighter control in one axis (e.g., lateral alignment).
 */
class SimpleGoalCheckerXY : public nav2_core::GoalChecker
{
public:
  SimpleGoalCheckerXY();
  ~SimpleGoalCheckerXY() override = default;

  void initialize(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    const std::string & plugin_name,
    const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;

  void reset() override;

  bool isGoalReached(
    const geometry_msgs::msg::Pose & query_pose,
    const geometry_msgs::msg::Pose & goal_pose,
    const geometry_msgs::msg::Twist & velocity) override;

  bool getTolerances(
    geometry_msgs::msg::Pose & pose_tolerance,
    geometry_msgs::msg::Twist & vel_tolerance) override;

protected:
  // 独立 x/y 容差（如果有设置），否则回退到 xy_goal_tolerance_
  double x_goal_tolerance_;
  double y_goal_tolerance_;
  double yaw_goal_tolerance_;
  bool check_xy_;

  // 兼容参数：未显式设置 x/y 时作为公共兜底值
  double xy_goal_tolerance_;

  // Dynamic parameters handler
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr dyn_params_handler_;
  std::string plugin_name_;

  /**
   * @brief Callback executed when a parameter change is detected
   */
  rcl_interfaces::msg::SetParametersResult
  dynamicParametersCallback(std::vector<rclcpp::Parameter> parameters);
};

}  // namespace behavior_ext_plugins

#endif  // BEHAVIOR_EXT_PLUGINS__SIMPLE_GOAL_CHECKER_XY_HPP_
