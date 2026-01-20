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
 * @brief 动态路径任务执行节点
 * 根据输入的航点序列，动态执行导航和任务
 */
class DynamicPathTaskExecutor : public BT::StatefulActionNode
{
public:
    DynamicPathTaskExecutor(
        const std::string & name,
        const BT::NodeConfiguration & config,
        std::shared_ptr<rclcpp::Node> node
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus onStart() override;
    BT::NodeStatus onRunning() override;
    void onHalted() override;

private:
    std::shared_ptr<rclcpp::Node> node_;
    std::vector<geometry_msgs::msg::PoseStamped> full_path_;
    std::map<std::string, WaypointTaskInfo> wp_task_map_;
    std::vector<std::string> wp_ids_;
    size_t current_index_;
    std::string current_waypoint_id_;
    bool task_executed_;
    bool requires_next_waypoint_task_;
    std::string next_waypoint_task_type_;
    std::string waypoints_file_;
    
    // 当前状态
    enum State {
        NAVIGATING_TO_WAYPOINT,
        CHECKING_TASK,
        EXECUTING_ASCEND,
        EXECUTING_DESCEND,
        COMPLETED
    };
    State state_;
    
    // 目标姿态
    geometry_msgs::msg::PoseStamped current_target_pose_;
    
    // 任务参数
    double target_ascend_height_;
    double target_descend_height_;
    double ascend_speed_;
    double descend_speed_;
    double ascend_max_duration_;
    double descend_max_duration_;
    int ascend_margin_mm_;
    rclcpp::Time action_start_time_;
    
    // 所有航点映射（用于ID查找）
    std::map<std::string, geometry_msgs::msg::PoseStamped> all_wp_map_;
    
    // Nav2 Action Client
    using NavigateToPose = nav2_msgs::action::NavigateToPose;
    using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;
    rclcpp_action::Client<NavigateToPose>::SharedPtr nav_client_;
    GoalHandle::SharedPtr nav_goal_handle_;
    bool nav_goal_sent_;
    bool nav_result_ready_;
    GoalHandle::WrappedResult nav_result_;
    
    // 升降控制
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
    
    // 解析YAML文件
    bool parseTaskInfoFromYaml();
    
    // 获取航点ID
    std::string getWaypointIdByIndex(size_t index);
    
    // Nav2 导航辅助函数
    bool ensureNavClient();
    bool startNavigation(const geometry_msgs::msg::PoseStamped & goal);
    BT::NodeStatus checkNavigationStatus();
    
    // 升降辅助函数
    bool getCurrentZ(double & z_out);
    void publishZVelocity(double z_vel);
};

} // namespace fly_step_mission