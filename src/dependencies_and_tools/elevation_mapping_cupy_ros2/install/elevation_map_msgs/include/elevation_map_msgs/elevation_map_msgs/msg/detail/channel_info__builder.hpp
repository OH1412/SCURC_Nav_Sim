// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from elevation_map_msgs:msg/ChannelInfo.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__BUILDER_HPP_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "elevation_map_msgs/msg/detail/channel_info__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace elevation_map_msgs
{

namespace msg
{

namespace builder
{

class Init_ChannelInfo_channels
{
public:
  explicit Init_ChannelInfo_channels(::elevation_map_msgs::msg::ChannelInfo & msg)
  : msg_(msg)
  {}
  ::elevation_map_msgs::msg::ChannelInfo channels(::elevation_map_msgs::msg::ChannelInfo::_channels_type arg)
  {
    msg_.channels = std::move(arg);
    return std::move(msg_);
  }

private:
  ::elevation_map_msgs::msg::ChannelInfo msg_;
};

class Init_ChannelInfo_header
{
public:
  Init_ChannelInfo_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_ChannelInfo_channels header(::elevation_map_msgs::msg::ChannelInfo::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_ChannelInfo_channels(msg_);
  }

private:
  ::elevation_map_msgs::msg::ChannelInfo msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::elevation_map_msgs::msg::ChannelInfo>()
{
  return elevation_map_msgs::msg::builder::Init_ChannelInfo_header();
}

}  // namespace elevation_map_msgs

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__BUILDER_HPP_
