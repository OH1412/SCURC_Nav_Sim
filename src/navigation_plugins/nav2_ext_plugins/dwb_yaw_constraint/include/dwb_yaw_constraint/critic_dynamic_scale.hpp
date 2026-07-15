/*
 * Register a dynamic-parameter callback so DWB critic scale updates at runtime.
 * Without this, set_parameters on controller_server only updates the param store;
 * TrajectoryCritic::scale_ stays at the value read in initialize().
 */

#ifndef DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_
#define DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_

#include <cmath>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "nav2_util/lifecycle_node.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "rclcpp/rclcpp.hpp"

namespace dwb_yaw_constraint
{

/// Match relative param name against whatever format rclcpp delivers.
inline bool matchParamName(const std::string & pname, const std::string & relative)
{
  if (pname.empty() || relative.empty()) {
    return false;
  }
  if (pname == relative) {
    return true;
  }
  // FQN: "/ns/node/FollowPath....scale"
  const std::string slash_suffix = "/" + relative;
  if (pname.size() >= slash_suffix.size() &&
    pname.compare(pname.size() - slash_suffix.size(), slash_suffix.size(), slash_suffix) == 0)
  {
    return true;
  }
  // Last resort: relative path appears anywhere in the delivered name
  return pname.find(relative) != std::string::npos;
}

/// Pull critic scale from the parameter store into memory.
/// Prefer calling from prepare() — on_set_parameters callbacks are often not
/// delivered to TrajectoryCritic plugins under controller_server.
inline bool syncScaleFromParamStore(
  const nav2_util::LifecycleNode::SharedPtr & node,
  const std::string & scale_param_name,
  double current_scale,
  const std::function<void(double)> & set_scale,
  const char * /*critic_tag*/)
{
  if (!node) {
    return false;
  }
  double store_scale = current_scale;
  if (!node->get_parameter(scale_param_name, store_scale)) {
    return false;
  }
  if (std::fabs(store_scale - current_scale) > 1e-9) {
    // Diagnostic (disabled — prepare() runs every cycle):
    // RCLCPP_INFO(node->get_logger(),
    //   "CRITIC_SCALE_SYNC %s %s: mem=%.3f -> store=%.3f",
    //   critic_tag, scale_param_name.c_str(), current_scale, store_scale);
    set_scale(store_scale);
    return true;
  }
  return false;
}

inline void registerScaleDynamicCallback(
  const nav2_util::LifecycleNode::SharedPtr & node,
  const std::string & scale_param_name,
  const std::function<void(double)> & set_scale,
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr & handle)
{
  // RCLCPP_INFO(node->get_logger(),
  //   "CRITIC_SCALE_CB_REGISTERED watching='%s'", scale_param_name.c_str());
  handle = node->add_on_set_parameters_callback(
    [scale_param_name, set_scale](const std::vector<rclcpp::Parameter> & parameters) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      for (const auto & param : parameters) {
        if (param.get_type() != rclcpp::ParameterType::PARAMETER_DOUBLE) {
          continue;
        }
        if (matchParamName(param.get_name(), scale_param_name)) {
          set_scale(param.as_double());
          // RCLCPP_INFO(..., "CRITIC_SCALE_MEM_UPDATED ...");
        }
      }
      return result;
    });
}

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_
