// Copyright (c) 2026
//
// ArmControl BT Action Node — 机械臂控制行为树节点
// 在 navigate_waypoints_with_task.xml 中替代 TODO 占位符，
// 通过 ROS2 Action 调用 arm_control_server 完成 map→base_link 坐标变换与抓取任务。
//

#ifndef BEHAVIOR_EXT_PLUGINS__ARM_CONTROL_BT_NODE_HPP_
#define BEHAVIOR_EXT_PLUGINS__ARM_CONTROL_BT_NODE_HPP_

#include <string>

#include "nav2_behavior_tree/bt_action_node.hpp"
#include "behavior_ext_plugins/action/arm_control.hpp"

namespace behavior_ext_plugins
{

/**
 * @brief 机械臂控制 BT 动作节点
 *
 * 继承 BtActionNode<ArmControl>，封装对 arm_control Action Server 的调用。
 * 在 BT XML 中使用标签 <ArmControl .../> 即可触发。
 */
class ArmControlAction : public nav2_behavior_tree::BtActionNode<
  behavior_ext_plugins::action::ArmControl>
{
public:
  /**
   * @brief 构造函数
   * @param xml_tag_name XML 标签名（BT 引擎传入）
   * @param action_name  Action 服务名
   * @param conf         BT 节点配置
   */
  ArmControlAction(
    const std::string & xml_tag_name,
    const std::string & action_name,
    const BT::NodeConfiguration & conf);

  /**
   * @brief 每 tick 调用，用于填充 action goal
   */
  void on_tick() override;

  /**
   * @brief action 成功完成时调用
   */
  BT::NodeStatus on_success() override;

  /**
   * @brief action 被中断/失败时调用
   */
  BT::NodeStatus on_aborted() override;

  /**
   * @brief 声明该节点提供的 BT 端口
   */
  static BT::PortsList providedPorts()
  {
    return providedBasicPorts(
      {
        BT::InputPort<geometry_msgs::msg::PoseStamped>(
          "target_pose", "Target pose in map frame for arm control"),
        BT::OutputPort<geometry_msgs::msg::PoseStamped>(
          "base_link_pose", "Transformed pose in base_link frame"),
      });
  }
};

}  // namespace behavior_ext_plugins

#endif  // BEHAVIOR_EXT_PLUGINS__ARM_CONTROL_BT_NODE_HPP_
