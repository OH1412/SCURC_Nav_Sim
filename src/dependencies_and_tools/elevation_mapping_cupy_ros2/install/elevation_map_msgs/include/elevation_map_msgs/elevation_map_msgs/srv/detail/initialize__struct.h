// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from elevation_map_msgs:srv/Initialize.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__STRUCT_H_
#define ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Constant 'POINTS'.
enum
{
  elevation_map_msgs__srv__Initialize_Request__POINTS = 0
};

/// Constant 'NEAREST'.
enum
{
  elevation_map_msgs__srv__Initialize_Request__NEAREST = 0
};

/// Constant 'LINEAR'.
enum
{
  elevation_map_msgs__srv__Initialize_Request__LINEAR = 1
};

/// Constant 'CUBIC'.
enum
{
  elevation_map_msgs__srv__Initialize_Request__CUBIC = 2
};

// Include directives for member types
// Member 'points'
#include "geometry_msgs/msg/detail/point_stamped__struct.h"

/// Struct defined in srv/Initialize in the package elevation_map_msgs.
typedef struct elevation_map_msgs__srv__Initialize_Request
{
  uint8_t type;
  uint8_t method;
  geometry_msgs__msg__PointStamped__Sequence points;
} elevation_map_msgs__srv__Initialize_Request;

// Struct for a sequence of elevation_map_msgs__srv__Initialize_Request.
typedef struct elevation_map_msgs__srv__Initialize_Request__Sequence
{
  elevation_map_msgs__srv__Initialize_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} elevation_map_msgs__srv__Initialize_Request__Sequence;


// Constants defined in the message

/// Struct defined in srv/Initialize in the package elevation_map_msgs.
typedef struct elevation_map_msgs__srv__Initialize_Response
{
  bool success;
} elevation_map_msgs__srv__Initialize_Response;

// Struct for a sequence of elevation_map_msgs__srv__Initialize_Response.
typedef struct elevation_map_msgs__srv__Initialize_Response__Sequence
{
  elevation_map_msgs__srv__Initialize_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} elevation_map_msgs__srv__Initialize_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ELEVATION_MAP_MSGS__SRV__DETAIL__INITIALIZE__STRUCT_H_
