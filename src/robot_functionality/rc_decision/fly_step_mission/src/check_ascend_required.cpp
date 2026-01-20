#include "fly_step_mission/check_ascend_required.hpp"

namespace fly_step_mission
{

CheckAscendRequired::CheckAscendRequired(
    const std::string & name,
    const BT::NodeConfiguration & config
) : BT::ConditionNode(name, config)
{
}

BT::PortsList CheckAscendRequired::providedPorts()
{
    return {
        BT::InputPort<std::string>("task_type", "Current task type to check")
    };
}

BT::NodeStatus CheckAscendRequired::tick()
{
    std::string task_type;
    if (!getInput("task_type", task_type)) {
        // 如果无法获取task_type，默认返回FAILURE
        return BT::NodeStatus::FAILURE;
    }

    // 检查任务类型是否为"ascend"
    if (task_type == "ascend" && task_type != last_task_type_) {
        last_task_type_ = task_type;
        return BT::NodeStatus::SUCCESS;
    }
    
    last_task_type_ = task_type;
    return BT::NodeStatus::FAILURE;
}

} // namespace fly_step_mission