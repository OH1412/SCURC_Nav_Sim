// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from elevation_map_msgs:msg/Statistics.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__TRAITS_HPP_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "elevation_map_msgs/msg/detail/statistics__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"

namespace elevation_map_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const Statistics & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: pointcloud_process_fps
  {
    out << "pointcloud_process_fps: ";
    rosidl_generator_traits::value_to_yaml(msg.pointcloud_process_fps, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Statistics & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: header
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "header:\n";
    to_block_style_yaml(msg.header, out, indentation + 2);
  }

  // member: pointcloud_process_fps
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pointcloud_process_fps: ";
    rosidl_generator_traits::value_to_yaml(msg.pointcloud_process_fps, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Statistics & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace elevation_map_msgs

namespace rosidl_generator_traits
{

[[deprecated("use elevation_map_msgs::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const elevation_map_msgs::msg::Statistics & msg,
  std::ostream & out, size_t indentation = 0)
{
  elevation_map_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use elevation_map_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const elevation_map_msgs::msg::Statistics & msg)
{
  return elevation_map_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<elevation_map_msgs::msg::Statistics>()
{
  return "elevation_map_msgs::msg::Statistics";
}

template<>
inline const char * name<elevation_map_msgs::msg::Statistics>()
{
  return "elevation_map_msgs/msg/Statistics";
}

template<>
struct has_fixed_size<elevation_map_msgs::msg::Statistics>
  : std::integral_constant<bool, has_fixed_size<std_msgs::msg::Header>::value> {};

template<>
struct has_bounded_size<elevation_map_msgs::msg::Statistics>
  : std::integral_constant<bool, has_bounded_size<std_msgs::msg::Header>::value> {};

template<>
struct is_message<elevation_map_msgs::msg::Statistics>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__TRAITS_HPP_
