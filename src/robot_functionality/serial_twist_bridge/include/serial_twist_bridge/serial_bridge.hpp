#ifndef SERIAL_TWIST_BRIDGE__SERIAL_BRIDGE_HPP_
#define SERIAL_TWIST_BRIDGE__SERIAL_BRIDGE_HPP_

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <std_msgs/msg/string.hpp>

#include <string>
#include <memory>
#include <thread>
#include <atomic>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>

namespace serial_twist_bridge
{

class SerialBridge : public rclcpp::Node
{
public:
  SerialBridge();
  ~SerialBridge();

private:
  // ROS2 interfaces
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr twist_subscriber_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr debug_publisher_;

  // Serial communication
  int serial_port_;
  std::string serial_device_;
  int baud_rate_;

  // Thread for serial communication
  std::thread serial_thread_;
  std::atomic<bool> running_;

  // Parameters
  std::string twist_topic_;
  double publish_rate_;
  std::string frame_id_;

  // Callbacks
  void twistCallback(const geometry_msgs::msg::Twist::SharedPtr msg);

  // Serial functions
  bool openSerialPort();
  void closeSerialPort();
  bool configureSerialPort();
  void serialWorker();
  bool sendToMCU(const std::string& data);
  std::string formatTwistMessage(const geometry_msgs::msg::Twist::SharedPtr msg);

  // Utility functions
  int getBaudRateConstant(int baud_rate);
};

}  // namespace serial_twist_bridge

#endif  // SERIAL_TWIST_BRIDGE__SERIAL_BRIDGE_HPP_
