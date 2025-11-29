// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from elevation_map_msgs:srv/CheckSafety.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__STRUCT_H_
#define ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'polygons'
#include "geometry_msgs/msg/detail/polygon_stamped__struct.h"

/// Struct defined in srv/CheckSafety in the package elevation_map_msgs.
typedef struct elevation_map_msgs__srv__CheckSafety_Request
{
  geometry_msgs__msg__PolygonStamped__Sequence polygons;
  bool compute_untraversable_polygon;
} elevation_map_msgs__srv__CheckSafety_Request;

// Struct for a sequence of elevation_map_msgs__srv__CheckSafety_Request.
typedef struct elevation_map_msgs__srv__CheckSafety_Request__Sequence
{
  elevation_map_msgs__srv__CheckSafety_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} elevation_map_msgs__srv__CheckSafety_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'is_safe'
// Member 'traversability'
#include "rosidl_runtime_c/primitives_sequence.h"
// Member 'untraversable_polygons'
// already included above
// #include "geometry_msgs/msg/detail/polygon_stamped__struct.h"

/// Struct defined in srv/CheckSafety in the package elevation_map_msgs.
typedef struct elevation_map_msgs__srv__CheckSafety_Response
{
  rosidl_runtime_c__boolean__Sequence is_safe;
  /// Estimate of the traversability of the path.
  /// Ranges from 0 to 1 where 0 means not traversable and 1 highly traversable.
  rosidl_runtime_c__double__Sequence traversability;
  /// Polygons that are untraversable.
  geometry_msgs__msg__PolygonStamped__Sequence untraversable_polygons;
} elevation_map_msgs__srv__CheckSafety_Response;

// Struct for a sequence of elevation_map_msgs__srv__CheckSafety_Response.
typedef struct elevation_map_msgs__srv__CheckSafety_Response__Sequence
{
  elevation_map_msgs__srv__CheckSafety_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} elevation_map_msgs__srv__CheckSafety_Response__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__STRUCT_H_
