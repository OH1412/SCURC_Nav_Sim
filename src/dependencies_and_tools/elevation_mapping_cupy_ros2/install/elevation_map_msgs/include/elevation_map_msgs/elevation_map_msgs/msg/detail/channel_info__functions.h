// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from elevation_map_msgs:msg/ChannelInfo.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__FUNCTIONS_H_
#define ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "elevation_map_msgs/msg/rosidl_generator_c__visibility_control.h"

#include "elevation_map_msgs/msg/detail/channel_info__struct.h"

/// Initialize msg/ChannelInfo message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * elevation_map_msgs__msg__ChannelInfo
 * )) before or use
 * elevation_map_msgs__msg__ChannelInfo__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__init(elevation_map_msgs__msg__ChannelInfo * msg);

/// Finalize msg/ChannelInfo message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
void
elevation_map_msgs__msg__ChannelInfo__fini(elevation_map_msgs__msg__ChannelInfo * msg);

/// Create msg/ChannelInfo message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * elevation_map_msgs__msg__ChannelInfo__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
elevation_map_msgs__msg__ChannelInfo *
elevation_map_msgs__msg__ChannelInfo__create();

/// Destroy msg/ChannelInfo message.
/**
 * It calls
 * elevation_map_msgs__msg__ChannelInfo__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
void
elevation_map_msgs__msg__ChannelInfo__destroy(elevation_map_msgs__msg__ChannelInfo * msg);

/// Check for msg/ChannelInfo message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__are_equal(const elevation_map_msgs__msg__ChannelInfo * lhs, const elevation_map_msgs__msg__ChannelInfo * rhs);

/// Copy a msg/ChannelInfo message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__copy(
  const elevation_map_msgs__msg__ChannelInfo * input,
  elevation_map_msgs__msg__ChannelInfo * output);

/// Initialize array of msg/ChannelInfo messages.
/**
 * It allocates the memory for the number of elements and calls
 * elevation_map_msgs__msg__ChannelInfo__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__Sequence__init(elevation_map_msgs__msg__ChannelInfo__Sequence * array, size_t size);

/// Finalize array of msg/ChannelInfo messages.
/**
 * It calls
 * elevation_map_msgs__msg__ChannelInfo__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
void
elevation_map_msgs__msg__ChannelInfo__Sequence__fini(elevation_map_msgs__msg__ChannelInfo__Sequence * array);

/// Create array of msg/ChannelInfo messages.
/**
 * It allocates the memory for the array and calls
 * elevation_map_msgs__msg__ChannelInfo__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
elevation_map_msgs__msg__ChannelInfo__Sequence *
elevation_map_msgs__msg__ChannelInfo__Sequence__create(size_t size);

/// Destroy array of msg/ChannelInfo messages.
/**
 * It calls
 * elevation_map_msgs__msg__ChannelInfo__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
void
elevation_map_msgs__msg__ChannelInfo__Sequence__destroy(elevation_map_msgs__msg__ChannelInfo__Sequence * array);

/// Check for msg/ChannelInfo message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__Sequence__are_equal(const elevation_map_msgs__msg__ChannelInfo__Sequence * lhs, const elevation_map_msgs__msg__ChannelInfo__Sequence * rhs);

/// Copy an array of msg/ChannelInfo messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_elevation_map_msgs
bool
elevation_map_msgs__msg__ChannelInfo__Sequence__copy(
  const elevation_map_msgs__msg__ChannelInfo__Sequence * input,
  elevation_map_msgs__msg__ChannelInfo__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // ELEVATION_MAP_MSGS__MSG__DETAIL__CHANNEL_INFO__FUNCTIONS_H_
