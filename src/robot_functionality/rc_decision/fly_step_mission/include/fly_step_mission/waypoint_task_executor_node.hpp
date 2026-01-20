#pragma once

#include <memory>
#include <string>
#include <vector>
#include <map>
#include <functional>

#include <behaviortree_cpp_v3/action_node.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

#include "fly_step_mission/waypoint_mission_node.hpp"

namespace fly_step_mission
{

/**
 * @brief 航点任务执行节点
 * 检查当前航点是否有关联的任务（上升/下降），如果有则执行相应任务
 */
class WaypointTaskExecutorNode : public BT::SyncActionNode
{
public:
    WaypointTaskExecutorNode(
        const std::string & name,
        const BT::NodeConfiguration & config,
        std::shared_ptr<rclcpp::Node> node
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus tick() override;

private:
    std::shared_ptr<rclcpp::Node> node_;
    std::map<std::string, WaypointTaskInfo> wp_task_map_;
};

} // namespace fly_step_mission