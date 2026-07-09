#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <legged_mission_bt/msg/nav_reached.hpp>
#include <nav2_msgs/action/navigate_to_pose.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <std_msgs/msg/float64.hpp>
#include <std_msgs/msg/string.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include "legged_mission_bt/waypoint_registry.hpp"

class Nav2PoseNode : public BT::StatefulActionNode
{
public:
  using NavigateToPose = nav2_msgs::action::NavigateToPose;
  using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;

  Nav2PoseNode(
    const std::string & name,
    const BT::NodeConfiguration & config,
    std::shared_ptr<rclcpp::Node> node,
    std::shared_ptr<legged_mission_bt::WaypointRegistry> registry);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  bool ensureClient();
  bool resolveGoal(std::string & frame_id, double & x, double & y, double & yaw);
  bool sendGoal(const std::string & frame_id, double x, double y, double yaw);
  void publishNavReached(const std::string & nav_id);
  void publishNavZone(const std::string & zone, const std::string & reason = "");
  void publishNavSegmentYaw(
    const std::string & frame_id, double goal_x, double goal_y, double goal_yaw);
  void resetNavProgressLogSchedule();
  void maybeLogNavProgress();
  bool getCurrentStateInGoalFrame(
    double & x, double & y, double & yaw, double & vx, double & vy, double & wz) const;

  geometry_msgs::msg::PoseStamped makePose(
    const std::string & frame_id,
    double x, double y, double yaw);

  std::shared_ptr<rclcpp::Node> node_;
  std::shared_ptr<legged_mission_bt::WaypointRegistry> registry_;
  rclcpp_action::Client<NavigateToPose>::SharedPtr client_;
  rclcpp::Publisher<legged_mission_bt::msg::NavReached>::SharedPtr nav_reached_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr nav_zone_pub_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr nav_segment_yaw_pub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  nav_msgs::msg::Odometry::SharedPtr latest_odom_;

  std::string odom_topic_{"/state_estimation"};
  std::string base_frame_{"base_link"};
  double nav_progress_log_interval_{5.0};
  rclcpp::Time nav_progress_start_;
  rclcpp::Time next_progress_log_time_;

  std::string resolved_nav_id_;
  std::string resolved_frame_id_;
  double resolved_x_{0.0};
  double resolved_y_{0.0};
  double resolved_yaw_{0.0};

  GoalHandle::SharedPtr goal_handle_;
  GoalHandle::WrappedResult result_;
  bool goal_sent_{false};
  bool result_ready_{false};
  bool waiting_for_wp_{false};
  std::string wp_id_;
  int motion_planner_{0};               ///< 0=edge front-tangent + corridor multi-phase, 1=edge front-tangent, 2=edge rear-tangent
  bool limit_yaw_{false};              ///< Derived: true when motion_planner_==0
  bool middle_zone_applied_{false};    ///< Whether distance-based MIDDLE zone switch has fired
  double middle_zone_distance_{1.0};   ///< Distance [m] from goal to trigger MIDDLE switch
  rclcpp::Time resolve_start_;
  double waypoint_wait_timeout_{120.0};

  // ── Multi-phase corridor navigation (motion_planner_ == 0) ────────────
  /// Corridor waypoints (configurable via ROS params, defaults match p1 geometry)
  double corridor_entry_x_{2.3395};
  double corridor_entry_y_{-1.7000};
  double corridor_exit_x_{3.8315};

  /// Navigation phases for corridor traversal
  enum class CorridorPhase {
    APPROACH,   ///< Before corridor: edge zone, tangent toward entry point
    CORRIDOR,   ///< Inside corridor: middle zone, yaw=0
    EXIT,       ///< Past corridor exit: edge zone, tangent toward final goal
    FINAL       ///< Within middle_zone_distance_ of goal: middle zone, yaw=0
  };
  CorridorPhase corridor_phase_{CorridorPhase::APPROACH};
  bool corridor_phase_active_{false};  ///< True when multi-phase logic is active this nav step

  /// Determine current phase from robot position and publish zone / segment_yaw as needed.
  /// When phase changes, cancels the current navigate_to_pose goal and sends a new one
  /// toward the region's target waypoint.
  /// Returns true if phase changed.
  bool updateCorridorPhase();

  /// Cancel current nav goal (if any) and send a new one to the effective target.
  /// Used by updateCorridorPhase() to switch sub-goals without stopping.
  bool resendNavGoal();

  /// Original final goal — saved at onStart() and restored for the FINAL phase
  double original_goal_x_{0.0};
  double original_goal_y_{0.0};
  double original_goal_yaw_{0.0};

  /// Monotonic counter to tag each sendGoal() call; result callbacks only apply
  /// when the tag matches, preventing stale results from cancelled goals.
  int goal_sequence_{0};
};
