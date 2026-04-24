#include "dog_discrete_controller/dog_discrete_controller.hpp"
#include "nav2_util/node_utils.hpp"
#include "nav2_util/geometry_utils.hpp"
#include "tf2/utils.h"
#include "angles/angles.h"
#include <cmath>
#include "usart_pkg/msg/action.hpp"


using nav2_util::declare_parameter_if_not_declared;

namespace dog_nav
{

// =========================================================================
// 1. 生命周期：配置阶段 (读取参数，初始化接口)
// =========================================================================
void DogDiscreteController::configure(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)//特意取消注释
{
  node_ = parent;
  auto node = node_.lock();
  plugin_name_ = name;
  tf_ = tf;
  costmap_ros_ = costmap_ros;

  // 声明并读取参数 (在 nav2_params.yaml 中配置)
  declare_parameter_if_not_declared(node, plugin_name_ + ".lookahead_dist", rclcpp::ParameterValue(0.15));
  declare_parameter_if_not_declared(node, plugin_name_ + ".yaw_tolerance", rclcpp::ParameterValue(0.08)); // 约 4.5 度

  node->get_parameter(plugin_name_ + ".lookahead_dist", lookahead_dist_);
  node->get_parameter(plugin_name_ + ".yaw_tolerance", yaw_tolerance_);

  // 订阅狗的执行状态 (必须与底层发布的话题名完全一致)
  status_sub_ = node->create_subscription<std_msgs::msg::Bool>(
    "/dog_status/is_stepping", 10,
    std::bind(&DogDiscreteController::statusCallback, this, std::placeholders::_1));

  // 发布离散指令 (第一个字节发送动作指令1:前进, 2:后退, 3:左转, 4:右转, 0:停止，第二个字节发送速度指令0：慢，1：中，2：会)
  cmd_pub_ = node->create_publisher<usart_pkg::msg::Action>("/dog_step_cmd", 10);

  collision_checker_ = std::make_shared<DogCollisionChecker>(node, costmap_ros_);
}

// =========================================================================
// 2. 生命周期：激活、暂停、清理
// =========================================================================
void DogDiscreteController::cleanup()
{
  cmd_pub_.reset();
  status_sub_.reset();
}

void DogDiscreteController::activate()
{
  cmd_pub_->on_activate();
}

void DogDiscreteController::deactivate()
{
  cmd_pub_->on_deactivate();
}

// =========================================================================
// 3. 数据接收与回调
// =========================================================================
void DogDiscreteController::setPlan(const nav_msgs::msg::Path & path)
{
  global_plan_ = path;
  RCLCPP_INFO(logger_, "setPlan received: %zu poses", global_plan_.poses.size());
}

void DogDiscreteController::statusCallback(const std_msgs::msg::Bool::SharedPtr msg)
{
  is_stepping_ = msg->data;
  auto node = node_.lock();
  if (node) {
    RCLCPP_INFO_THROTTLE(
      logger_, *node->get_clock(), 1000,
      "statusCallback: is_stepping=%s", is_stepping_ ? "true" : "false");
  }
}

void DogDiscreteController::setSpeedLimit(const double & /*speed_limit*/, const bool & /*percentage*/)
{
  // 离散步态不需要连续动态限速，保持为空即可
}

// =========================================================================
// 4. 辅助函数：在全局路径上寻找预瞄点 (Lookahead Point)
// =========================================================================
geometry_msgs::msg::PoseStamped DogDiscreteController::getLookAheadPoint(
  const geometry_msgs::msg::PoseStamped & current_pose,
  const nav_msgs::msg::Path & transformed_plan)
{ 
  // 如果路径为空，保底返回当前位置
  if (transformed_plan.poses.empty()) {
    return current_pose;
  }

  // 因为 transformed_plan 已经被 transformGlobalPlan 裁剪过了
  // 它的第 0 个点就是离狗最近的点，我们直接从这里往后找
  for (const auto & pose : transformed_plan.poses) {
    double dx = pose.pose.position.x - current_pose.pose.position.x;
    double dy = pose.pose.position.y - current_pose.pose.position.y;
    double dist = std::hypot(dx, dy);

    if (dist >= lookahead_dist_) {
      return pose; // 找到了第一个超过预瞄距离的点
    }
  }

  // 保底：如果整条路径都很短，没超过预瞄距离，就返回路径的最后一个点
  return transformed_plan.poses.back();
}

// =========================================================================
// 5. 🌟 核心算法：路径追踪与离散指令下发 (10Hz调用)
// =========================================================================
geometry_msgs::msg::TwistStamped DogDiscreteController::computeVelocityCommands(
  const geometry_msgs::msg::PoseStamped & pose,
  const geometry_msgs::msg::Twist & velocity,
  nav2_core::GoalChecker * goal_checker)
{
  // 构造返回给 Nav2 框架的零速度
  geometry_msgs::msg::TwistStamped zero_cmd_vel;
  zero_cmd_vel.header.frame_id = "base_link";
  zero_cmd_vel.twist.linear.x = 0.0;
  zero_cmd_vel.twist.angular.z = 0.0;

  // 【核心约束1：状态锁】
  // if (!is_stepping_) {
  //   // if (node) {
  //   //   RCLCPP_WARN_THROTTLE(
  //   //     logger_, *node->get_clock(), 1000,
  //   //     "Skip publish: is_stepping_=true, waiting for motion complete.");
  //   // }
  //   RCLCPP_ERROR(
  //     logger_,
  //     "myinfo: is_stepping=%s", is_stepping_ ? "true" : "false");
    
  //   return zero_cmd_vel;
  // }

  // 1. 局部路径转换与裁剪逻辑 (保持你原来的代码逻辑)
  nav_msgs::msg::Path local_plan;
  local_plan.header.frame_id = pose.header.frame_id; 

  try {
    for (auto global_pose : global_plan_.poses) {
      geometry_msgs::msg::PoseStamped transformed_pose;
      global_pose.header.frame_id = global_plan_.header.frame_id;
      global_pose.header.stamp = rclcpp::Time(0); 
      transformed_pose = tf_->transform(global_pose, pose.header.frame_id);
      local_plan.poses.push_back(transformed_pose);
    }
  } catch (tf2::TransformException & ex) {
    RCLCPP_WARN_THROTTLE(logger_, *node_.lock()->get_clock(), 1000, "TF转换失败！");
    
    // 安全起见，发送站立/停止指令 (1)
    usart_pkg::msg::Action stop_cmd;
    stop_cmd.action_id = 1; // standup
    stop_cmd.speed_level = 0;
    cmd_pub_->publish(stop_cmd);
    return zero_cmd_vel;
  }

  // 裁剪路径
  double min_dist = std::numeric_limits<double>::max();
  size_t closest_index = 0;
  for (size_t i = 0; i < local_plan.poses.size(); ++i) {
    double dx = local_plan.poses[i].pose.position.x - pose.pose.position.x;
    double dy = local_plan.poses[i].pose.position.y - pose.pose.position.y;
    double dist = std::hypot(dx, dy);
    if (dist < min_dist) {
      min_dist = dist;
      closest_index = i;
    }
  }
  local_plan.poses.erase(local_plan.poses.begin(), local_plan.poses.begin() + closest_index);

  // 2. 获取预瞄点
  geometry_msgs::msg::PoseStamped target_pose = getLookAheadPoint(pose, local_plan);

  // 3. 计算偏差
  double dx = target_pose.pose.position.x - pose.pose.position.x;
  double dy = target_pose.pose.position.y - pose.pose.position.y;
  double distance_error = std::hypot(dx, dy);

  // A. 终点检查
  if (global_plan_.poses.empty()) {
    auto node = node_.lock();
    if (node) {
      RCLCPP_WARN_THROTTLE(
        logger_, *node->get_clock(), 1000,
        "Skip publish: global_plan_ is empty (setPlan not received or empty path).");
    }
    return zero_cmd_vel;
  }

  geometry_msgs::msg::Pose goal_pose = global_plan_.poses.back().pose;
  if (goal_checker->isGoalReached(pose.pose, goal_pose, velocity)) {
    RCLCPP_INFO(logger_, "已到达终点，切换至站立状态。");
    usart_pkg::msg::Action stand_cmd;
    stand_cmd.action_id = 1; // standup
    stand_cmd.speed_level = 0;
    cmd_pub_->publish(stand_cmd);
    return zero_cmd_vel;
  }

  // B. 角度计算
  double target_yaw = std::atan2(dy, dx);
  double current_yaw = tf2::getYaw(pose.pose.orientation);
  double yaw_error = angles::shortest_angular_distance(current_yaw, target_yaw);

  // 4. 【新版离散决策树】
  usart_pkg::msg::Action step_cmd;

  // 4.1 先在脑子里算出理论上的最优动作意图 (Intended Action)
  uint8_t intended_action = 1; // 默认站立
  if (std::abs(yaw_error) > 2.6) {
    intended_action = 9; // 想后退
  } else if (std::abs(yaw_error) > yaw_tolerance_) {
    intended_action = (yaw_error > 0) ? 4 : 5; // 想左转或右转
  } else if (distance_error > 0.04) {
    intended_action = 2; // 想前进
  }
  // 4.2 【测试期强制安全锁】：映射出对应的物理步长参数
  // 无论多远，目前全部锁死为 0 档极慢速测试
  uint8_t intended_speed = 0;  // 永远下发 0 档速度
  double physical_step = 0.09; // 0档对应的平移步长 (9cm)
  double turn_angle = 0.1;     // 0档对应的旋转弧度 (约5.7度)
  step_cmd.speed_level = 0; // 默认所有动作速度等级均为 0

  // 4.3 拿着算好的意图和步长参数，去查 70x45cm 的真实轮廓会不会撞墙
  if (collision_checker_->isCollisionFree(pose, intended_action, physical_step, turn_angle)) {
    
    // 将刚才算好的意图装填进发送包
    step_cmd.action_id = intended_action; 
    step_cmd.speed_level = intended_speed;
  
  } else {
    //  发生碰撞预警，强行篡改指令为原地待命
    RCLCPP_WARN(logger_, "防撞触发！试图执行动作 %d 被拦截，强行切换至待命状态！", intended_action);
    step_cmd.action_id = 1; // 1 为站立 (standup)
    step_cmd.speed_level = 0;
  }
  // 5. 下发指令
  auto node = node_.lock();
  if (node) {
    RCLCPP_INFO_THROTTLE(
      logger_, *node->get_clock(), 1000,
      "Publish /dog_step_cmd: action_id=%u speed_level=%u", step_cmd.action_id, step_cmd.speed_level);
  }
  cmd_pub_->publish(step_cmd);

  return zero_cmd_vel;
}

}// namespace dog_nav

// 注册插件
#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(dog_nav::DogDiscreteController, nav2_core::Controller)