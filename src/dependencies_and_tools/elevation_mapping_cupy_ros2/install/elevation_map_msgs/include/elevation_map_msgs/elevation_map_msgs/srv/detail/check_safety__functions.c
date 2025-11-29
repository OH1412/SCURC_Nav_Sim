// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from elevation_map_msgs:srv/CheckSafety.idl
// generated code does not contain a copyright notice
#include "elevation_map_msgs/srv/detail/check_safety__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"

// Include directives for member types
// Member `polygons`
#include "geometry_msgs/msg/detail/polygon_stamped__functions.h"

bool
elevation_map_msgs__srv__CheckSafety_Request__init(elevation_map_msgs__srv__CheckSafety_Request * msg)
{
  if (!msg) {
    return false;
  }
  // polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__init(&msg->polygons, 0)) {
    elevation_map_msgs__srv__CheckSafety_Request__fini(msg);
    return false;
  }
  // compute_untraversable_polygon
  return true;
}

void
elevation_map_msgs__srv__CheckSafety_Request__fini(elevation_map_msgs__srv__CheckSafety_Request * msg)
{
  if (!msg) {
    return;
  }
  // polygons
  geometry_msgs__msg__PolygonStamped__Sequence__fini(&msg->polygons);
  // compute_untraversable_polygon
}

bool
elevation_map_msgs__srv__CheckSafety_Request__are_equal(const elevation_map_msgs__srv__CheckSafety_Request * lhs, const elevation_map_msgs__srv__CheckSafety_Request * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__are_equal(
      &(lhs->polygons), &(rhs->polygons)))
  {
    return false;
  }
  // compute_untraversable_polygon
  if (lhs->compute_untraversable_polygon != rhs->compute_untraversable_polygon) {
    return false;
  }
  return true;
}

bool
elevation_map_msgs__srv__CheckSafety_Request__copy(
  const elevation_map_msgs__srv__CheckSafety_Request * input,
  elevation_map_msgs__srv__CheckSafety_Request * output)
{
  if (!input || !output) {
    return false;
  }
  // polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__copy(
      &(input->polygons), &(output->polygons)))
  {
    return false;
  }
  // compute_untraversable_polygon
  output->compute_untraversable_polygon = input->compute_untraversable_polygon;
  return true;
}

elevation_map_msgs__srv__CheckSafety_Request *
elevation_map_msgs__srv__CheckSafety_Request__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Request * msg = (elevation_map_msgs__srv__CheckSafety_Request *)allocator.allocate(sizeof(elevation_map_msgs__srv__CheckSafety_Request), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(elevation_map_msgs__srv__CheckSafety_Request));
  bool success = elevation_map_msgs__srv__CheckSafety_Request__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
elevation_map_msgs__srv__CheckSafety_Request__destroy(elevation_map_msgs__srv__CheckSafety_Request * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    elevation_map_msgs__srv__CheckSafety_Request__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
elevation_map_msgs__srv__CheckSafety_Request__Sequence__init(elevation_map_msgs__srv__CheckSafety_Request__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Request * data = NULL;

  if (size) {
    data = (elevation_map_msgs__srv__CheckSafety_Request *)allocator.zero_allocate(size, sizeof(elevation_map_msgs__srv__CheckSafety_Request), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = elevation_map_msgs__srv__CheckSafety_Request__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        elevation_map_msgs__srv__CheckSafety_Request__fini(&data[i - 1]);
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
elevation_map_msgs__srv__CheckSafety_Request__Sequence__fini(elevation_map_msgs__srv__CheckSafety_Request__Sequence * array)
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
      elevation_map_msgs__srv__CheckSafety_Request__fini(&array->data[i]);
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

elevation_map_msgs__srv__CheckSafety_Request__Sequence *
elevation_map_msgs__srv__CheckSafety_Request__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Request__Sequence * array = (elevation_map_msgs__srv__CheckSafety_Request__Sequence *)allocator.allocate(sizeof(elevation_map_msgs__srv__CheckSafety_Request__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = elevation_map_msgs__srv__CheckSafety_Request__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
elevation_map_msgs__srv__CheckSafety_Request__Sequence__destroy(elevation_map_msgs__srv__CheckSafety_Request__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    elevation_map_msgs__srv__CheckSafety_Request__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
elevation_map_msgs__srv__CheckSafety_Request__Sequence__are_equal(const elevation_map_msgs__srv__CheckSafety_Request__Sequence * lhs, const elevation_map_msgs__srv__CheckSafety_Request__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!elevation_map_msgs__srv__CheckSafety_Request__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
elevation_map_msgs__srv__CheckSafety_Request__Sequence__copy(
  const elevation_map_msgs__srv__CheckSafety_Request__Sequence * input,
  elevation_map_msgs__srv__CheckSafety_Request__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(elevation_map_msgs__srv__CheckSafety_Request);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    elevation_map_msgs__srv__CheckSafety_Request * data =
      (elevation_map_msgs__srv__CheckSafety_Request *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!elevation_map_msgs__srv__CheckSafety_Request__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          elevation_map_msgs__srv__CheckSafety_Request__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!elevation_map_msgs__srv__CheckSafety_Request__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}


// Include directives for member types
// Member `is_safe`
// Member `traversability`
#include "rosidl_runtime_c/primitives_sequence_functions.h"
// Member `untraversable_polygons`
// already included above
// #include "geometry_msgs/msg/detail/polygon_stamped__functions.h"

bool
elevation_map_msgs__srv__CheckSafety_Response__init(elevation_map_msgs__srv__CheckSafety_Response * msg)
{
  if (!msg) {
    return false;
  }
  // is_safe
  if (!rosidl_runtime_c__boolean__Sequence__init(&msg->is_safe, 0)) {
    elevation_map_msgs__srv__CheckSafety_Response__fini(msg);
    return false;
  }
  // traversability
  if (!rosidl_runtime_c__double__Sequence__init(&msg->traversability, 0)) {
    elevation_map_msgs__srv__CheckSafety_Response__fini(msg);
    return false;
  }
  // untraversable_polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__init(&msg->untraversable_polygons, 0)) {
    elevation_map_msgs__srv__CheckSafety_Response__fini(msg);
    return false;
  }
  return true;
}

void
elevation_map_msgs__srv__CheckSafety_Response__fini(elevation_map_msgs__srv__CheckSafety_Response * msg)
{
  if (!msg) {
    return;
  }
  // is_safe
  rosidl_runtime_c__boolean__Sequence__fini(&msg->is_safe);
  // traversability
  rosidl_runtime_c__double__Sequence__fini(&msg->traversability);
  // untraversable_polygons
  geometry_msgs__msg__PolygonStamped__Sequence__fini(&msg->untraversable_polygons);
}

bool
elevation_map_msgs__srv__CheckSafety_Response__are_equal(const elevation_map_msgs__srv__CheckSafety_Response * lhs, const elevation_map_msgs__srv__CheckSafety_Response * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // is_safe
  if (!rosidl_runtime_c__boolean__Sequence__are_equal(
      &(lhs->is_safe), &(rhs->is_safe)))
  {
    return false;
  }
  // traversability
  if (!rosidl_runtime_c__double__Sequence__are_equal(
      &(lhs->traversability), &(rhs->traversability)))
  {
    return false;
  }
  // untraversable_polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__are_equal(
      &(lhs->untraversable_polygons), &(rhs->untraversable_polygons)))
  {
    return false;
  }
  return true;
}

bool
elevation_map_msgs__srv__CheckSafety_Response__copy(
  const elevation_map_msgs__srv__CheckSafety_Response * input,
  elevation_map_msgs__srv__CheckSafety_Response * output)
{
  if (!input || !output) {
    return false;
  }
  // is_safe
  if (!rosidl_runtime_c__boolean__Sequence__copy(
      &(input->is_safe), &(output->is_safe)))
  {
    return false;
  }
  // traversability
  if (!rosidl_runtime_c__double__Sequence__copy(
      &(input->traversability), &(output->traversability)))
  {
    return false;
  }
  // untraversable_polygons
  if (!geometry_msgs__msg__PolygonStamped__Sequence__copy(
      &(input->untraversable_polygons), &(output->untraversable_polygons)))
  {
    return false;
  }
  return true;
}

elevation_map_msgs__srv__CheckSafety_Response *
elevation_map_msgs__srv__CheckSafety_Response__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Response * msg = (elevation_map_msgs__srv__CheckSafety_Response *)allocator.allocate(sizeof(elevation_map_msgs__srv__CheckSafety_Response), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(elevation_map_msgs__srv__CheckSafety_Response));
  bool success = elevation_map_msgs__srv__CheckSafety_Response__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
elevation_map_msgs__srv__CheckSafety_Response__destroy(elevation_map_msgs__srv__CheckSafety_Response * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    elevation_map_msgs__srv__CheckSafety_Response__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
elevation_map_msgs__srv__CheckSafety_Response__Sequence__init(elevation_map_msgs__srv__CheckSafety_Response__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Response * data = NULL;

  if (size) {
    data = (elevation_map_msgs__srv__CheckSafety_Response *)allocator.zero_allocate(size, sizeof(elevation_map_msgs__srv__CheckSafety_Response), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = elevation_map_msgs__srv__CheckSafety_Response__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        elevation_map_msgs__srv__CheckSafety_Response__fini(&data[i - 1]);
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
elevation_map_msgs__srv__CheckSafety_Response__Sequence__fini(elevation_map_msgs__srv__CheckSafety_Response__Sequence * array)
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
      elevation_map_msgs__srv__CheckSafety_Response__fini(&array->data[i]);
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

elevation_map_msgs__srv__CheckSafety_Response__Sequence *
elevation_map_msgs__srv__CheckSafety_Response__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  elevation_map_msgs__srv__CheckSafety_Response__Sequence * array = (elevation_map_msgs__srv__CheckSafety_Response__Sequence *)allocator.allocate(sizeof(elevation_map_msgs__srv__CheckSafety_Response__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = elevation_map_msgs__srv__CheckSafety_Response__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
elevation_map_msgs__srv__CheckSafety_Response__Sequence__destroy(elevation_map_msgs__srv__CheckSafety_Response__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    elevation_map_msgs__srv__CheckSafety_Response__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
elevation_map_msgs__srv__CheckSafety_Response__Sequence__are_equal(const elevation_map_msgs__srv__CheckSafety_Response__Sequence * lhs, const elevation_map_msgs__srv__CheckSafety_Response__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!elevation_map_msgs__srv__CheckSafety_Response__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
elevation_map_msgs__srv__CheckSafety_Response__Sequence__copy(
  const elevation_map_msgs__srv__CheckSafety_Response__Sequence * input,
  elevation_map_msgs__srv__CheckSafety_Response__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(elevation_map_msgs__srv__CheckSafety_Response);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    elevation_map_msgs__srv__CheckSafety_Response * data =
      (elevation_map_msgs__srv__CheckSafety_Response *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!elevation_map_msgs__srv__CheckSafety_Response__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          elevation_map_msgs__srv__CheckSafety_Response__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!elevation_map_msgs__srv__CheckSafety_Response__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
