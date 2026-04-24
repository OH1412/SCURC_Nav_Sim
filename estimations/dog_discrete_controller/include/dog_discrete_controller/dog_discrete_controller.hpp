#ifndef DOG_DISCRETE_CONTROLLER__DOG_DISCRETE_CONTROLLER_HPP_
#define DOG_DISCRETE_CONTROLLER__DOG_DISCRETE_CONTROLLER_HPP_

#include <string>
#include <memory>

// ROS 2 核心库
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"

// Nav2 核心接口
#include "nav2_core/controller.hpp"

// 消息类型
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "nav_msgs/msg/path.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/string.hpp"
#include "usart_pkg/msg/action.hpp"
// TF2 变换
#include "tf2_ros/buffer.h"
#include "dog_discrete_controller/dog_collision_checker.hpp"

namespace dog_nav
{

class DogDiscreteController : public nav2_core::Controller
{
public:
  DogDiscreteController() = default;
  ~DogDiscreteController() override = default;

  // ==============================================================
  // 1. Nav2 必须重载的生命周期函数 (Lifecycle Methods)
  // ==============================================================
  
  // 节点配置阶段调用（读取参数、创建发布者/订阅者）
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;

  // 节点清理阶段调用（释放资源）
  void cleanup() override;

  // 节点激活阶段调用（激活发布者）
  void activate() override;

  // 节点休眠阶段调用（暂停发布者）
  void deactivate() override;

  // ==============================================================
  // 2. Nav2 核心控制与数据接口
  // ==============================================================

  // 核心！10Hz 循环调用的解算函数
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped & pose,
    const geometry_msgs::msg::Twist & velocity,
    nav2_core::GoalChecker * goal_checker) override;

  // 接收由全局规划器传来的最新路径
  void setPlan(const nav_msgs::msg::Path & path) override;

  // 动态限速接口（Nav2 接口要求必须实现，即使我们不用也要写上空函数）
  void setSpeedLimit(const double & speed_limit, const bool & percentage) override;

private:
  // --- ROS 2 底层节点与工具指针 ---
  rclcpp_lifecycle::LifecycleNode::WeakPtr node_;
  std::shared_ptr<tf2_ros::Buffer> tf_;
  std::string plugin_name_;
  rclcpp::Logger logger_ {rclcpp::get_logger("DogDiscreteController")};

  // --- 订阅者与发布者 ---
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr status_sub_;
  // 注意：Nav2 推荐使用 LifecyclePublisher，方便统一管理状态
  rclcpp_lifecycle::LifecyclePublisher<usart_pkg::msg::Action>::SharedPtr cmd_pub_;

  // --- 核心状态与数据 ---
  bool is_stepping_ = false;        // 狗是否正在走步子的标志位
  nav_msgs::msg::Path global_plan_; // 当前缓存的全局路径

  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros_;//（新增：指针，用来存储局部代价地图）
  std::shared_ptr<DogCollisionChecker> collision_checker_;

  // --- 算法参数 (将从 yaml 文件中读取) ---
  double lookahead_dist_; // 预瞄距离（单位：米）
  double yaw_tolerance_;  // 角度容忍度（单位：弧度，超过这个值就发原地旋转指令）
    
  // --- 内部辅助函数 ---
  
  // 状态订阅的回调函数
  void statusCallback(const std_msgs::msg::Bool::SharedPtr msg);
  
  // 核心数学运算：在路径上找到距离当前位置 lookahead_dist_ 的预瞄点
  geometry_msgs::msg::PoseStamped getLookAheadPoint(
    const geometry_msgs::msg::PoseStamped & current_pose,
    const nav_msgs::msg::Path & transformed_plan);// 新增了路径参数
};

}  // namespace dog_nav

#endif  // DOG_DISCRETE_CONTROLLER__DOG_DISCRETE_CONTROLLER_HPP_