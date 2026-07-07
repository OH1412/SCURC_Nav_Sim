#pragma once

#include <cstdlib>
#include <mutex>
#include <sstream>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

namespace legged_bringup
{
namespace mission_log
{

inline std::string escape_json(const std::string & input)
{
  std::string out;
  out.reserve(input.size() + 8);
  for (char c : input) {
    switch (c) {
      case '\\': out += "\\\\"; break;
      case '"': out += "\\\""; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      default: out += c; break;
    }
  }
  return out;
}

inline void publish(
  rclcpp::Node & node,
  const std::string & source,
  const std::string & event_id,
  const std::string & level,
  const std::string & detail)
{
  // 环境变量 MISSION_LOG_ENABLED=0 可临时关闭所有日志
  static const bool kEnabled = []{
    const char* env = std::getenv("MISSION_LOG_ENABLED");
    return env == nullptr || env[0] != '0';
  }();
  if (!kEnabled) return;

  static std::mutex mutex;
  static std::weak_ptr<rclcpp::Publisher<std_msgs::msg::String>> weak_pub;

  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub;
  {
    std::lock_guard<std::mutex> lock(mutex);
    pub = weak_pub.lock();
    if (!pub) {
      pub = node.create_publisher<std_msgs::msg::String>(
        "/bringup/mission_log_event", rclcpp::QoS(rclcpp::KeepLast(512)).reliable());
      weak_pub = pub;
    }
  }

  const rclcpp::Time stamp = node.get_clock()->now();
  const int64_t ns = stamp.nanoseconds();
  const int64_t sec = ns / 1000000000LL;
  const int64_t nanosec = ns % 1000000000LL;
  std::ostringstream oss;
  oss << '{'
      << "\"sec\":" << sec << ','
      << "\"nanosec\":" << nanosec << ','
      << "\"source\":\"" << escape_json(source) << "\","
      << "\"event_id\":\"" << escape_json(event_id) << "\","
      << "\"level\":\"" << escape_json(level) << "\","
      << "\"detail\":\"" << escape_json(detail) << "\""
      << '}';

  std_msgs::msg::String msg;
  msg.data = oss.str();
  pub->publish(msg);
}

}  // namespace mission_log
}  // namespace legged_bringup
