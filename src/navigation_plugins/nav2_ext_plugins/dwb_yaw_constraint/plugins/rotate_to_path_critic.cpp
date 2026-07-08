/*
 * RotateToPath — DWB critic that penalizes trajectories whose heading deviates
 * from the path tangent direction.
 */

#include "dwb_yaw_constraint/rotate_to_path_critic.hpp"

#include <cmath>
#include <limits>
#include "angles/angles.h"
#include "dwb_core/exceptions.hpp"
#include "dwb_core/trajectory_utils.hpp"
#include "nav2_util/node_utils.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace dwb_yaw_constraint
{

namespace
{

inline double dist_sq(double x1, double y1, double x2, double y2)
{
  double dx = x1 - x2;
  double dy = y1 - y2;
  return dx * dx + dy * dy;
}

}  // namespace

void RotateToPathCritic::onInit()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("RotateToPathCritic: Failed to lock lifecycle node");
  }

  const std::string prefix = dwb_plugin_name_ + ".";
  const std::string ns = prefix + name_ + ".";

  nav2_util::declare_parameter_if_not_declared(
    node, ns + "path_lookahead_dist", rclcpp::ParameterValue(0.5));
  nav2_util::declare_parameter_if_not_declared(
    node, ns + "lookahead_time", rclcpp::ParameterValue(-1.0));
  nav2_util::declare_parameter_if_not_declared(
    node, ns + "yaw_error_threshold", rclcpp::ParameterValue(0.087));

  node->get_parameter(ns + "path_lookahead_dist", path_lookahead_dist_);
  node->get_parameter(ns + "lookahead_time", lookahead_time_);
  node->get_parameter(ns + "yaw_error_threshold", yaw_error_threshold_);

  // scale_ is inherited from dwb_core::TrajectoryCritic — declared by DWB
  // from the "critic_name.scale" parameter. We just read it for logging.
  RCLCPP_INFO(
    node->get_logger(),
    "RotateToPath [%s] scale=%.1f, path_lookahead=%.2f m, lookahead_time=%.2f s, "
    "yaw_error_threshold=%.2f rad",
    name_.c_str(), scale_, path_lookahead_dist_, lookahead_time_, yaw_error_threshold_);

  tangent_valid_ = false;
  target_yaw_ = 0.0;
}

bool RotateToPathCritic::prepare(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Twist2D & /*vel*/,
  const geometry_msgs::msg::Pose2D & /*goal*/,
  const nav_2d_msgs::msg::Path2D & global_plan)
{
  tangent_valid_ = false;

  if (global_plan.poses.empty()) {
    return true;
  }

  target_yaw_ = computeTangentYaw(pose, global_plan);
  tangent_valid_ = true;
  return true;
}

double RotateToPathCritic::computeTangentYaw(
  const geometry_msgs::msg::Pose2D & pose,
  const nav_2d_msgs::msg::Path2D & global_plan)
{
  const auto & pts = global_plan.poses;

  // 1. Find the closest point on the path to the robot
  size_t closest_idx = 0;
  double best_d2 = std::numeric_limits<double>::max();
  for (size_t i = 0; i < pts.size(); ++i) {
    double d2 = dist_sq(pose.x, pose.y, pts[i].x, pts[i].y);
    if (d2 < best_d2) {
      best_d2 = d2;
      closest_idx = i;
    }
  }

  // 2. Walk forward along the path by path_lookahead_dist_ to get tangent
  double accumulated_dist = 0.0;
  size_t lookahead_idx = closest_idx;

  for (size_t i = closest_idx; i + 1 < pts.size(); ++i) {
    double seg_len = std::sqrt(dist_sq(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y));
    if (accumulated_dist + seg_len >= path_lookahead_dist_) {
      // Interpolate within this segment
      double remaining = path_lookahead_dist_ - accumulated_dist;
      double t = (seg_len > 1e-9) ? (remaining / seg_len) : 0.0;
      double lx = pts[i].x + t * (pts[i + 1].x - pts[i].x);
      double ly = pts[i].y + t * (pts[i + 1].y - pts[i].y);
      return std::atan2(ly - pts[closest_idx].y, lx - pts[closest_idx].x);
    }
    accumulated_dist += seg_len;
    lookahead_idx = i + 1;
  }

  // 3. Fallback: path is too short or we're near the end
  //    Use the direction from closest point toward the next point (or last segment)
  if (closest_idx + 1 < pts.size()) {
    // Forward tangent: closest → next
    double dx = pts[closest_idx + 1].x - pts[closest_idx].x;
    double dy = pts[closest_idx + 1].y - pts[closest_idx].y;
    double len = std::sqrt(dx * dx + dy * dy);
    if (len > 1e-9) {
      return std::atan2(dy, dx);
    }
  } else if (closest_idx > 0) {
    // At the last point, use the direction from previous → last
    double dx = pts[closest_idx].x - pts[closest_idx - 1].x;
    double dy = pts[closest_idx].y - pts[closest_idx - 1].y;
    double len = std::sqrt(dx * dx + dy * dy);
    if (len > 1e-9) {
      return std::atan2(dy, dx);
    }
  }

  // 4. Last resort: use the goal's theta if set, or just the current pose heading
  if (pts.size() == 1) {
    return pts[0].theta;  // single-point path, use its heading
  }
  return pose.theta;  // can't determine tangent, keep current heading
}

double RotateToPathCritic::scoreTrajectory(const dwb_msgs::msg::Trajectory2D & traj)
{
  if (!tangent_valid_ || traj.poses.empty()) {
    return 0.0;
  }

  // Determine which yaw to evaluate
  double eval_yaw;
  if (lookahead_time_ >= 0.0) {
    const geometry_msgs::msg::Pose2D eval_pose =
      dwb_core::projectPose(traj, lookahead_time_);
    eval_yaw = eval_pose.theta;
  } else {
    eval_yaw = traj.poses.back().theta;
  }

  double yaw_error = angles::shortest_angular_distance(eval_yaw, target_yaw_);

  // Hard constraint: when yaw is far off the path direction, reject any
  // trajectory with significant linear velocity.  This forces the robot
  // to rotate toward the path tangent BEFORE translating, preventing
  // crab-walking (lateral drift while facing the wrong way).
  // Only active when scale > 0 (i.e., edge zone — disabled in middle zone).
  if (scale_ > 0.0 && std::fabs(yaw_error) > yaw_error_threshold_) {
    double linear_speed = std::hypot(traj.velocity.x, traj.velocity.y);
    if (linear_speed > 0.05) {
      throw dwb_core::IllegalTrajectoryException(
        name_, "Must rotate to path direction before translating.");
    }
  }

  return scale_ * std::fabs(yaw_error);
}

}  // namespace dwb_yaw_constraint

PLUGINLIB_EXPORT_CLASS(
  dwb_yaw_constraint::RotateToPathCritic,
  dwb_core::TrajectoryCritic)
