/*
 * Register a dynamic-parameter callback so DWB critic scale updates at runtime.
 * Without this, set_parameters on controller_server only updates the param store;
 * TrajectoryCritic::scale_ stays at the value read in initialize().
 */

#ifndef DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_
#define DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_

#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "nav2_util/lifecycle_node.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "rclcpp/rclcpp.hpp"

namespace dwb_yaw_constraint
{

inline void registerScaleDynamicCallback(
  const nav2_util::LifecycleNode::SharedPtr & node,
  const std::string & scale_param_name,
  const std::function<void(double)> & set_scale,
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr & handle)
{
  handle = node->add_on_set_parameters_callback(
    [scale_param_name, set_scale](const std::vector<rclcpp::Parameter> & parameters) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;
      for (const auto & param : parameters) {
        if (param.get_name() == scale_param_name &&
          param.get_type() == rclcpp::ParameterType::PARAMETER_DOUBLE)
        {
          set_scale(param.as_double());
        }
      }
      return result;
    });
}

}  // namespace dwb_yaw_constraint

#endif  // DWB_YAW_CONSTRAINT__CRITIC_DYNAMIC_SCALE_HPP_
