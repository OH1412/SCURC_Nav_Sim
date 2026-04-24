#ifndef DOG_DISCRETE_CONTROLLER__DOG_COLLISION_CHECKER_HPP_
#define DOG_DISCRETE_CONTROLLER__DOG_COLLISION_CHECKER_HPP_

#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "nav2_costmap_2d/costmap_2d_ros.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_costmap_2d/footprint_collision_checker.hpp"

namespace dog_nav
{

/**
 * @class DogCollisionChecker
 * @brief 独立负责机器狗前向碰撞预测的模块
 */
class DogCollisionChecker
{
public:
  /**
   * @brief 构造函数
   * @param node 用于打印日志的节点指针
   * @param costmap_ros 局部代价地图的指针
   */
  DogCollisionChecker(
    rclcpp_lifecycle::LifecycleNode::SharedPtr node,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros);

  ~DogCollisionChecker() = default;

  /**
   * @brief 检查前方指定距离处是否安全
   * @param current_pose 机器狗当前的位姿
   * @param forward_dist 向前探测的距离（米）
   * @return true 如果安全
   * @return false 如果检测到碰撞危险
   */
  bool isCollisionFree(
    const geometry_msgs::msg::PoseStamped & current_pose,
    uint8_t action_id,
    double step_length,
    double turn_angle);

private:
  rclcpp_lifecycle::LifecycleNode::SharedPtr node_;
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros_;
  rclcpp::Logger logger_{rclcpp::get_logger("DogCollisionChecker")};
};

}  // namespace dog_nav

#endif  // DOG_DISCRETE_CONTROLLER__DOG_COLLISION_CHECKER_HPP_