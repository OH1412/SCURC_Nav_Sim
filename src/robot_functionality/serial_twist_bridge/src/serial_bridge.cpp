#include "serial_twist_bridge/serial_bridge.hpp"

#include <chrono>
#include <iostream>
#include <sstream>
#include <cstring>
#include <cmath>
#include <iomanip>

using namespace std::chrono_literals;
using std::placeholders::_1;

namespace serial_twist_bridge
{

SerialBridge::SerialBridge()
: Node("serial_bridge"),
  serial_port_(-1),
  running_(true)
{
  // Declare parameters
  this->declare_parameter<std::string>("serial_device", "/dev/ttyUSB0");
  this->declare_parameter<int>("baud_rate", 115200);
  this->declare_parameter<std::string>("twist_topic", "/cmd_vel");
  this->declare_parameter<double>("publish_rate", 50.0);
  this->declare_parameter<std::string>("frame_id", "base_link");

  // Get parameters
  this->get_parameter("serial_device", serial_device_);
  this->get_parameter("baud_rate", baud_rate_);
  this->get_parameter("twist_topic", twist_topic_);
  this->get_parameter("publish_rate", publish_rate_);
  this->get_parameter("frame_id", frame_id_);

  // Create subscribers and publishers
  twist_subscriber_ = this->create_subscription<geometry_msgs::msg::Twist>(
    twist_topic_, 10, std::bind(&SerialBridge::twistCallback, this, _1));

  debug_publisher_ = this->create_publisher<std_msgs::msg::String>("serial_bridge/debug", 10);

  // Open serial port
  if (!openSerialPort()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to open serial port: %s", serial_device_.c_str());
    return;
  }

  // Start serial worker thread
  serial_thread_ = std::thread(&SerialBridge::serialWorker, this);

  RCLCPP_INFO(this->get_logger(), "Serial Twist Bridge initialized");
  RCLCPP_INFO(this->get_logger(), "Serial device: %s", serial_device_.c_str());
  RCLCPP_INFO(this->get_logger(), "Baud rate: %d", baud_rate_);
  RCLCPP_INFO(this->get_logger(), "Twist topic: %s", twist_topic_.c_str());
}

SerialBridge::~SerialBridge()
{
  running_ = false;
  if (serial_thread_.joinable()) {
    serial_thread_.join();
  }
  closeSerialPort();
}

void SerialBridge::twistCallback(const geometry_msgs::msg::Twist::SharedPtr msg)
{
  // Format message for MCU
  std::string serial_data = formatTwistMessage(msg);

  // Send to MCU
  if (sendToMCU(serial_data)) {
    // Publish debug message
    auto debug_msg = std_msgs::msg::String();
    debug_msg.data = "Sent: " + serial_data;
    debug_publisher_->publish(debug_msg);
  } else {
    RCLCPP_WARN(this->get_logger(), "Failed to send data to MCU");
  }
}

bool SerialBridge::openSerialPort()
{
  serial_port_ = open(serial_device_.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
  if (serial_port_ == -1) {
    RCLCPP_ERROR(this->get_logger(), "Failed to open serial port: %s", strerror(errno));
    return false;
  }

  if (!configureSerialPort()) {
    close(serial_port_);
    serial_port_ = -1;
    return false;
  }

  RCLCPP_INFO(this->get_logger(), "Serial port opened successfully");
  return true;
}

void SerialBridge::closeSerialPort()
{
  if (serial_port_ != -1) {
    close(serial_port_);
    serial_port_ = -1;
    RCLCPP_INFO(this->get_logger(), "Serial port closed");
  }
}

bool SerialBridge::configureSerialPort()
{
  struct termios tty;

  if (tcgetattr(serial_port_, &tty) != 0) {
    RCLCPP_ERROR(this->get_logger(), "Error getting serial port attributes: %s", strerror(errno));
    return false;
  }

  // Set baud rate
  int baud_constant = getBaudRateConstant(baud_rate_);
  cfsetospeed(&tty, baud_constant);
  cfsetispeed(&tty, baud_constant);

  // Configure serial port
  tty.c_cflag &= ~PARENB; // No parity
  tty.c_cflag &= ~CSTOPB; // 1 stop bit
  tty.c_cflag &= ~CSIZE;
  tty.c_cflag |= CS8;     // 8 data bits
  tty.c_cflag &= ~CRTSCTS; // No hardware flow control
  tty.c_cflag |= CREAD | CLOCAL; // Enable receiver, ignore modem control lines

  tty.c_iflag &= ~(IXON | IXOFF | IXANY); // Disable software flow control
  tty.c_iflag &= ~(IGNBRK|BRKINT|PARMRK|ISTRIP|INLCR|IGNCR|ICRNL); // Disable special handling

  tty.c_oflag &= ~OPOST; // Raw output
  tty.c_oflag &= ~ONLCR; // Don't convert line feeds

  tty.c_lflag &= ~ICANON; // Non-canonical mode
  tty.c_lflag &= ~ECHO;   // Disable echo
  tty.c_lflag &= ~ECHOE;  // Disable erasure
  tty.c_lflag &= ~ECHONL; // Disable new-line echo
  tty.c_lflag &= ~ISIG;   // Disable interpretation of INTR, QUIT and SUSP

  // Set timeouts
  tty.c_cc[VTIME] = 0; // No timeout
  tty.c_cc[VMIN] = 0;  // No minimum characters

  if (tcsetattr(serial_port_, TCSANOW, &tty) != 0) {
    RCLCPP_ERROR(this->get_logger(), "Error setting serial port attributes: %s", strerror(errno));
    return false;
  }

  return true;
}

int SerialBridge::getBaudRateConstant(int baud_rate)
{
  switch (baud_rate) {
    case 9600: return B9600;
    case 19200: return B19200;
    case 38400: return B38400;
    case 57600: return B57600;
    case 115200: return B115200;
    case 230400: return B230400;
    case 460800: return B460800;
    case 500000: return B500000;
    case 576000: return B576000;
    case 921600: return B921600;
    case 1000000: return B1000000;
    case 1152000: return B1152000;
    case 1500000: return B1500000;
    case 2000000: return B2000000;
    case 2500000: return B2500000;
    case 3000000: return B3000000;
    case 3500000: return B3500000;
    case 4000000: return B4000000;
    default:
      RCLCPP_WARN(this->get_logger(), "Unsupported baud rate %d, using 115200", baud_rate);
      return B115200;
  }
}

void SerialBridge::serialWorker()
{
  while (running_) {
    // 这里可以添加从MCU接收数据的逻辑
    std::this_thread::sleep_for(100ms);
  }
}

bool SerialBridge::sendToMCU(const std::string& data)
{
  if (serial_port_ == -1) {
    return false;
  }

  ssize_t bytes_written = write(serial_port_, data.c_str(), data.length());
  if (bytes_written < 0) {
    RCLCPP_ERROR(this->get_logger(), "Error writing to serial port: %s", strerror(errno));
    return false;
  }

  // Add newline for MCU parsing
  const char* newline = "\r\n";
  write(serial_port_, newline, strlen(newline));

  return true;
}

std::string SerialBridge::formatTwistMessage(const geometry_msgs::msg::Twist::SharedPtr msg)
{
  // Format: Vx,Vy,Vz,Wx,Wy,Wz
  // Example: 0.50,0.00,0.00,0.00,0.00,1.20
  std::stringstream ss;
  ss << std::fixed << std::setprecision(3);
  ss << msg->linear.x << ",";
  ss << msg->linear.y << ",";
  ss << msg->linear.z << ",";
  ss << msg->angular.x << ",";
  ss << msg->angular.y << ",";
  ss << msg->angular.z;

  return ss.str();
}

}  // namespace serial_twist_bridge

// Main function
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<serial_twist_bridge::SerialBridge>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
