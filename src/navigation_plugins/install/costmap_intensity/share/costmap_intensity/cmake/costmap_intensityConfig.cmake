# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_costmap_intensity_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED costmap_intensity_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(costmap_intensity_FOUND FALSE)
  elseif(NOT costmap_intensity_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(costmap_intensity_FOUND FALSE)
  endif()
  return()
endif()
set(_costmap_intensity_CONFIG_INCLUDED TRUE)

# output package information
if(NOT costmap_intensity_FIND_QUIETLY)
  message(STATUS "Found costmap_intensity: 1.1.12 (${costmap_intensity_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'costmap_intensity' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${costmap_intensity_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(costmap_intensity_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${costmap_intensity_DIR}/${_extra}")
endforeach()
