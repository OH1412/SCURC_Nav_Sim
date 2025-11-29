// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from elevation_map_msgs:srv/Initialize.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__BUILDER_HPP_
#define ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "elevation_map_msgs/srv/detail/initialize__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace elevation_map_msgs
{

namespace srv
{

namespace builder
{

class Init_Initialize_Request_points
{
public:
  explicit Init_Initialize_Request_points(::elevation_map_msgs::srv::Initialize_Request & msg)
  : msg_(msg)
  {}
  ::elevation_map_msgs::srv::Initialize_Request points(::elevation_map_msgs::srv::Initialize_Request::_points_type arg)
  {
    msg_.points = std::move(arg);
    return std::move(msg_);
  }

private:
  ::elevation_map_msgs::srv::Initialize_Request msg_;
};

class Init_Initialize_Request_method
{
public:
  explicit Init_Initialize_Request_method(::elevation_map_msgs::srv::Initialize_Request & msg)
  : msg_(msg)
  {}
  Init_Initialize_Request_points method(::elevation_map_msgs::srv::Initialize_Request::_method_type arg)
  {
    msg_.method = std::move(arg);
    return Init_Initialize_Request_points(msg_);
  }

private:
  ::elevation_map_msgs::srv::Initialize_Request msg_;
};

class Init_Initialize_Request_type
{
public:
  Init_Initialize_Request_type()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Initialize_Request_method type(::elevation_map_msgs::srv::Initialize_Request::_type_type arg)
  {
    msg_.type = std::move(arg);
    return Init_Initialize_Request_method(msg_);
  }

private:
  ::elevation_map_msgs::srv::Initialize_Request msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::elevation_map_msgs::srv::Initialize_Request>()
{
  return elevation_map_msgs::srv::builder::Init_Initialize_Request_type();
}

}  // namespace elevation_map_msgs


namespace elevation_map_msgs
{

namespace srv
{

namespace builder
{

class Init_Initialize_Response_success
{
public:
  Init_Initialize_Response_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::elevation_map_msgs::srv::Initialize_Response success(::elevation_map_msgs::srv::Initialize_Response::_success_type arg)
  {
    msg_.success = std::move(arg);
    return std::move(msg_);
  }

private:
  ::elevation_map_msgs::srv::Initialize_Response msg_;
};

}  // namespace builder

}  // namespace srv

template<typename MessageType>
auto build();

template<>
inline
auto build<::elevation_map_msgs::srv::Initialize_Response>()
{
  return elevation_map_msgs::srv::builder::Init_Initialize_Response_success();
}

}  // namespace elevation_map_msgs

#endif  // ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__BUILDER_HPP_
