// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from elevation_map_msgs:msg/ChannelInfo.idl
// generated code does not contain a copyright notice
#include "elevation_map_msgs/msg/detail/channel_info__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/detail/header__functions.h"
// Member `channels`
#include "rosidl_runtime_c/string_functions.h"

bool
elevation_map_msgs__msg__ChannelInfo__init(elevation_map_msgs__msg__ChannelInfo * msg)
{
  if (!msg) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__init(&msg->header)) {
    elevation_map_msgs__msg__ChannelInfo__fini(msg);
    return false;
  }
  // channels
  if (!rosidl_runtime_c__String__Sequence__init(&msg->channels, 0)) {
    elevation_map_msgs__msg__ChannelInfo__fini(msg);
    return false;
  }
  return true;
}

void
elevation_map_msgs__msg__ChannelInfo__fini(elevation_map_msgs__msg__ChannelInfo * msg)
{
  if (!msg) {
    return;
  }
  // header
  std_msgs__msg__Header__fini(&msg->header);
  // channels
  rosidl_runtime_c__String__Sequence__fini(&msg->channels);
}

bool
elevation_map_msgs__msg__ChannelInfo__are_equal(const elevation_map_msgs__msg__ChannelInfo * lhs, const elevation_map_msgs__msg__ChannelInfo * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__are_equal(
      &(lhs->header), &(rhs->header)))
  {
    return false;
  }
  // channels
  if (!rosidl_runtime_c__String__Sequence__are_equal(
      &(lhs->channels), &(rhs->channels)))
  {
    return false;
  }
  return true;
}

bool
elevation_map_msgs__msg__ChannelInfo__copy(
  const elevation_map_msgs__msg__ChannelInfo * input,
  elevation_map_msgs__msg__ChannelInfo * output)
{
  if (!input || !output) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__copy(
      &(input->header), &(output->header)))
  {
    return false;
  }
  // channels
  if (!rosidl_runtime_c__String__Sequence__copy(
      &(input->channels), &(output->channels)))
  {
    return false;
  }
  return true;
}

elevation_map_msgs__msg__ChannelInfo *
elevation_map_msgs__msg__ChannelInfo__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__msg__ChannelInfo * msg = (elevation_map_msgs__msg__ChannelInfo *)allocator.allocate(sizeof(elevation_map_msgs__msg__ChannelInfo), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(elevation_map_msgs__msg__ChannelInfo));
  bool success = elevation_map_msgs__msg__ChannelInfo__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
elevation_map_msgs__msg__ChannelInfo__destroy(elevation_map_msgs__msg__ChannelInfo * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    elevation_map_msgs__msg__ChannelInfo__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
elevation_map_msgs__msg__ChannelInfo__Sequence__init(elevation_map_msgs__msg__ChannelInfo__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__msg__ChannelInfo * data = NULL;

  if (size) {
    data = (elevation_map_msgs__msg__ChannelInfo *)allocator.zero_allocate(size, sizeof(elevation_map_msgs__msg__ChannelInfo), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = elevation_map_msgs__msg__ChannelInfo__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        elevation_map_msgs__msg__ChannelInfo__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
elevation_map_msgs__msg__ChannelInfo__Sequence__fini(elevation_map_msgs__msg__ChannelInfo__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      elevation_map_msgs__msg__ChannelInfo__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

elevation_map_msgs__msg__ChannelInfo__Sequence *
elevation_map_msgs__msg__ChannelInfo__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__msg__ChannelInfo__Sequence * array = (elevation_map_msgs__msg__ChannelInfo__Sequence *)allocator.allocate(sizeof(elevation_map_msgs__msg__ChannelInfo__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = elevation_map_msgs__msg__ChannelInfo__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
elevation_map_msgs__msg__ChannelInfo__Sequence__destroy(elevation_map_msgs__msg__ChannelInfo__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    elevation_map_msgs__msg__ChannelInfo__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
elevation_map_msgs__msg__ChannelInfo__Sequence__are_equal(const elevation_map_msgs__msg__ChannelInfo__Sequence * lhs, const elevation_map_msgs__msg__ChannelInfo__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!elevation_map_msgs__msg__ChannelInfo__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
elevation_map_msgs__msg__ChannelInfo__Sequence__copy(
  const elevation_map_msgs__msg__ChannelInfo__Sequence * input,
  elevation_map_msgs__msg__ChannelInfo__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(elevation_map_msgs__msg__ChannelInfo);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    elevation_map_msgs__msg__ChannelInfo * data =
      (elevation_map_msgs__msg__ChannelInfo *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!elevation_map_msgs__msg__ChannelInfo__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          elevation_map_msgs__msg__ChannelInfo__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!elevation_map_msgs__msg__ChannelInfo__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
