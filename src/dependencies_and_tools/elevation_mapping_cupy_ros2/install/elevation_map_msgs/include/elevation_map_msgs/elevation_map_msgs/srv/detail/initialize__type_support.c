// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from elevation_map_msgs:srv/Initialize.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "elevation_map_msgs/srv/detail/initialize__rosidl_typesupport_introspection_c.h"
#include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "elevation_map_msgs/srv/detail/initialize__functions.h"
#include "elevation_map_msgs/srv/detail/initialize__struct.h"


// Include directives for member types
// Member `points`
#include "geometry_msgs/msg/point_stamped.h"
// Member `points`
#include "geometry_msgs/msg/detail/point_stamped__rosidl_typesupport_introspection_c.h"

#ifdef __cplusplus
extern "C"
{
#endif

void elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  elevation_map_msgs__srv__Initialize_Request__init(message_memory);
}

void elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_fini_function(void * message_memory)
{
  elevation_map_msgs__srv__Initialize_Request__fini(message_memory);
}

size_t elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__size_function__Initialize_Request__points(
  const void * untyped_member)
{
  const geometry_msgs__msg__PointStamped__Sequence * member =
    (const geometry_msgs__msg__PointStamped__Sequence *)(untyped_member);
  return member->size;
}

const void * elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_const_function__Initialize_Request__points(
  const void * untyped_member, size_t index)
{
  const geometry_msgs__msg__PointStamped__Sequence * member =
    (const geometry_msgs__msg__PointStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void * elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_function__Initialize_Request__points(
  void * untyped_member, size_t index)
{
  geometry_msgs__msg__PointStamped__Sequence * member =
    (geometry_msgs__msg__PointStamped__Sequence *)(untyped_member);
  return &member->data[index];
}

void elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__fetch_function__Initialize_Request__points(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const geometry_msgs__msg__PointStamped * item =
    ((const geometry_msgs__msg__PointStamped *)
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_const_function__Initialize_Request__points(untyped_member, index));
  geometry_msgs__msg__PointStamped * value =
    (geometry_msgs__msg__PointStamped *)(untyped_value);
  *value = *item;
}

void elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__assign_function__Initialize_Request__points(
  void * untyped_member, size_t index, const void * untyped_value)
{
  geometry_msgs__msg__PointStamped * item =
    ((geometry_msgs__msg__PointStamped *)
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_function__Initialize_Request__points(untyped_member, index));
  const geometry_msgs__msg__PointStamped * value =
    (const geometry_msgs__msg__PointStamped *)(untyped_value);
  *item = *value;
}

bool elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__resize_function__Initialize_Request__points(
  void * untyped_member, size_t size)
{
  geometry_msgs__msg__PointStamped__Sequence * member =
    (geometry_msgs__msg__PointStamped__Sequence *)(untyped_member);
  geometry_msgs__msg__PointStamped__Sequence__fini(member);
  return geometry_msgs__msg__PointStamped__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_member_array[3] = {
  {
    "type",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_UINT8,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__Initialize_Request, type),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "method",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_UINT8,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__Initialize_Request, method),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "points",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_MESSAGE,  // type
    0,  // upper bound of string
    NULL,  // members of sub message (initialized later)
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__Initialize_Request, points),  // bytes offset in struct
    NULL,  // default value
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__size_function__Initialize_Request__points,  // size() function pointer
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_const_function__Initialize_Request__points,  // get_const(index) function pointer
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__get_function__Initialize_Request__points,  // get(index) function pointer
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__fetch_function__Initialize_Request__points,  // fetch(index, &value) function pointer
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__assign_function__Initialize_Request__points,  // assign(index, value) function pointer
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__resize_function__Initialize_Request__points  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_members = {
  "elevation_map_msgs__srv",  // message namespace
  "Initialize_Request",  // message name
  3,  // number of fields
  sizeof(elevation_map_msgs__srv__Initialize_Request),
  elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_member_array,  // message members
  elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_init_function,  // function to initialize message memory (memory has to be allocated)
  elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_type_support_handle = {
  0,
  &elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Request)() {
  elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_member_array[2].members_ =
    ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, geometry_msgs, msg, PointStamped)();
  if (!elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &elevation_map_msgs__srv__Initialize_Request__rosidl_typesupport_introspection_c__Initialize_Request_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

// already included above
// #include <stddef.h>
// already included above
// #include "elevation_map_msgs/srv/detail/initialize__rosidl_typesupport_introspection_c.h"
// already included above
// #include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "rosidl_typesupport_introspection_c/field_types.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
// already included above
// #include "rosidl_typesupport_introspection_c/message_introspection.h"
// already included above
// #include "elevation_map_msgs/srv/detail/initialize__functions.h"
// already included above
// #include "elevation_map_msgs/srv/detail/initialize__struct.h"


#ifdef __cplusplus
extern "C"
{
#endif

void elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  elevation_map_msgs__srv__Initialize_Response__init(message_memory);
}

void elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_fini_function(void * message_memory)
{
  elevation_map_msgs__srv__Initialize_Response__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_member_array[1] = {
  {
    "success",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_BOOLEAN,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(elevation_map_msgs__srv__Initialize_Response, success),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_members = {
  "elevation_map_msgs__srv",  // message namespace
  "Initialize_Response",  // message name
  1,  // number of fields
  sizeof(elevation_map_msgs__srv__Initialize_Response),
  elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_member_array,  // message members
  elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_init_function,  // function to initialize message memory (memory has to be allocated)
  elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_type_support_handle = {
  0,
  &elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Response)() {
  if (!elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &elevation_map_msgs__srv__Initialize_Response__rosidl_typesupport_introspection_c__Initialize_Response_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif

#include "rosidl_runtime_c/service_type_support_struct.h"
// already included above
// #include "elevation_map_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
// already included above
// #include "elevation_map_msgs/srv/detail/initialize__rosidl_typesupport_introspection_c.h"
// already included above
// #include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/service_introspection.h"

// this is intentionally not const to allow initialization later to prevent an initialization race
static rosidl_typesupport_introspection_c__ServiceMembers elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_members = {
  "elevation_map_msgs__srv",  // service namespace
  "Initialize",  // service name
  // these two fields are initialized below on the first access
  NULL,  // request message
  // elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_Request_message_type_support_handle,
  NULL  // response message
  // elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_Response_message_type_support_handle
};

static rosidl_service_type_support_t elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_type_support_handle = {
  0,
  &elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_members,
  get_service_typesupport_handle_function,
};

// Forward declaration of request/response type support functions
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Request)();

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Response)();

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_elevation_map_msgs
const rosidl_service_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__SERVICE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize)() {
  if (!elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_type_support_handle.typesupport_identifier) {
    elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  rosidl_typesupport_introspection_c__ServiceMembers * service_members =
    (rosidl_typesupport_introspection_c__ServiceMembers *)elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_type_support_handle.data;

  if (!service_members->request_members_) {
    service_members->request_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Request)()->data;
  }
  if (!service_members->response_members_) {
    service_members->response_members_ =
      (const rosidl_typesupport_introspection_c__MessageMembers *)
      ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, elevation_map_msgs, srv, Initialize_Response)()->data;
  }

  return &elevation_map_msgs__srv__detail__initialize__rosidl_typesupport_introspection_c__Initialize_service_type_support_handle;
}
