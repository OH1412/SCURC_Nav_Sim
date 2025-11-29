// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from elevation_map_msgs:srv/CheckSafety.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "elevation_map_msgs/srv/detail/check_safety__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace elevation_map_msgs
{

namespace srv
{

namespace rosidl_typesupport_introspection_cpp
{

void CheckSafety_Request_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) elevation_map_msgs::srv::CheckSafety_Request(_init);
}

void CheckSafety_Request_fini_function(void * message_memory)
{
  auto typed_message = static_cast<elevation_map_msgs::srv::CheckSafety_Request *>(message_memory);
  typed_message->~CheckSafety_Request();
}

size_t size_function__CheckSafety_Request__polygons(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return member->size();
}

const void * get_const_function__CheckSafety_Request__polygons(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return &member[index];
}

void * get_function__CheckSafety_Request__polygons(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return &member[index];
}

void fetch_function__CheckSafety_Request__polygons(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const geometry_msgs::msg::PolygonStamped *>(
    get_const_function__CheckSafety_Request__polygons(untyped_member, index));
  auto & value = *reinterpret_cast<geometry_msgs::msg::PolygonStamped *>(untyped_value);
  value = item;
}

void assign_function__CheckSafety_Request__polygons(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<geometry_msgs::msg::PolygonStamped *>(
    get_function__CheckSafety_Request__polygons(untyped_member, index));
  const auto & value = *reinterpret_cast<const geometry_msgs::msg::PolygonStamped *>(untyped_value);
  item = value;
}

void resize_function__CheckSafety_Request__polygons(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember CheckSafety_Request_message_member_array[2] = {
  {
    "polygons",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<geometry_msgs::msg::PolygonStamped>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs::srv::CheckSafety_Request, polygons),  // bytes offset in struct
    nullptr,  // default value
    size_function__CheckSafety_Request__polygons,  // size() function pointer
    get_const_function__CheckSafety_Request__polygons,  // get_const(index) function pointer
    get_function__CheckSafety_Request__polygons,  // get(index) function pointer
    fetch_function__CheckSafety_Request__polygons,  // fetch(index, &value) function pointer
    assign_function__CheckSafety_Request__polygons,  // assign(index, value) function pointer
    resize_function__CheckSafety_Request__polygons  // resize(index) function pointer
  },
  {
    "compute_untraversable_polygon",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs::srv::CheckSafety_Request, compute_untraversable_polygon),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers CheckSafety_Request_message_members = {
  "elevation_map_msgs::srv",  // message namespace
  "CheckSafety_Request",  // message name
  2,  // number of fields
  sizeof(elevation_map_msgs::srv::CheckSafety_Request),
  CheckSafety_Request_message_member_array,  // message members
  CheckSafety_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  CheckSafety_Request_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t CheckSafety_Request_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &CheckSafety_Request_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace srv

}  // namespace elevation_map_msgs


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<elevation_map_msgs::srv::CheckSafety_Request>()
{
  return &::elevation_map_msgs::srv::rosidl_typesupport_introspection_cpp::CheckSafety_Request_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, elevation_map_msgs, srv, CheckSafety_Request)() {
  return &::elevation_map_msgs::srv::rosidl_typesupport_introspection_cpp::CheckSafety_Request_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

// already included above
// #include "array"
// already included above
// #include "cstddef"
// already included above
// #include "string"
// already included above
// #include "vector"
// already included above
// #include "rosidl_runtime_c/message_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/field_types.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace elevation_map_msgs
{

namespace srv
{

namespace rosidl_typesupport_introspection_cpp
{

void CheckSafety_Response_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) elevation_map_msgs::srv::CheckSafety_Response(_init);
}

void CheckSafety_Response_fini_function(void * message_memory)
{
  auto typed_message = static_cast<elevation_map_msgs::srv::CheckSafety_Response *>(message_memory);
  typed_message->~CheckSafety_Response();
}

size_t size_function__CheckSafety_Response__is_safe(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<bool> *>(untyped_member);
  return member->size();
}

void fetch_function__CheckSafety_Response__is_safe(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & member = *reinterpret_cast<const std::vector<bool> *>(untyped_member);
  auto & value = *reinterpret_cast<bool *>(untyped_value);
  value = member[index];
}

void assign_function__CheckSafety_Response__is_safe(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & member = *reinterpret_cast<std::vector<bool> *>(untyped_member);
  const auto & value = *reinterpret_cast<const bool *>(untyped_value);
  member[index] = value;
}

void resize_function__CheckSafety_Response__is_safe(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<bool> *>(untyped_member);
  member->resize(size);
}

size_t size_function__CheckSafety_Response__traversability(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<double> *>(untyped_member);
  return member->size();
}

const void * get_const_function__CheckSafety_Response__traversability(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<double> *>(untyped_member);
  return &member[index];
}

void * get_function__CheckSafety_Response__traversability(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<double> *>(untyped_member);
  return &member[index];
}

void fetch_function__CheckSafety_Response__traversability(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const double *>(
    get_const_function__CheckSafety_Response__traversability(untyped_member, index));
  auto & value = *reinterpret_cast<double *>(untyped_value);
  value = item;
}

void assign_function__CheckSafety_Response__traversability(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<double *>(
    get_function__CheckSafety_Response__traversability(untyped_member, index));
  const auto & value = *reinterpret_cast<const double *>(untyped_value);
  item = value;
}

void resize_function__CheckSafety_Response__traversability(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<double> *>(untyped_member);
  member->resize(size);
}

size_t size_function__CheckSafety_Response__untraversable_polygons(const void * untyped_member)
{
  const auto * member = reinterpret_cast<const std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return member->size();
}

const void * get_const_function__CheckSafety_Response__untraversable_polygons(const void * untyped_member, size_t index)
{
  const auto & member =
    *reinterpret_cast<const std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return &member[index];
}

void * get_function__CheckSafety_Response__untraversable_polygons(void * untyped_member, size_t index)
{
  auto & member =
    *reinterpret_cast<std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  return &member[index];
}

void fetch_function__CheckSafety_Response__untraversable_polygons(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const auto & item = *reinterpret_cast<const geometry_msgs::msg::PolygonStamped *>(
    get_const_function__CheckSafety_Response__untraversable_polygons(untyped_member, index));
  auto & value = *reinterpret_cast<geometry_msgs::msg::PolygonStamped *>(untyped_value);
  value = item;
}

void assign_function__CheckSafety_Response__untraversable_polygons(
  void * untyped_member, size_t index, const void * untyped_value)
{
  auto & item = *reinterpret_cast<geometry_msgs::msg::PolygonStamped *>(
    get_function__CheckSafety_Response__untraversable_polygons(untyped_member, index));
  const auto & value = *reinterpret_cast<const geometry_msgs::msg::PolygonStamped *>(untyped_value);
  item = value;
}

void resize_function__CheckSafety_Response__untraversable_polygons(void * untyped_member, size_t size)
{
  auto * member =
    reinterpret_cast<std::vector<geometry_msgs::msg::PolygonStamped> *>(untyped_member);
  member->resize(size);
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember CheckSafety_Response_message_member_array[3] = {
  {
    "is_safe",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs::srv::CheckSafety_Response, is_safe),  // bytes offset in struct
    nullptr,  // default value
    size_function__CheckSafety_Response__is_safe,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    fetch_function__CheckSafety_Response__is_safe,  // fetch(index, &value) function pointer
    assign_function__CheckSafety_Response__is_safe,  // assign(index, value) function pointer
    resize_function__CheckSafety_Response__is_safe  // resize(index) function pointer
  },
  {
    "traversability",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs::srv::CheckSafety_Response, traversability),  // bytes offset in struct
    nullptr,  // default value
    size_function__CheckSafety_Response__traversability,  // size() function pointer
    get_const_function__CheckSafety_Response__traversability,  // get_const(index) function pointer
    get_function__CheckSafety_Response__traversability,  // get(index) function pointer
    fetch_function__CheckSafety_Response__traversability,  // fetch(index, &value) function pointer
    assign_function__CheckSafety_Response__traversability,  // assign(index, value) function pointer
    resize_function__CheckSafety_Response__traversability  // resize(index) function pointer
  },
  {
    "untraversable_polygons",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<geometry_msgs::msg::PolygonStamped>(),  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs::srv::CheckSafety_Response, untraversable_polygons),  // bytes offset in struct
    nullptr,  // default value
    size_function__CheckSafety_Response__untraversable_polygons,  // size() function pointer
    get_const_function__CheckSafety_Response__untraversable_polygons,  // get_const(index) function pointer
    get_function__CheckSafety_Response__untraversable_polygons,  // get(index) function pointer
    fetch_function__CheckSafety_Response__untraversable_polygons,  // fetch(index, &value) function pointer
    assign_function__CheckSafety_Response__untraversable_polygons,  // assign(index, value) function pointer
    resize_function__CheckSafety_Response__untraversable_polygons  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers CheckSafety_Response_message_members = {
  "elevation_map_msgs::srv",  // message namespace
  "CheckSafety_Response",  // message name
  3,  // number of fields
  sizeof(elevation_map_msgs::srv::CheckSafety_Response),
  CheckSafety_Response_message_member_array,  // message members
  CheckSafety_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  CheckSafety_Response_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t CheckSafety_Response_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &CheckSafety_Response_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace srv

}  // namespace elevation_map_msgs


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<elevation_map_msgs::srv::CheckSafety_Response>()
{
  return &::elevation_map_msgs::srv::rosidl_typesupport_introspection_cpp::CheckSafety_Response_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, elevation_map_msgs, srv, CheckSafety_Response)() {
  return &::elevation_map_msgs::srv::rosidl_typesupport_introspection_cpp::CheckSafety_Response_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_cpp/service_type_support.hpp"
// already included above
// #include "rosidl_typesupport_interface/macros.h"
// already included above
// #include "rosidl_typesupport_introspection_cpp/visibility_control.h"
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__struct.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/identifier.hpp"
// already included above
// #include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/service_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/service_type_support_decl.hpp"

namespace elevation_map_msgs
{

namespace srv
{

namespace rosidl_typesupport_introspection_cpp
{

// this is intentionally not const to allow initialization later to prevent an initialization race
static ::rosidl_typesupport_introspection_cpp::ServiceMembers CheckSafety_service_members = {
  "elevation_map_msgs::srv",  // service namespace
  "CheckSafety",  // service name
  // these two fields are initialized below on the first access
  // see get_service_type_support_handle<elevation_map_msgs::srv::CheckSafety>()
  nullptr,  // request message
  nullptr  // response message
};

static const rosidl_service_type_support_t CheckSafety_service_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &CheckSafety_service_members,
  get_service_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace srv

}  // namespace elevation_map_msgs


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
get_service_type_support_handle<elevation_map_msgs::srv::CheckSafety>()
{
  // get a handle to the value to be returned
  auto service_type_support =
    &::elevation_map_msgs::srv::rosidl_typesupport_introspection_cpp::CheckSafety_service_type_support_handle;
  // get a non-const and properly typed version of the data void *
  auto service_members = const_cast<::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
    static_cast<const ::rosidl_typesupport_introspection_cpp::ServiceMembers *>(
      service_type_support->data));
  // make sure that both the request_members_ and the response_members_ are initialized
  // if they are not, initialize them
  if (
    service_members->request_members_ == nullptr ||
    service_members->response_members_ == nullptr)
  {
    // initialize the request_members_ with the static function from the external library
    service_members->request_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::elevation_map_msgs::srv::CheckSafety_Request
      >()->data
      );
    // initialize the response_members_ with the static function from the external library
    service_members->response_members_ = static_cast<
      const ::rosidl_typesupport_introspection_cpp::MessageMembers *
      >(
      ::rosidl_typesupport_introspection_cpp::get_message_type_support_handle<
        ::elevation_map_msgs::srv::CheckSafety_Response
      >()->data
      );
  }
  // finally return the properly initialized service_type_support handle
  return service_type_support;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, elevation_map_msgs, srv, CheckSafety)() {
  return ::rosidl_typesupport_introspection_cpp::get_service_type_support_handle<elevation_map_msgs::srv::CheckSafety>();
}

#ifdef __cplusplus
}
#endif
