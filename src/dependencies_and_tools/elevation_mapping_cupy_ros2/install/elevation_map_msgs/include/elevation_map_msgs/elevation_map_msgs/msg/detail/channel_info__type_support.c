// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from elevation_map_msgs:msg/ChannelInfo.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "elevation_map_msgs/msg/detail/channel_info__rosidl_typesupport_introspection_c.h"
#include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "elevation_map_msgs/msg/detail/channel_info__functions.h"
#include "elevation_map_msgs/msg/detail/channel_info__struct.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/header.h"
// Member `header`
#include "std_msgs/msg/detail/header__rosidl_typesupport_introspection_c.h"
// Member `channels`
#include "rosidl_runtime_c/string_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  elevation_map_msgs__msg__ChannelInfo__init(message_memory);
}

void elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_fini_function(void * message_memory)
{
  elevation_map_msgs__msg__ChannelInfo__fini(message_memory);
}

size_t elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__size_function__ChannelInfo__channels(
  const void * untyped_member)
{
  const rosidl_runtime_c__String__Sequence * member =
    (const rosidl_runtime_c__String__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_const_function__ChannelInfo__channels(
  const void * untyped_member, size_t index)
{
  const rosidl_runtime_c__String__Sequence * member =
    (const rosidl_runtime_c__String__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_function__ChannelInfo__channels(
  void * untyped_member, size_t index)
{
  rosidl_runtime_c__String__Sequence * member =
    (rosidl_runtime_c__String__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__fetch_function__ChannelInfo__channels(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const rosidl_runtime_c__String * item =
    ((const rosidl_runtime_c__String *)
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_const_function__ChannelInfo__channels(untyped_member, index));
  rosidl_runtime_c__String * value =
    (rosidl_runtime_c__String *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__assign_function__ChannelInfo__channels(
  void * untyped_member, size_t index, const void * untyped_value)
{
  rosidl_runtime_c__String * item =
    ((rosidl_runtime_c__String *)
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_function__ChannelInfo__channels(untyped_member, index));
  const rosidl_runtime_c__String * value =
    (const rosidl_runtime_c__String *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__resize_function__ChannelInfo__channels(
  void * untyped_member, size_t size)
{
  rosidl_runtime_c__String__Sequence * member =
    (rosidl_runtime_c__String__Sequence *)(untyped_member);
  rosidl_runtime_c__String__Sequence__fini(member);
  return rosidl_runtime_c__String__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_member_array[2] = {
  {
    "header",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__msg__ChannelInfo, header),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "channels",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__msg__ChannelInfo, channels),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__size_function__ChannelInfo__channels,  // size() function pointer
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_const_function__ChannelInfo__channels,  // get_const(index) function pointer
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__get_function__ChannelInfo__channels,  // get(index) function pointer
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__fetch_function__ChannelInfo__channels,  // fetch(index, &value) function pointer
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__assign_function__ChannelInfo__channels,  // assign(index, value) function pointer
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__resize_function__ChannelInfo__channels  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_members = {
  "elevation_map_msgs__msg",  // message namespace
  "ChannelInfo",  // message name
  2,  // number of fields
  sizeof(elevation_map_msgs__msg__ChannelInfo),
  elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_member_array,  // message members
  elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_init_function,  // function to initialize message memory (memory has to be allocated)
  elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_type_support_handle = {
  0,
  &elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, msg, ChannelInfo)() {
  elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, std_msgs, msg, Header)();
  if (!elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &elevation_map_msgs__msg__ChannelInfo__rosidl_typesupport_introspection_c__ChannelInfo_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
