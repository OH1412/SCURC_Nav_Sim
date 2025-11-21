#ifndef R2_WAYPOINT_LOADER_CPP_WAYPOINT_LOADER_HPP_
#define R2_WAYPOINT_LOADER_CPP_WAYPOINT_LOADER_HPP_

#include <vector>
#include <string>
#include <map>
#include <mutex>
#include <chrono> 
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "nav2_msgs/action/follow_waypoints.hpp"
#include "nav_msgs/nav_msgs/msg/map_meta_data.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
#include "lifecycle_msgs/msg/state.hpp"
#include "./plugins/r2_waypoint_task.hpp" 
#include "./common_structs.hpp"


namespace r2_waypoint_loader_cpp {

using FollowWaypoints = nav2_msgs::action::FollowWaypoints;
using GoalHandleFollow = rclcpp_action::ClientGoalHandle<FollowWaypoints>;

class WaypointLoader : public rclcpp::Node {
public:
    explicit WaypointLoader(const rclcpp::NodeOptions& options = rclcpp::NodeOptions());
    ~WaypointLoader() override = default;

    // 航点关系枚举
    enum class WaypointRelation {
        RELATION_PLUS_3,
        RELATION_MINUS_3,
        RELATION_PLUS_1,
        RELATION_MINUS_1,
        RELATION_ERROR
    };

private:
    std::map<std::string, WaypointTaskInfo> wp_task_map_;  // 航点ID → 任务信息

    // 核心成员变量
    rclcpp_action::Client<FollowWaypoints>::SharedPtr follow_action_client_;
    rclcpp::TimerBase::SharedPtr start_timer_;

    // 任务执行相关组件
    std::shared_ptr<r2_waypoint_loader_cpp::R2WaypointTask> task_plugin_;
    // 航点任务存储
    std::map<std::string, geometry_msgs::msg::PoseStamped> all_wp_map_;
    std::vector<geometry_msgs::msg::PoseStamped> waypoints_;
    std::vector<geometry_msgs::msg::PoseStamped> full_waypoints_;
    std::vector<std::string> prepoints_;  // 存储航点ID列表
    std::vector<int> main_waypoint_ids_;  // 存储主航点ID

    // 状态变量
    std::mutex waypoint_mutex_;
    uint32_t last_processed_waypoint_ = UINT_MAX;
    // uint32_t last_processed_waypoint_ = 0;
    bool rise_triggered_ = false;
    double start_delay_;
    std::string waypoints_path_;

    // 初始化函数
    void init_parameters();  // 初始化参数
    void init_components();  // 初始化组件（包含任务执行器初始化）
    void send_nav_goal();    // 发送导航目标

    // 回调函数
    void on_start_timer();
    bool wait_for_action_server_with_timeout(const std::chrono::seconds& timeout);
    bool wait_for_nav2_system_ready();  // 等待Nav2系统就绪
    void goal_response_callback(const GoalHandleFollow::SharedPtr& goal_handle);
    void feedback_callback(GoalHandleFollow::SharedPtr, const std::shared_ptr<const FollowWaypoints::Feedback> feedback);
    void result_callback(const GoalHandleFollow::WrappedResult& result);

    // 航点处理函数
    bool parse_all_waypoints_from_yaml();
    bool build_full_waypath();
    WaypointRelation judge_waypoint_relation(int start_id, int end_id);
    bool get_transition_points(int start_id, int end_id, geometry_msgs::msg::PoseStamped& trans1, geometry_msgs::msg::PoseStamped& trans2);
    std::string get_wp_id_by_index(uint32_t index);

    // 未使用函数（保留声明，避免编译错误）
    void execute_post_waypoint_actions(int current_wp);
};

}  // namespace r2_waypoint_loader_cpp

#endif  // R2_WAYPOINT_LOADER_CPP_WAYPOINT_LOADER_HPP_
