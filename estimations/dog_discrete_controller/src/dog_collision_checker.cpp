#include "dog_discrete_controller/dog_collision_checker.hpp"
#include "nav2_costmap_2d/cost_values.hpp"
#include "tf2/utils.h"
#include <cmath>

namespace dog_nav
{

DogCollisionChecker::DogCollisionChecker(
  rclcpp_lifecycle::LifecycleNode::SharedPtr node,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)
: node_(node), costmap_ros_(costmap_ros)
{
}

bool DogCollisionChecker::isCollisionFree(
  const geometry_msgs::msg::PoseStamped & current_pose, 
  uint8_t action_id,
  double step_length,
  double turn_angle)
{
  double current_yaw = tf2::getYaw(current_pose.pose.orientation);
  
  // 1. 初始化未来坐标（如果不动，就是当前坐标）
  double future_x = current_pose.pose.position.x;
  double future_y = current_pose.pose.position.y;
  double future_yaw = current_yaw;

  // 2. 根据不同的指令，推演未来位姿
  if (action_id == 2) { // 前进
    future_x += step_length * std::cos(current_yaw);
    future_y += step_length * std::sin(current_yaw);
  } 
  else if (action_id == 9) { // 后退
    future_x -= step_length * std::cos(current_yaw);
    future_y -= step_length * std::sin(current_yaw);
  } 
  else if (action_id == 4) { // 左转
    future_yaw += turn_angle;
  } 
  else if (action_id == 5) { // 右转
    future_yaw -= turn_angle;
  }

  // 3. 拿到代价地图和机器狗 70x45 矩形轮廓
  auto costmap = costmap_ros_->getCostmap();
  std::vector<geometry_msgs::msg::Point> footprint = costmap_ros_->getRobotFootprint();
  nav2_costmap_2d::FootprintCollisionChecker<nav2_costmap_2d::Costmap2D *> footprint_checker(costmap);

  // 4. 将长方形放置到推演出的【未来位置】进行检测
  double footprint_cost = footprint_checker.footprintCostAtPose(
    future_x, future_y, future_yaw, footprint);

  // 5. 安全评估
  if (footprint_cost == static_cast<double>(nav2_costmap_2d::NO_INFORMATION) &&
      costmap_ros_->getLayeredCostmap()->isTrackingUnknown()) {
    RCLCPP_WARN_THROTTLE(logger_, *node_->get_clock(), 1000, "预警：下一步会踏入未知区域！");
    return false; 
  }

  // 150 是安全膨胀区，253 是碰墙，这里设为 150 保证不擦伤肩膀
  if (footprint_cost >= 150.0) { 
    RCLCPP_WARN_THROTTLE(logger_, *node_->get_clock(), 1000, "预警：下一步有碰撞风险 (Cost: %.0f)！", footprint_cost);
    return false; 
  }

  return true; 
}

}  // namespace dog_nav