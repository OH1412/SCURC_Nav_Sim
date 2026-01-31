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
#include <yaml-cpp/yaml.h>
#include <fstream>

#include "fly_step_mission/waypoint_mission_node.hpp"

namespace fly_step_mission
{

/**
 * @brief 航点路径生成节点
 * 根据输入的主航点ID列表，从YAML文件中生成完整的路径（包括过渡航点）
 */
class PathGeneratorNode : public BT::SyncActionNode
{
public:
    PathGeneratorNode(
        const std::string & name,
        const BT::NodeConfiguration & config,
        std::shared_ptr<rclcpp::Node> node
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus tick() override;

private:
    /**
     * @brief 解析YAML文件中的所有航点
     */
    bool parseAllWaypointsFromYaml();

    /**
     * @brief 根据主航点关系判断类型
     */
    WaypointRelation judgeWaypointRelation(int start_id, int end_id);

    /**
     * @brief 根据主航点关系获取两个过渡点
     */
    bool getTransitionPoints(int start_id, int end_id, 
        geometry_msgs::msg::PoseStamped& trans1, geometry_msgs::msg::PoseStamped& trans2);

    /**
     * @brief 构建完整路径（主航点+过渡点）
     */
    bool buildFullWaypath();

    std::shared_ptr<rclcpp::Node> node_;
    std::string waypoints_file_;
    std::map<std::string, geometry_msgs::msg::PoseStamped> all_wp_map_;
    std::map<std::string, WaypointTaskInfo> wp_task_map_;
    std::vector<std::string> prepoints_;
    std::vector<int> main_waypoint_ids_;
    std::vector<geometry_msgs::msg::PoseStamped> waypoints_;
    std::vector<geometry_msgs::msg::PoseStamped> full_waypoints_;
};

} // namespace fly_step_mission