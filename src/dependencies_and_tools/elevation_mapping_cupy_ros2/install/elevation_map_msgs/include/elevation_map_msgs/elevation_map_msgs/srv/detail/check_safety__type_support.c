// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from elevation_map_msgs:srv/CheckSafety.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "elevation_map_msgs/srv/detail/check_safety__rosidl_typesupport_introspection_c.h"
#include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "elevation_map_msgs/srv/detail/check_safety__functions.h"
#include "elevation_map_msgs/srv/detail/check_safety__struct.h"


// Include directives for member types
// Member `polygons`
#include "geometry_msgs/msg/polygon_stamped.h"
// Member `polygons`
#include "geometry_msgs/msg/detail/polygon_stamped__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  elevation_map_msgs__srv__CheckSafety_Request__init(message_memory);
}

void elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_fini_function(void * message_memory)
{
  elevation_map_msgs__srv__CheckSafety_Request__fini(message_memory);
}

size_t elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__size_function__CheckSafety_Request__polygons(
  const void * untyped_member)
{
  const geometry_msgs__msg__PolygonStamped__Sequence * member =
    (const geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Request__polygons(
  const void * untyped_member, size_t index)
{
  const geometry_msgs__msg__PolygonStamped__Sequence * member =
    (const geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_function__CheckSafety_Request__polygons(
  void * untyped_member, size_t index)
{
  geometry_msgs__msg__PolygonStamped__Sequence * member =
    (geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Request__polygons(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const geometry_msgs__msg__PolygonStamped * item =
    ((const geometry_msgs__msg__PolygonStamped *)
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Request__polygons(untyped_member, index));
  geometry_msgs__msg__PolygonStamped * value =
    (geometry_msgs__msg__PolygonStamped *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Request__polygons(
  void * untyped_member, size_t index, const void * untyped_value)
{
  geometry_msgs__msg__PolygonStamped * item =
    ((geometry_msgs__msg__PolygonStamped *)
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_function__CheckSafety_Request__polygons(untyped_member, index));
  const geometry_msgs__msg__PolygonStamped * value =
    (const geometry_msgs__msg__PolygonStamped *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Request__polygons(
  void * untyped_member, size_t size)
{
  geometry_msgs__msg__PolygonStamped__Sequence * member =
    (geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  geometry_msgs__msg__PolygonStamped__Sequence__fini(member);
  return geometry_msgs__msg__PolygonStamped__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_member_array[2] = {
  {
    "polygons",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__CheckSafety_Request, polygons),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__size_function__CheckSafety_Request__polygons,  // size() function pointer
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Request__polygons,  // get_const(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__get_function__CheckSafety_Request__polygons,  // get(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Request__polygons,  // fetch(index, &value) function pointer
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Request__polygons,  // assign(index, value) function pointer
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Request__polygons  // resize(index) function pointer
  },
  {
    "compute_untraversable_polygon",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__CheckSafety_Request, compute_untraversable_polygon),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_members = {
  "elevation_map_msgs__srv",  // message namespace
  "CheckSafety_Request",  // message name
  2,  // number of fields
  sizeof(elevation_map_msgs__srv__CheckSafety_Request),
  elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_member_array,  // message members
  elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_type_support_handle = {
  0,
  &elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Request)() {
  elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_member_array[0].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, geometry_msgs, msg, PolygonStamped)();
  if (!elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &elevation_map_msgs__srv__CheckSafety_Request__rosidl_typesupport_introspection_c__CheckSafety_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__rosidl_typesupport_introspection_c.h"
// already included above
// #include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__functions.h"
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__struct.h"


// Include directives for member types
// Member `is_safe`
// Member `traversability`
#include "rosidl_runtime_c/primitives_sequence_functions.h"
// Member `untraversable_polygons`
// already included above
// #include "geometry_msgs/msg/polygon_stamped.h"
// Member `untraversable_polygons`
// already included above
// #include "geometry_msgs/msg/detail/polygon_stamped__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  elevation_map_msgs__srv__CheckSafety_Response__init(message_memory);
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_fini_function(void * message_memory)
{
  elevation_map_msgs__srv__CheckSafety_Response__fini(message_memory);
}

size_t elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__is_safe(
  const void * untyped_member)
{
  const rosidl_runtime_c__boolean__Sequence * member =
    (const rosidl_runtime_c__boolean__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__is_safe(
  const void * untyped_member, size_t index)
{
  const rosidl_runtime_c__boolean__Sequence * member =
    (const rosidl_runtime_c__boolean__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__is_safe(
  void * untyped_member, size_t index)
{
  rosidl_runtime_c__boolean__Sequence * member =
    (rosidl_runtime_c__boolean__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__is_safe(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const bool * item =
    ((const bool *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__is_safe(untyped_member, index));
  bool * value =
    (bool *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__is_safe(
  void * untyped_member, size_t index, const void * untyped_value)
{
  bool * item =
    ((bool *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__is_safe(untyped_member, index));
  const bool * value =
    (const bool *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__is_safe(
  void * untyped_member, size_t size)
{
  rosidl_runtime_c__boolean__Sequence * member =
    (rosidl_runtime_c__boolean__Sequence *)(untyped_member);
  rosidl_runtime_c__boolean__Sequence__fini(member);
  return rosidl_runtime_c__boolean__Sequence__init(member, size);
}

size_t elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__traversability(
  const void * untyped_member)
{
  const rosidl_runtime_c__double__Sequence * member =
    (const rosidl_runtime_c__double__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__traversability(
  const void * untyped_member, size_t index)
{
  const rosidl_runtime_c__double__Sequence * member =
    (const rosidl_runtime_c__double__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__traversability(
  void * untyped_member, size_t index)
{
  rosidl_runtime_c__double__Sequence * member =
    (rosidl_runtime_c__double__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__traversability(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const double * item =
    ((const double *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__traversability(untyped_member, index));
  double * value =
    (double *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__traversability(
  void * untyped_member, size_t index, const void * untyped_value)
{
  double * item =
    ((double *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__traversability(untyped_member, index));
  const double * value =
    (const double *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__traversability(
  void * untyped_member, size_t size)
{
  rosidl_runtime_c__double__Sequence * member =
    (rosidl_runtime_c__double__Sequence *)(untyped_member);
  rosidl_runtime_c__double__Sequence__fini(member);
  return rosidl_runtime_c__double__Sequence__init(member, size);
}

size_t elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__untraversable_polygons(
  const void * untyped_member)
{
  const geometry_msgs__msg__PolygonStamped__Sequence * member =
    (const geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__untraversable_polygons(
  const void * untyped_member, size_t index)
{
  const geometry_msgs__msg__PolygonStamped__Sequence * member =
    (const geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__untraversable_polygons(
  void * untyped_member, size_t index)
{
  geometry_msgs__msg__PolygonStamped__Sequence * member =
    (geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__untraversable_polygons(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const geometry_msgs__msg__PolygonStamped * item =
    ((const geometry_msgs__msg__PolygonStamped *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__untraversable_polygons(untyped_member, index));
  geometry_msgs__msg__PolygonStamped * value =
    (geometry_msgs__msg__PolygonStamped *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__untraversable_polygons(
  void * untyped_member, size_t index, const void * untyped_value)
{
  geometry_msgs__msg__PolygonStamped * item =
    ((geometry_msgs__msg__PolygonStamped *)
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__untraversable_polygons(untyped_member, index));
  const geometry_msgs__msg__PolygonStamped * value =
    (const geometry_msgs__msg__PolygonStamped *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__untraversable_polygons(
  void * untyped_member, size_t size)
{
  geometry_msgs__msg__PolygonStamped__Sequence * member =
    (geometry_msgs__msg__PolygonStamped__Sequence *)(untyped_member);
  geometry_msgs__msg__PolygonStamped__Sequence__fini(member);
  return geometry_msgs__msg__PolygonStamped__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_member_array[3] = {
  {
    "is_safe",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__CheckSafety_Response, is_safe),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__is_safe,  // size() function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__is_safe,  // get_const(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__is_safe,  // get(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__is_safe,  // fetch(index, &value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__is_safe,  // assign(index, value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__is_safe  // resize(index) function pointer
  },
  {
    "traversability",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_DOUBLE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__CheckSafety_Response, traversability),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__traversability,  // size() function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__traversability,  // get_const(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__traversability,  // get(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__traversability,  // fetch(index, &value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__traversability,  // assign(index, value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__traversability  // resize(index) function pointer
  },
  {
    "untraversable_polygons",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__CheckSafety_Response, untraversable_polygons),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__size_function__CheckSafety_Response__untraversable_polygons,  // size() function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_const_function__CheckSafety_Response__untraversable_polygons,  // get_const(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__get_function__CheckSafety_Response__untraversable_polygons,  // get(index) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__fetch_function__CheckSafety_Response__untraversable_polygons,  // fetch(index, &value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__assign_function__CheckSafety_Response__untraversable_polygons,  // assign(index, value) function pointer
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__resize_function__CheckSafety_Response__untraversable_polygons  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_members = {
  "elevation_map_msgs__srv",  // message namespace
  "CheckSafety_Response",  // message name
  3,  // number of fields
  sizeof(elevation_map_msgs__srv__CheckSafety_Response),
  elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_member_array,  // message members
  elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_type_support_handle = {
  0,
  &elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Response)() {
  elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_member_array[2].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, geometry_msgs, msg, PolygonStamped)();
  if (!elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &elevation_map_msgs__srv__CheckSafety_Response__rosidl_typesupport_introspection_c__CheckSafety_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "elevation_map_msgs/srv/detail/check_safety__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_members = {
  "elevation_map_msgs__srv",  // service namespace
  "CheckSafety",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_Request_message_type_support_handle,
  NULL  // response message
  // elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_Response_message_type_support_handle
};

static rosidl_service_type_support_t elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_type_support_handle = {
  0,
  &elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety)() {
  if (!elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, CheckSafety_Response)()->data;
  }

  return &elevation_map_msgs__srv__detail__check_safety__rosidl_typesupport_introspection_c__CheckSafety_service_type_support_handle;
}
