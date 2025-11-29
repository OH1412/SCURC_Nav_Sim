# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_pangolin_simulation_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED pangolin_simulation_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(pangolin_simulation_FOUND FALSE)
  elseif(NOT pangolin_simulation_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(pangolin_simulation_FOUND FALSE)
  endif()
  return()
endif()
set(_pangolin_simulation_CONFIG_INCLUDED TRUE)

# output package information
if(NOT pangolin_simulation_FIND_QUIETLY)
  message(STATUS "Found pangolin_simulation: 1.0.0 (${pangolin_simulation_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'pangolin_simulation' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${pangolin_simulation_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(pangolin_simulation_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "ament_cmake_export_dependencies-extras.cmake")
foreach(_extra ${_extras})
  include("${pangolin_simulation_DIR}/${_extra}")
endforeach()
