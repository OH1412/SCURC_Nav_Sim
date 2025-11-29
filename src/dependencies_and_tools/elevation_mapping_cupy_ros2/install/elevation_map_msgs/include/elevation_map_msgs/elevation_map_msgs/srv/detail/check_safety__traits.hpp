// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from elevation_map_msgs:srv/CheckSafety.idl
// generated code does not contain a copyright notice

#ifndef ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__TRAITS_HPP_
#define ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "elevation_map_msgs/srv/detail/check_safety__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'polygons'
#include "geometry_msgs/msg/detail/polygon_stamped__traits.hpp"

namespace elevation_map_msgs
{

namespace srv
{

inline void to_flow_style_yaml(
  const CheckSafety_Request & msg,
  std::ostream & out)
{
  out << "{";
  // member: polygons
  {
    if (msg.polygons.size() == 0) {
      out << "polygons: []";
    } else {
      out << "polygons: [";
      size_t pending_items = msg.polygons.size();
      for (auto item : msg.polygons) {
        to_flow_style_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
    out << ", ";
  }

  // member: compute_untraversable_polygon
  {
    out << "compute_untraversable_polygon: ";
    rosidl_generator_traits::value_to_yaml(msg.compute_untraversable_polygon, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const CheckSafety_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: polygons
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.polygons.size() == 0) {
      out << "polygons: []\n";
    } else {
      out << "polygons:\n";
      for (auto item : msg.polygons) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "-\n";
        to_block_style_yaml(item, out, indentation + 2);
      }
    }
  }

  // member: compute_untraversable_polygon
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "compute_untraversable_polygon: ";
    rosidl_generator_traits::value_to_yaml(msg.compute_untraversable_polygon, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const CheckSafety_Request & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace elevation_map_msgs

namespace rosidl_generator_traits
{

[[deprecated("use elevation_map_msgs::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const elevation_map_msgs::srv::CheckSafety_Request & msg,
  std::ostream & out, size_t indentation = 0)
{
  elevation_map_msgs::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use elevation_map_msgs::srv::to_yaml() instead")]]
inline std::string to_yaml(const elevation_map_msgs::srv::CheckSafety_Request & msg)
{
  return elevation_map_msgs::srv::to_yaml(msg);
}

template<>
inline const char * data_type<elevation_map_msgs::srv::CheckSafety_Request>()
{
  return "elevation_map_msgs::srv::CheckSafety_Request";
}

template<>
inline const char * name<elevation_map_msgs::srv::CheckSafety_Request>()
{
  return "elevation_map_msgs/srv/CheckSafety_Request";
}

template<>
struct has_fixed_size<elevation_map_msgs::srv::CheckSafety_Request>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<elevation_map_msgs::srv::CheckSafety_Request>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<elevation_map_msgs::srv::CheckSafety_Request>
  : std::true_type {};

}  // namespace rosidl_generator_traits

// Include directives for member types
// Member 'untraversable_polygons'
// already included above
// #include "geometry_msgs/msg/detail/polygon_stamped__traits.hpp"

namespace elevation_map_msgs
{

namespace srv
{

inline void to_flow_style_yaml(
  const CheckSafety_Response & msg,
  std::ostream & out)
{
  out << "{";
  // member: is_safe
  {
    if (msg.is_safe.size() == 0) {
      out << "is_safe: []";
    } else {
      out << "is_safe: [";
      size_t pending_items = msg.is_safe.size();
      for (auto item : msg.is_safe) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
    out << ", ";
  }

  // member: traversability
  {
    if (msg.traversability.size() == 0) {
      out << "traversability: []";
    } else {
      out << "traversability: [";
      size_t pending_items = msg.traversability.size();
      for (auto item : msg.traversability) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
    out << ", ";
  }

  // member: untraversable_polygons
  {
    if (msg.untraversable_polygons.size() == 0) {
      out << "untraversable_polygons: []";
    } else {
      out << "untraversable_polygons: [";
      size_t pending_items = msg.untraversable_polygons.size();
      for (auto item : msg.untraversable_polygons) {
        to_flow_style_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const CheckSafety_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: is_safe
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.is_safe.size() == 0) {
      out << "is_safe: []\n";
    } else {
      out << "is_safe:\n";
      for (auto item : msg.is_safe) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }

  // member: traversability
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.traversability.size() == 0) {
      out << "traversability: []\n";
    } else {
      out << "traversability:\n";
      for (auto item : msg.traversability) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }

  // member: untraversable_polygons
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.untraversable_polygons.size() == 0) {
      out << "untraversable_polygons: []\n";
    } else {
      out << "untraversable_polygons:\n";
      for (auto item : msg.untraversable_polygons) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "-\n";
        to_block_style_yaml(item, out, indentation + 2);
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const CheckSafety_Response & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace srv

}  // namespace elevation_map_msgs

namespace rosidl_generator_traits
{

[[deprecated("use elevation_map_msgs::srv::to_block_style_yaml() instead")]]
inline void to_yaml(
  const elevation_map_msgs::srv::CheckSafety_Response & msg,
  std::ostream & out, size_t indentation = 0)
{
  elevation_map_msgs::srv::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use elevation_map_msgs::srv::to_yaml() instead")]]
inline std::string to_yaml(const elevation_map_msgs::srv::CheckSafety_Response & msg)
{
  return elevation_map_msgs::srv::to_yaml(msg);
}

template<>
inline const char * data_type<elevation_map_msgs::srv::CheckSafety_Response>()
{
  return "elevation_map_msgs::srv::CheckSafety_Response";
}

template<>
inline const char * name<elevation_map_msgs::srv::CheckSafety_Response>()
{
  return "elevation_map_msgs/srv/CheckSafety_Response";
}

template<>
struct has_fixed_size<elevation_map_msgs::srv::CheckSafety_Response>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<elevation_map_msgs::srv::CheckSafety_Response>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<elevation_map_msgs::srv::CheckSafety_Response>
  : std::true_type {};

}  // namespace rosidl_generator_traits

namespace rosidl_generator_traits
{

template<>
inline const char * data_type<elevation_map_msgs::srv::CheckSafety>()
{
  return "elevation_map_msgs::srv::CheckSafety";
}

template<>
inline const char * name<elevation_map_msgs::srv::CheckSafety>()
{
  return "elevation_map_msgs/srv/CheckSafety";
}

template<>
struct has_fixed_size<elevation_map_msgs::srv::CheckSafety>
  : std::integral_constant<
    bool,
    has_fixed_size<elevation_map_msgs::srv::CheckSafety_Request>::value &&
    has_fixed_size<elevation_map_msgs::srv::CheckSafety_Response>::value
  >
{
};

template<>
struct has_bounded_size<elevation_map_msgs::srv::CheckSafety>
  : std::integral_constant<
    bool,
    has_bounded_size<elevation_map_msgs::srv::CheckSafety_Request>::value &&
    has_bounded_size<elevation_map_msgs::srv::CheckSafety_Response>::value
  >
{
};

template<>
struct is_service<elevation_map_msgs::srv::CheckSafety>
  : std::true_type
{
};

template<>
struct is_service_request<elevation_map_msgs::srv::CheckSafety_Request>
  : std::true_type
{
};

template<>
struct is_service_response<elevation_map_msgs::srv::CheckSafety_Response>
  : std::true_type
{
};

}  // namespace rosidl_generator_traits

#endif  // ELEVATION_MAP_MSGS__SRV__DETAIL__CHECK_SAFETY__TRAITS_HPP_
