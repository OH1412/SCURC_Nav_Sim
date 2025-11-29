// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from elevation_map_msgs:msg/Statistics.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__STRUCT_H_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"

/// Struct defined in msg/Statistics in the package elevation_map_msgs.
typedef struct elevation_map_msgs__msg__Statistics
{
  std_msgs__msg__Header header;
  double pointcloud_process_fps;
} elevation_map_msgs__msg__Statistics;

// Struct for a sequence of elevation_map_msgs__msg__Statistics.
typedef struct elevation_map_msgs__msg__Statistics__Sequence
{
  elevation_map_msgs__msg__Statistics * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} elevation_map_msgs__msg__Statistics__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__STATISTICS__STRUCT_H_
