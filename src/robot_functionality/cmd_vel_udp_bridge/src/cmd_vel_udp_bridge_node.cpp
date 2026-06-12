#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>

#include <geometry_msgs/msg/twist.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <yaml-cpp/yaml.h>

namespace cmd_vel_udp_bridge {

#pragma pack(push, 1)
struct UdpCommand {
  int32_t mode = 2;
  float vx = 0.0f;
  float vy = 0.0f;
  float yaw = 0.0f;
  uint8_t e_stop = 0;
};
#pragma pack(pop)

static_assert(sizeof(UdpCommand) == 17, "UdpCommand must be 17 bytes packed");

class CmdVelUdpBridgeNode : public rclcpp::Node {
public:
  CmdVelUdpBridgeNode() : Node("cmd_vel_udp_bridge") {
    udp_ip_ = declare_parameter<std::string>("udp_ip", "127.0.0.1");
    udp_port_ = declare_parameter<int>("udp_port", 9870);
    mode_ = declare_parameter<int>("mode", 2);
    cmd_vx_min_ = declare_parameter<double>("cmd_vx_min", -1.0);
    cmd_vx_max_ = declare_parameter<double>("cmd_vx_max", 1.0);
    cmd_vy_min_ = declare_parameter<double>("cmd_vy_min", -1.0);
    cmd_vy_max_ = declare_parameter<double>("cmd_vy_max", 1.0);
    cmd_yaw_min_ = declare_parameter<double>("cmd_yaw_min", -1.0);
    cmd_yaw_max_ = declare_parameter<double>("cmd_yaw_max", 1.0);
    use_twist_stamped_ = declare_parameter<bool>("use_twist_stamped", false);
    cmd_vel_topic_ = declare_parameter<std::string>("cmd_vel_topic", "/cmd_vel");
    estop_topic_ = declare_parameter<std::string>("estop_topic", "");
    deploy_config_file_ = declare_parameter<std::string>("deploy_config_file", "");

    if (!deploy_config_file_.empty()) {
      load_velocity_limits_from_yaml(deploy_config_file_);
    }

    setup_socket();
    setup_subscribers();

    RCLCPP_INFO(get_logger(),
                "cmd_vel_udp_bridge: topic=%s ip=%s port=%d mode=%d",
                cmd_vel_topic_.c_str(), udp_ip_.c_str(), udp_port_, mode_);
    RCLCPP_INFO(get_logger(),
                "limits: vx[%.2f, %.2f] vy[%.2f, %.2f] yaw[%.2f, %.2f]",
                cmd_vx_min_, cmd_vx_max_, cmd_vy_min_, cmd_vy_max_,
                cmd_yaw_min_, cmd_yaw_max_);
  }

  ~CmdVelUdpBridgeNode() override {
    if (sock_fd_ >= 0) {
      ::close(sock_fd_);
      sock_fd_ = -1;
    }
  }

private:
  void setup_socket() {
    sock_fd_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_fd_ < 0) {
      throw std::runtime_error("Failed to create UDP socket");
    }

    std::memset(&dest_addr_, 0, sizeof(dest_addr_));
    dest_addr_.sin_family = AF_INET;
    dest_addr_.sin_port = htons(static_cast<uint16_t>(udp_port_));
    if (::inet_pton(AF_INET, udp_ip_.c_str(), &dest_addr_.sin_addr) != 1) {
      throw std::runtime_error("Invalid udp_ip: " + udp_ip_);
    }
  }

  void setup_subscribers() {
    if (use_twist_stamped_) {
      cmd_vel_stamped_sub_ = create_subscription<geometry_msgs::msg::TwistStamped>(
          cmd_vel_topic_, rclcpp::QoS(10),
          [this](const geometry_msgs::msg::TwistStamped::SharedPtr msg) {
            handle_twist(msg->twist);
          });
    } else {
      cmd_vel_sub_ = create_subscription<geometry_msgs::msg::Twist>(
          cmd_vel_topic_, rclcpp::QoS(10),
          [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
            handle_twist(*msg);
          });
    }

    if (!estop_topic_.empty()) {
      estop_sub_ = create_subscription<std_msgs::msg::Bool>(
          estop_topic_, rclcpp::QoS(10),
          [this](const std_msgs::msg::Bool::SharedPtr msg) {
            estop_latched_ = msg->data;
          });
    }
  }

  void handle_twist(const geometry_msgs::msg::Twist &msg) {
    UdpCommand cmd;
    cmd.mode = mode_;
    cmd.e_stop = estop_latched_ ? 1 : 0;

    cmd.vx = static_cast<float>(scale_ratio(msg.linear.x, cmd_vx_min_, cmd_vx_max_));
    cmd.vy = static_cast<float>(scale_ratio(msg.linear.y, cmd_vy_min_, cmd_vy_max_));
    cmd.yaw = static_cast<float>(scale_ratio(msg.angular.z, cmd_yaw_min_, cmd_yaw_max_));

    send_packet(cmd);
  }

  double scale_ratio(double value, double min_value, double max_value) const {
    if (!std::isfinite(value) || max_value <= 0.0 || min_value >= max_value) {
      return 0.0;
    }
    value = std::clamp(value, min_value, max_value);
    const double ratio = value / max_value;
    return std::clamp(ratio, -1.0, 1.0);
  }

  void load_velocity_limits_from_yaml(const std::string &yaml_path) {
    try {
      YAML::Node root = YAML::LoadFile(yaml_path);
      if (root["cmd_vx_min"]) cmd_vx_min_ = root["cmd_vx_min"].as<double>();
      if (root["cmd_vx_max"]) cmd_vx_max_ = root["cmd_vx_max"].as<double>();
      if (root["cmd_vy_min"]) cmd_vy_min_ = root["cmd_vy_min"].as<double>();
      if (root["cmd_vy_max"]) cmd_vy_max_ = root["cmd_vy_max"].as<double>();
      if (root["cmd_yaw_min"]) cmd_yaw_min_ = root["cmd_yaw_min"].as<double>();
      if (root["cmd_yaw_max"]) cmd_yaw_max_ = root["cmd_yaw_max"].as<double>();
    } catch (const std::exception &e) {
      RCLCPP_WARN(get_logger(), "Failed to load deploy_config_file: %s", e.what());
    }
  }

  void send_packet(const UdpCommand &cmd) {
    const ssize_t sent = ::sendto(sock_fd_, &cmd, sizeof(cmd), 0,
                                  reinterpret_cast<struct sockaddr *>(&dest_addr_),
                                  sizeof(dest_addr_));
    if (sent != static_cast<ssize_t>(sizeof(cmd))) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000,
                           "UDP send failed or partial (%ld bytes)",
                           static_cast<long>(sent));
    }
  }

  std::string udp_ip_;
  int udp_port_ = 9870;
  int mode_ = 2;
  std::string deploy_config_file_;

  double cmd_vx_min_ = -1.0;
  double cmd_vx_max_ = 1.0;
  double cmd_vy_min_ = -1.0;
  double cmd_vy_max_ = 1.0;
  double cmd_yaw_min_ = -1.0;
  double cmd_yaw_max_ = 3.14;
  bool use_twist_stamped_ = false;
  std::string cmd_vel_topic_ = "/cmd_vel";
  std::string estop_topic_;

  int sock_fd_ = -1;
  struct sockaddr_in dest_addr_ {};

  bool estop_latched_ = false;

  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Subscription<geometry_msgs::msg::TwistStamped>::SharedPtr cmd_vel_stamped_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr estop_sub_;
};

}  // namespace cmd_vel_udp_bridge

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<cmd_vel_udp_bridge::CmdVelUdpBridgeNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
