// Copyright (c) 2026
//
// ArmControl BT Action Node 实现 — 机械臂控制行为树节点
//

#include "behavior_ext_plugins/arm_control_bt_node.hpp"
#include "behavior_ext_plugins/set_pose_bt_node.hpp"

namespace behavior_ext_plugins
{

ArmControlAction::ArmControlAction(
  const std::string & xml_tag_name,
  const std::string & action_name,
  const BT::NodeConfiguration & conf)
: nav2_behavior_tree::BtActionNode<behavior_ext_plugins::action::ArmControl>(
    xml_tag_name, action_name, conf)
{
}

void ArmControlAction::on_tick()
{
  // 从 BT 端口读取 map 坐标系下的目标位姿
  geometry_msgs::msg::PoseStamped target_pose;
  if (!getInput<geometry_msgs::msg::PoseStamped>("target_pose", target_pose)) {
    RCLCPP_ERROR(node_->get_logger(),
      "[ArmControl] Missing input port 'target_pose' — arm control aborted.");
    return;
  }

  // 确保 frame_id 为 map
  if (target_pose.header.frame_id.empty()) {
    target_pose.header.frame_id = "map";
  }

  // 填充 action goal
  goal_.target_pose = target_pose;

  RCLCPP_INFO(node_->get_logger(),
    "[ArmControl] Sending arm control goal: map_frame target=(%.2f, %.2f, %.2f)",
    target_pose.pose.position.x,
    target_pose.pose.position.y,
    target_pose.pose.position.z);
}

BT::NodeStatus ArmControlAction::on_success()
{
  // 将变换后的 base_link 坐标写回 BT 黑板
  setOutput("base_link_pose", result_.result->base_link_pose);

  RCLCPP_INFO(node_->get_logger(),
    "[ArmControl] Arm task completed successfully. "
    "base_link pose: (%.2f, %.2f, %.2f) — %s",
    result_.result->base_link_pose.pose.position.x,
    result_.result->base_link_pose.pose.position.y,
    result_.result->base_link_pose.pose.position.z,
    result_.result->message.c_str());

  return BT::NodeStatus::SUCCESS;
}

BT::NodeStatus ArmControlAction::on_aborted()
{
  RCLCPP_ERROR(node_->get_logger(),
    "[ArmControl] Arm task FAILED: %s",
    result_.result->message.c_str());

  return BT::NodeStatus::FAILURE;
}

}  // namespace behavior_ext_plugins

// ============================================================================
// BT 节点注册 — 通过 BehaviorTree.CPP 插件机制导出
// ============================================================================
// 当 libbehavior_ext_plugins_lib.so 被加载时，
// BT::BehaviorTreeFactory 自动调用此函数完成节点注册。
// 之后在 BT XML 中即可使用 <ArmControl .../> 标签。
//
// 必须定义 BT_PLUGIN_EXPORT，否则 BTCPP_EXPORT 展开为 static
// 导致 BT_RegisterNodesFromPlugin 无法被外部链接。
#define BT_PLUGIN_EXPORT
#include "behaviortree_cpp_v3/bt_factory.h"

BT_REGISTER_NODES(factory)
{
  // ArmControl — 机械臂抓取 Action 节点
  BT::NodeBuilder arm_builder = [](const std::string & name,
                                    const BT::NodeConfiguration & config)
      -> std::unique_ptr<BT::TreeNode> {
    return std::make_unique<behavior_ext_plugins::ArmControlAction>(
      name, "arm_control", config);
  };
  factory.registerBuilder<behavior_ext_plugins::ArmControlAction>(
    "ArmControl", arm_builder);

  // SetPoseStamped — 将 x/y/z/yaw 打包为 PoseStamped 写入黑board
  BT::NodeBuilder setpose_builder = [](const std::string & name,
                                        const BT::NodeConfiguration & config)
      -> std::unique_ptr<BT::TreeNode> {
    return std::make_unique<behavior_ext_plugins::SetPoseStamped>(
      name, config);
  };
  factory.registerBuilder<behavior_ext_plugins::SetPoseStamped>(
    "SetPoseStamped", setpose_builder);
}
