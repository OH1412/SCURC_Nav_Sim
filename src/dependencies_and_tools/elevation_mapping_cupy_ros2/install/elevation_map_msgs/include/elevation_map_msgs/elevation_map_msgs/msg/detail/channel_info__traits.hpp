// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from elevation_map_msgs:msg/ChannelInfo.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__TRAITS_HPP_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "elevation_map_msgs/msg/detail/channel_info__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"

namespace elevation_map_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const ChannelInfo & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: channels
  {
    if (msg.channels.size() == 0) {
      out << "channels: []";
    } else {
      out << "channels: [";
      size_t pending_items = msg.channels.size();
      for (auto item : msg.channels) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const ChannelInfo & msg,
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

  // member: channels
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.channels.size() == 0) {
      out << "channels: []\n";
    } else {
      out << "channels:\n";
      for (auto item : msg.channels) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const ChannelInfo & msg, bool use_flow_style = false)
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
  const elevation_map_msgs::msg::ChannelInfo & msg,
  std::ostream & out, size_t indentation = 0)
{
  elevation_map_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use elevation_map_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const elevation_map_msgs::msg::ChannelInfo & msg)
{
  return elevation_map_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<elevation_map_msgs::msg::ChannelInfo>()
{
  return "elevation_map_msgs::msg::ChannelInfo";
}

template<>
inline const char * name<elevation_map_msgs::msg::ChannelInfo>()
{
  return "elevation_map_msgs/msg/ChannelInfo";
}

template<>
struct has_fixed_size<elevation_map_msgs::msg::ChannelInfo>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<elevation_map_msgs::msg::ChannelInfo>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<elevation_map_msgs::msg::ChannelInfo>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__TRAITS_HPP_
