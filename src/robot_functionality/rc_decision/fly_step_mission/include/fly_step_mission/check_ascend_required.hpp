#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/condition_node.h>
#include <rclcpp/rclcpp.hpp>

namespace fly_step_mission
{

/**
 * @brief 检查是否需要执行上升任务的条件节点
 */
class CheckAscendRequired : public BT::ConditionNode
{
public:
    CheckAscendRequired(
        const std::string & name,
        const BT::NodeConfiguration & config
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus tick() override;

private:
    std::string last_task_type_;
};

} // namespace fly_step_mission