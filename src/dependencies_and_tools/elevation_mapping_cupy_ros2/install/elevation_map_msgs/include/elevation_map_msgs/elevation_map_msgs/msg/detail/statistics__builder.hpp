// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from elevation_map_msgs:msg/Statistics.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__BUILDER_HPP_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "elevation_map_msgs/msg/detail/statistics__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace elevation_map_msgs
{

namespace msg
{

namespace builder
{

class Init_Statistics_pointcloud_process_fps
{
public:
  explicit Init_Statistics_pointcloud_process_fps(::elevation_map_msgs::msg::Statistics & msg)
  : msg_(msg)
  {}
  ::elevation_map_msgs::msg::Statistics pointcloud_process_fps(::elevation_map_msgs::msg::Statistics::_pointcloud_process_fps_type arg)
  {
    msg_.pointcloud_process_fps = std::move(arg);
    return std::move(msg_);
  }

private:
  ::elevation_map_msgs::msg::Statistics msg_;
};

class Init_Statistics_header
{
public:
  Init_Statistics_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Statistics_pointcloud_process_fps header(::elevation_map_msgs::msg::Statistics::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_Statistics_pointcloud_process_fps(msg_);
  }

private:
  ::elevation_map_msgs::msg::Statistics msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::elevation_map_msgs::msg::Statistics>()
{
  return elevation_map_msgs::msg::builder::Init_Statistics_header();
}

}  // namespace elevation_map_msgs

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__BUILDER_HPP_
