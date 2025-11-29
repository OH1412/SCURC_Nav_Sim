// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from elevation_map_msgs:srv/Initialize.idl
// generated code does not contain a copyright notice
#include "elevation_map_msgs/srv/detail/initialize__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

// Include directives for member types
// Member `points`
#include "geometry_msgs/msg/detail/point_stamped__functions.h"

bool
elevation_map_msgs__srv__Initialize_Request__init(elevation_map_msgs__srv__Initialize_Request * msg)
{
  if (!msg) {
    return false;
  }
  // type
  // method
  // points
  if (!geometry_msgs__msg__PointStamped__Sequence__init(&msg->points, 0)) {
    elevation_map_msgs__srv__Initialize_Request__fini(msg);
    return false;
  }
  return true;
}

void
elevation_map_msgs__srv__Initialize_Request__fini(elevation_map_msgs__srv__Initialize_Request * msg)
{
  if (!msg) {
    return;
  }
  // type
  // method
  // points
  geometry_msgs__msg__PointStamped__Sequence__fini(&msg->points);
}

bool
elevation_map_msgs__srv__Initialize_Request__are_equal(const elevation_map_msgs__srv__Initialize_Request * lhs, const elevation_map_msgs__srv__Initialize_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // type
  if (lhs->type != rhs->type) {
    return false;
  }
  // method
  if (lhs->method != rhs->method) {
    return false;
  }
  // points
  if (!geometry_msgs__msg__PointStamped__Sequence__are_equal(
      &(lhs->points), &(rhs->points)))
  {
    return false;
  }
  return true;
}

bool
elevation_map_msgs__srv__Initialize_Request__copy(
  const elevation_map_msgs__srv__Initialize_Request * input,
  elevation_map_msgs__srv__Initialize_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // type
  output->type = input->type;
  // method
  output->method = input->method;
  // points
  if (!geometry_msgs__msg__PointStamped__Sequence__copy(
      &(input->points), &(output->points)))
  {
    return false;
  }
  return true;
}

elevation_map_msgs__srv__Initialize_Request *
elevation_map_msgs__srv__Initialize_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Request * msg = (elevation_map_msgs__srv__Initialize_Request *)allocator.allocate(sizeof(elevation_map_msgs__srv__Initialize_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(elevation_map_msgs__srv__Initialize_Request));
  bool success = elevation_map_msgs__srv__Initialize_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
elevation_map_msgs__srv__Initialize_Request__destroy(elevation_map_msgs__srv__Initialize_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    elevation_map_msgs__srv__Initialize_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
elevation_map_msgs__srv__Initialize_Request__Sequence__init(elevation_map_msgs__srv__Initialize_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Request * data = NULL;

  if (size) {
    data = (elevation_map_msgs__srv__Initialize_Request *)allocator.zero_allocate(size, sizeof(elevation_map_msgs__srv__Initialize_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = elevation_map_msgs__srv__Initialize_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        elevation_map_msgs__srv__Initialize_Request__fini(&data[i - 1]);
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
elevation_map_msgs__srv__Initialize_Request__Sequence__fini(elevation_map_msgs__srv__Initialize_Request__Sequence * array)
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
      elevation_map_msgs__srv__Initialize_Request__fini(&array->data[i]);
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

elevation_map_msgs__srv__Initialize_Request__Sequence *
elevation_map_msgs__srv__Initialize_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Request__Sequence * array = (elevation_map_msgs__srv__Initialize_Request__Sequence *)allocator.allocate(sizeof(elevation_map_msgs__srv__Initialize_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = elevation_map_msgs__srv__Initialize_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
elevation_map_msgs__srv__Initialize_Request__Sequence__destroy(elevation_map_msgs__srv__Initialize_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    elevation_map_msgs__srv__Initialize_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
elevation_map_msgs__srv__Initialize_Request__Sequence__are_equal(const elevation_map_msgs__srv__Initialize_Request__Sequence * lhs, const elevation_map_msgs__srv__Initialize_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!elevation_map_msgs__srv__Initialize_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
elevation_map_msgs__srv__Initialize_Request__Sequence__copy(
  const elevation_map_msgs__srv__Initialize_Request__Sequence * input,
  elevation_map_msgs__srv__Initialize_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(elevation_map_msgs__srv__Initialize_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    elevation_map_msgs__srv__Initialize_Request * data =
      (elevation_map_msgs__srv__Initialize_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!elevation_map_msgs__srv__Initialize_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          elevation_map_msgs__srv__Initialize_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!elevation_map_msgs__srv__Initialize_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


bool
elevation_map_msgs__srv__Initialize_Response__init(elevation_map_msgs__srv__Initialize_Response * msg)
{
  if (!msg) {
    return false;
  }
  // success
  return true;
}

void
elevation_map_msgs__srv__Initialize_Response__fini(elevation_map_msgs__srv__Initialize_Response * msg)
{
  if (!msg) {
    return;
  }
  // success
}

bool
elevation_map_msgs__srv__Initialize_Response__are_equal(const elevation_map_msgs__srv__Initialize_Response * lhs, const elevation_map_msgs__srv__Initialize_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // success
  if (lhs->success != rhs->success) {
    return false;
  }
  return true;
}

bool
elevation_map_msgs__srv__Initialize_Response__copy(
  const elevation_map_msgs__srv__Initialize_Response * input,
  elevation_map_msgs__srv__Initialize_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // success
  output->success = input->success;
  return true;
}

elevation_map_msgs__srv__Initialize_Response *
elevation_map_msgs__srv__Initialize_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Response * msg = (elevation_map_msgs__srv__Initialize_Response *)allocator.allocate(sizeof(elevation_map_msgs__srv__Initialize_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(elevation_map_msgs__srv__Initialize_Response));
  bool success = elevation_map_msgs__srv__Initialize_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
elevation_map_msgs__srv__Initialize_Response__destroy(elevation_map_msgs__srv__Initialize_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    elevation_map_msgs__srv__Initialize_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
elevation_map_msgs__srv__Initialize_Response__Sequence__init(elevation_map_msgs__srv__Initialize_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Response * data = NULL;

  if (size) {
    data = (elevation_map_msgs__srv__Initialize_Response *)allocator.zero_allocate(size, sizeof(elevation_map_msgs__srv__Initialize_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = elevation_map_msgs__srv__Initialize_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        elevation_map_msgs__srv__Initialize_Response__fini(&data[i - 1]);
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
elevation_map_msgs__srv__Initialize_Response__Sequence__fini(elevation_map_msgs__srv__Initialize_Response__Sequence * array)
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
      elevation_map_msgs__srv__Initialize_Response__fini(&array->data[i]);
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

elevation_map_msgs__srv__Initialize_Response__Sequence *
elevation_map_msgs__srv__Initialize_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__Initialize_Response__Sequence * array = (elevation_map_msgs__srv__Initialize_Response__Sequence *)allocator.allocate(sizeof(elevation_map_msgs__srv__Initialize_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = elevation_map_msgs__srv__Initialize_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
elevation_map_msgs__srv__Initialize_Response__Sequence__destroy(elevation_map_msgs__srv__Initialize_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    elevation_map_msgs__srv__Initialize_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
elevation_map_msgs__srv__Initialize_Response__Sequence__are_equal(const elevation_map_msgs__srv__Initialize_Response__Sequence * lhs, const elevation_map_msgs__srv__Initialize_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!elevation_map_msgs__srv__Initialize_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
elevation_map_msgs__srv__Initialize_Response__Sequence__copy(
  const elevation_map_msgs__srv__Initialize_Response__Sequence * input,
  elevation_map_msgs__srv__Initialize_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(elevation_map_msgs__srv__Initialize_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    elevation_map_msgs__srv__Initialize_Response * data =
      (elevation_map_msgs__srv__Initialize_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!elevation_map_msgs__srv__Initialize_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          elevation_map_msgs__srv__Initialize_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!elevation_map_msgs__srv__Initialize_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
