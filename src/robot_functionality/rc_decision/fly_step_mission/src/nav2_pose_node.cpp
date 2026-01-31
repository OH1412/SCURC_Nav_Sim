#include "fly_step_mission/nav2_pose_node.hpp"

using namespace std::chrono_literals;

Nav2PoseNode::Nav2PoseNode(const std::string & name,
                           const BT::NodeConfiguration & config,
                           std::shared_ptr<rclcpp::Node> node)
: BT::StatefulActionNode(name, config),
  node_(std::move(node))
{
  client_ = rclcpp_action::create_client<NavigateToPose>(
    node_, "navigate_to_pose");
}

BT::PortsList Nav2PoseNode::providedPorts()
{
  return {
    BT::InputPort<std::string>("frame_id"),
    BT::InputPort<double>("x"),
    BT::InputPort<double>("y"),
    BT::InputPort<double>("yaw")
  };
}

bool Nav2PoseNode::ensureClient()
{
  if (!client_) {
    return false;
  }

  if (!client_->action_server_is_ready()) {
    RCLCPP_INFO(node_->get_logger(),
      "Nav2PoseNode: waiting for action server (up to 60s)...");
    if (!client_->wait_for_action_server(60s)) {
      RCLCPP_ERROR(node_->get_logger(),
        "Nav2PoseNode: navigate_to_pose action server not available after 60s");
      return false;
    }
    RCLCPP_INFO(node_->get_logger(),
      "Nav2PoseNode: action server is ready!");
  }
  return true;
}

geometry_msgs::msg::PoseStamped Nav2PoseNode::makePose(
  const std::string & frame_id, double x, double y, double yaw)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = frame_id;
  pose.header.stamp    = node_->now();

  pose.pose.position.x = x;
  pose.pose.position.y = y;
  pose.pose.position.z = 0.0;

  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, yaw);
  pose.pose.orientation = tf2::toMsg(q);

  return pose;
}

BT::NodeStatus Nav2PoseNode::onStart()
{
  if (!ensureClient()) {
    return BT::NodeStatus::FAILURE;
  }

  std::string frame_id;
  double x, y, yaw;

  if (!getInput("frame_id", frame_id) ||
      !getInput("x", x) ||
      !getInput("y", y) ||
      !getInput("yaw", yaw))
  {
    RCLCPP_ERROR(node_->get_logger(),
      "Nav2PoseNode: missing input ports");
    return BT::NodeStatus::FAILURE;
  }

  auto pose = makePose(frame_id, x, y, yaw);

  NavigateToPose::Goal goal;
  goal.pose = pose;

  goal_sent_    = false;
  result_ready_ = false;

  auto send_goal_options =
    rclcpp_action::Client<NavigateToPose>::SendGoalOptions{};

  send_goal_options.result_callback =
    [this](const GoalHandle::WrappedResult & result)
    {
      result_       = result;
      result_ready_ = true;
    };

  RCLCPP_INFO(node_->get_logger(),
    "Nav2PoseNode: sending goal (%.2f, %.2f, yaw=%.2f)",
    x, y, yaw);

  auto future_goal_handle =
    client_->async_send_goal(goal, send_goal_options);

  if (rclcpp::spin_until_future_complete(node_, future_goal_handle, 5s)
      != rclcpp::FutureReturnCode::SUCCESS)
  {
    RCLCPP_ERROR(node_->get_logger(),
      "Nav2PoseNode: failed to send goal");
    return BT::NodeStatus::FAILURE;
  }

  goal_handle_ = future_goal_handle.get();
  if (!goal_handle_) {
    RCLCPP_ERROR(node_->get_logger(),
      "Nav2PoseNode: goal rejected");
    return BT::NodeStatus::FAILURE;
  }

  goal_sent_ = true;
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus Nav2PoseNode::onRunning()
{
  if (!goal_sent_) {
    return BT::NodeStatus::FAILURE;
  }

  if (!result_ready_) {
    rclcpp::spin_some(node_);
    return BT::NodeStatus::RUNNING;
  }

  switch (result_.code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      RCLCPP_INFO(node_->get_logger(),
        "Nav2PoseNode: goal succeeded");
      return BT::NodeStatus::SUCCESS;

    case rclcpp_action::ResultCode::ABORTED:
      RCLCPP_WARN(node_->get_logger(),
        "Nav2PoseNode: goal aborted");
      return BT::NodeStatus::FAILURE;

    case rclcpp_action::ResultCode::CANCELED:
      RCLCPP_WARN(node_->get_logger(),
        "Nav2PoseNode: goal canceled");
      return BT::NodeStatus::FAILURE;

    default:
      RCLCPP_ERROR(node_->get_logger(),
        "Nav2PoseNode: unknown result code");
      return BT::NodeStatus::FAILURE;
  }
}

void Nav2PoseNode::onHalted()
{
  if (goal_handle_) {
    RCLCPP_WARN(node_->get_logger(),
      "Nav2PoseNode: halted, cancel goal");
    client_->async_cancel_goal(goal_handle_);
  }
  goal_sent_    = false;
  result_ready_ = false;
}