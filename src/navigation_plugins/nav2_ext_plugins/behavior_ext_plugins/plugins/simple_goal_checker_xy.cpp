// Copyright (c) 2026
//
// SimpleGoalCheckerXY — 支持独立 x/y 容差的目标检查器实现

#include "behavior_ext_plugins/simple_goal_checker_xy.hpp"

#include <cmath>
#include <algorithm>
#include <memory>
#include <string>

#include "angles/angles.h"
#include "nav2_util/node_utils.hpp"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace behavior_ext_plugins
{

SimpleGoalCheckerXY::SimpleGoalCheckerXY()
: x_goal_tolerance_(0.10),
  y_goal_tolerance_(0.10),
  yaw_goal_tolerance_(0.10),
  check_xy_(true),
  xy_goal_tolerance_(0.10)
{
}

void SimpleGoalCheckerXY::initialize(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  const std::string & plugin_name,
  const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> /*costmap_ros*/)
{
  plugin_name_ = plugin_name;
  auto node = parent.lock();
  if (!node) {
    throw std::runtime_error{"SimpleGoalCheckerXY: failed to lock parent node"};
  }

  // 声明参数（与 nav2_controller::SimpleGoalChecker 兼容）
  nav2_util::declare_parameter_if_not_declared(
    node, plugin_name_ + ".xy_goal_tolerance", rclcpp::ParameterValue(0.10));
  nav2_util::declare_parameter_if_not_declared(
    node, plugin_name_ + ".x_goal_tolerance", rclcpp::ParameterValue(-1.0));  // -1 表示"未设置"
  nav2_util::declare_parameter_if_not_declared(
    node, plugin_name_ + ".y_goal_tolerance", rclcpp::ParameterValue(-1.0));  // -1 表示"未设置"
  nav2_util::declare_parameter_if_not_declared(
    node, plugin_name_ + ".yaw_goal_tolerance", rclcpp::ParameterValue(0.10));

  node->get_parameter(plugin_name_ + ".xy_goal_tolerance", xy_goal_tolerance_);
  node->get_parameter(plugin_name_ + ".x_goal_tolerance", x_goal_tolerance_);
  node->get_parameter(plugin_name_ + ".y_goal_tolerance", y_goal_tolerance_);
  node->get_parameter(plugin_name_ + ".yaw_goal_tolerance", yaw_goal_tolerance_);

  // 如果未显式设置 x / y 容差（值为负），回退到 xy_goal_tolerance_
  if (x_goal_tolerance_ < 0.0) {
    x_goal_tolerance_ = xy_goal_tolerance_;
  }
  if (y_goal_tolerance_ < 0.0) {
    y_goal_tolerance_ = xy_goal_tolerance_;
  }

  RCLCPP_INFO(
    node->get_logger(),
    "SimpleGoalCheckerXY [%s] initialized: x_tol=%.3f m, y_tol=%.3f m, yaw_tol=%.3f rad",
    plugin_name_.c_str(), x_goal_tolerance_, y_goal_tolerance_, yaw_goal_tolerance_);

  // 注册动态参数回调
  dyn_params_handler_ = node->add_on_set_parameters_callback(
    [this](std::vector<rclcpp::Parameter> parameters) {
      return dynamicParametersCallback(parameters);
    });
}

void SimpleGoalCheckerXY::reset()
{
  // 无状态需要重置
}

bool SimpleGoalCheckerXY::isGoalReached(
  const geometry_msgs::msg::Pose & query_pose,
  const geometry_msgs::msg::Pose & goal_pose,
  const geometry_msgs::msg::Twist & /*velocity*/)
{
  if (check_xy_) {
    double dx = query_pose.position.x - goal_pose.position.x;
    double dy = query_pose.position.y - goal_pose.position.y;

    // ★ 核心改动：分别检查 x 和 y，而非欧氏距离
    if (std::fabs(dx) > x_goal_tolerance_ ||
        std::fabs(dy) > y_goal_tolerance_) {
      return false;
    }
  }

  // 检查偏航角
  double query_yaw = tf2::getYaw(query_pose.orientation);
  double goal_yaw = tf2::getYaw(goal_pose.orientation);
  double dyaw = angles::shortest_angular_distance(query_yaw, goal_yaw);

  if (std::fabs(dyaw) > yaw_goal_tolerance_) {
    return false;
  }

  return true;
}

bool SimpleGoalCheckerXY::getTolerances(
  geometry_msgs::msg::Pose & pose_tolerance,
  geometry_msgs::msg::Twist & vel_tolerance)
{
  // 返回独立 x/y 容差
  pose_tolerance.position.x = x_goal_tolerance_;
  pose_tolerance.position.y = y_goal_tolerance_;
  pose_tolerance.position.z = 0.0;

  // 角度容差用 orientation.z 表示（yaw 方向）
  pose_tolerance.orientation.z = yaw_goal_tolerance_;

  // 速度容差不检查
  vel_tolerance.linear.x = std::numeric_limits<double>::lowest();
  vel_tolerance.angular.z = std::numeric_limits<double>::lowest();

  return true;
}

rcl_interfaces::msg::SetParametersResult
SimpleGoalCheckerXY::dynamicParametersCallback(std::vector<rclcpp::Parameter> parameters)
{
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = true;

  for (const auto & param : parameters) {
    const std::string & name = param.get_name();

    if (name == plugin_name_ + ".x_goal_tolerance") {
      double val = param.as_double();
      if (val >= 0.0) {
        x_goal_tolerance_ = val;
      }
      // 负值保留当前值（保持 xy 回退）
    } else if (name == plugin_name_ + ".y_goal_tolerance") {
      double val = param.as_double();
      if (val >= 0.0) {
        y_goal_tolerance_ = val;
      }
    } else if (name == plugin_name_ + ".xy_goal_tolerance") {
      xy_goal_tolerance_ = param.as_double();
      // 同时更新 y（如果 y 未独立设置）
      // 注意：x_goal_tolerance_ 的负值标记在此无法精确区分，
      // 因此仅更新 xy_goal_tolerance_ 兜底值，运行时可通过
      // 显式设置 x/y 来覆盖
    } else if (name == plugin_name_ + ".yaw_goal_tolerance") {
      yaw_goal_tolerance_ = param.as_double();
    }
  }

  return result;
}

}  // namespace behavior_ext_plugins

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(behavior_ext_plugins::SimpleGoalCheckerXY, nav2_core::GoalChecker)
