#include "fly_step_mission/check_descend_required.hpp"

namespace fly_step_mission
{

CheckDescendRequired::CheckDescendRequired(
    const std::string & name,
    const BT::NodeConfiguration & config
) : BT::ConditionNode(name, config)
{
}

BT::PortsList CheckDescendRequired::providedPorts()
{
    return {
        BT::InputPort<std::string>("task_type", "Current task type to check")
    };
}

BT::NodeStatus CheckDescendRequired::tick()
{
    std::string task_type;
    if (!getInput("task_type", task_type)) {
        // 如果无法获取task_type，默认返回FAILURE
        return BT::NodeStatus::FAILURE;
    }

    // 检查任务类型是否为"descend"或"delayed_descend"
    if ((task_type == "descend" || task_type == "delayed_descend") && task_type != last_task_type_) {
        last_task_type_ = task_type;
        return BT::NodeStatus::SUCCESS;
    }
    
    last_task_type_ = task_type;
    return BT::NodeStatus::FAILURE;
}

} // namespace fly_step_mission