// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from nav2_msgs:msg/Route.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "nav2_msgs/msg/detail/route__rosidl_typesupport_introspection_c.h"
#include "nav2_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "nav2_msgs/msg/detail/route__functions.h"
#include "nav2_msgs/msg/detail/route__struct.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/header.h"
// Member `header`
#include "std_msgs/msg/detail/header__rosidl_typesupport_introspection_c.h"
// Member `nodes`
#include "nav2_msgs/msg/route_node.h"
// Member `nodes`
#include "nav2_msgs/msg/detail/route_node__rosidl_typesupport_introspection_c.h"
// Member `edges`
#include "nav2_msgs/msg/route_edge.h"
// Member `edges`
#include "nav2_msgs/msg/detail/route_edge__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  nav2_msgs__msg__Route__init(message_memory);
}

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_fini_function(void * message_memory)
{
  nav2_msgs__msg__Route__fini(message_memory);
}

size_t nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__size_function__Route__nodes(
  const void * untyped_member)
{
  const nav2_msgs__msg__RouteNode__Sequence * member =
    (const nav2_msgs__msg__RouteNode__Sequence *)(untyped_member);
  return member->size;
}

const void * nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__nodes(
  const void * untyped_member, size_t index)
{
  const nav2_msgs__msg__RouteNode__Sequence * member =
    (const nav2_msgs__msg__RouteNode__Sequence *)(untyped_member);
  return &member->data[index];
}

void * nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__nodes(
  void * untyped_member, size_t index)
{
  nav2_msgs__msg__RouteNode__Sequence * member =
    (nav2_msgs__msg__RouteNode__Sequence *)(untyped_member);
  return &member->data[index];
}

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__fetch_function__Route__nodes(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const nav2_msgs__msg__RouteNode * item =
    ((const nav2_msgs__msg__RouteNode *)
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__nodes(untyped_member, index));
  nav2_msgs__msg__RouteNode * value =
    (nav2_msgs__msg__RouteNode *)(untyped_value);
  *value = *item;
}

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__assign_function__Route__nodes(
  void * untyped_member, size_t index, const void * untyped_value)
{
  nav2_msgs__msg__RouteNode * item =
    ((nav2_msgs__msg__RouteNode *)
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__nodes(untyped_member, index));
  const nav2_msgs__msg__RouteNode * value =
    (const nav2_msgs__msg__RouteNode *)(untyped_value);
  *item = *value;
}

bool nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__resize_function__Route__nodes(
  void * untyped_member, size_t size)
{
  nav2_msgs__msg__RouteNode__Sequence * member =
    (nav2_msgs__msg__RouteNode__Sequence *)(untyped_member);
  nav2_msgs__msg__RouteNode__Sequence__fini(member);
  return nav2_msgs__msg__RouteNode__Sequence__init(member, size);
}

size_t nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__size_function__Route__edges(
  const void * untyped_member)
{
  const nav2_msgs__msg__RouteEdge__Sequence * member =
    (const nav2_msgs__msg__RouteEdge__Sequence *)(untyped_member);
  return member->size;
}

const void * nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__edges(
  const void * untyped_member, size_t index)
{
  const nav2_msgs__msg__RouteEdge__Sequence * member =
    (const nav2_msgs__msg__RouteEdge__Sequence *)(untyped_member);
  return &member->data[index];
}

void * nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__edges(
  void * untyped_member, size_t index)
{
  nav2_msgs__msg__RouteEdge__Sequence * member =
    (nav2_msgs__msg__RouteEdge__Sequence *)(untyped_member);
  return &member->data[index];
}

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__fetch_function__Route__edges(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const nav2_msgs__msg__RouteEdge * item =
    ((const nav2_msgs__msg__RouteEdge *)
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__edges(untyped_member, index));
  nav2_msgs__msg__RouteEdge * value =
    (nav2_msgs__msg__RouteEdge *)(untyped_value);
  *value = *item;
}

void nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__assign_function__Route__edges(
  void * untyped_member, size_t index, const void * untyped_value)
{
  nav2_msgs__msg__RouteEdge * item =
    ((nav2_msgs__msg__RouteEdge *)
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__edges(untyped_member, index));
  const nav2_msgs__msg__RouteEdge * value =
    (const nav2_msgs__msg__RouteEdge *)(untyped_value);
  *item = *value;
}

bool nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__resize_function__Route__edges(
  void * untyped_member, size_t size)
{
  nav2_msgs__msg__RouteEdge__Sequence * member =
    (nav2_msgs__msg__RouteEdge__Sequence *)(untyped_member);
  nav2_msgs__msg__RouteEdge__Sequence__fini(member);
  return nav2_msgs__msg__RouteEdge__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_member_array[4] = {
  {
    "header",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(nav2_msgs__msg__Route, header),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "route_cost",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(nav2_msgs__msg__Route, route_cost),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "nodes",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(nav2_msgs__msg__Route, nodes),  // bytes offset in struct
    NULL,  // default value
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__size_function__Route__nodes,  // size() function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__nodes,  // get_const(index) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__nodes,  // get(index) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__fetch_function__Route__nodes,  // fetch(index, &value) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__assign_function__Route__nodes,  // assign(index, value) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__resize_function__Route__nodes  // resize(index) function pointer
  },
  {
    "edges",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(nav2_msgs__msg__Route, edges),  // bytes offset in struct
    NULL,  // default value
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__size_function__Route__edges,  // size() function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_const_function__Route__edges,  // get_const(index) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__get_function__Route__edges,  // get(index) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__fetch_function__Route__edges,  // fetch(index, &value) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__assign_function__Route__edges,  // assign(index, value) function pointer
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__resize_function__Route__edges  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_members = {
  "nav2_msgs__msg",  // message namespace
  "Route",  // message name
  4,  // number of fields
  sizeof(nav2_msgs__msg__Route),
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_member_array,  // message members
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_init_function,  // function to initialize message memory (memory has to be allocated)
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_type_support_handle = {
  0,
  &nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_nav2_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, nav2_msgs, msg, Route)() {
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, std_msgs, msg, Header)();
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_member_array[2].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, nav2_msgs, msg, RouteNode)();
  nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_member_array[3].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, nav2_msgs, msg, RouteEdge)();
  if (!nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_type_support_handle.typesupport_identifier) {
    nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &nav2_msgs__msg__Route__rosidl_typesupport_introspection_c__Route_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
