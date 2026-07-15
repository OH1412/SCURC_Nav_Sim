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
#include "legged_bringup/mission_log.hpp"

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

    // 死区补偿参数：当速度非零但低于死区阈值时，自动提升到最小有效速度
    // 对称死区（正负方向使用同一阈值）
    deadzone_vx_ = declare_parameter<double>("deadzone_vx", 0.45);
    deadzone_vy_ = declare_parameter<double>("deadzone_vy", 0.43);
    deadzone_wz_ = declare_parameter<double>("deadzone_wz", 0.85);
    min_effective_vx_ = declare_parameter<double>("min_effective_vx", 0.5);
    min_effective_vy_ = declare_parameter<double>("min_effective_vy", 0.5);
    min_effective_wz_ = declare_parameter<double>("min_effective_wz", 0.9);
    // 非对称死区（正负方向独立设置，若未配置则沿用对称死区值）
    deadzone_vx_pos_ = declare_parameter<double>("deadzone_vx_positive", deadzone_vx_);
    deadzone_vx_neg_ = declare_parameter<double>("deadzone_vx_negative", deadzone_vx_);
    deadzone_vy_pos_ = declare_parameter<double>("deadzone_vy_positive", deadzone_vy_);
    deadzone_vy_neg_ = declare_parameter<double>("deadzone_vy_negative", deadzone_vy_);
    deadzone_wz_pos_ = declare_parameter<double>("deadzone_wz_positive", deadzone_wz_);
    deadzone_wz_neg_ = declare_parameter<double>("deadzone_wz_negative", deadzone_wz_);
    min_effective_vx_pos_ = declare_parameter<double>("min_effective_vx_positive", min_effective_vx_);
    min_effective_vx_neg_ = declare_parameter<double>("min_effective_vx_negative", min_effective_vx_);
    min_effective_vy_pos_ = declare_parameter<double>("min_effective_vy_positive", min_effective_vy_);
    min_effective_vy_neg_ = declare_parameter<double>("min_effective_vy_negative", min_effective_vy_);
    min_effective_wz_pos_ = declare_parameter<double>("min_effective_wz_positive", min_effective_wz_);
    min_effective_wz_neg_ = declare_parameter<double>("min_effective_wz_negative", min_effective_wz_);
    publish_compensated_ = declare_parameter<bool>("publish_compensated", true);

    if (!deploy_config_file_.empty()) {
      load_velocity_limits_from_yaml(deploy_config_file_);
    }

    setup_socket();
    setup_subscribers();

    RCLCPP_INFO(get_logger(),
                "cmd_vel_udp_bridge: topic=%s ip=%s port=%d mode=%d",
                cmd_vel_topic_.c_str(), udp_ip_.c_str(), udp_port_, mode_);
    legged_bringup::mission_log::publish(
      *this, "cmd_vel_udp_bridge", "UDP_BRIDGE_STARTED", "INFO",
      "订阅话题=" + cmd_vel_topic_ + " UDP目标=" + udp_ip_ + ":" + std::to_string(udp_port_) +
      " 模式=" + std::to_string(mode_));
    RCLCPP_INFO(get_logger(),
                "limits: vx[%.2f, %.2f] vy[%.2f, %.2f] yaw[%.2f, %.2f]",
                cmd_vx_min_, cmd_vx_max_, cmd_vy_min_, cmd_vy_max_,
                cmd_yaw_min_, cmd_yaw_max_);
    RCLCPP_INFO(get_logger(),
                "deadzone_compensation: vx(dz_pos=%.3f dz_neg=%.3f min_pos=%.3f min_neg=%.3f) "
                "vy(dz_pos=%.3f dz_neg=%.3f min_pos=%.3f min_neg=%.3f) "
                "wz(dz_pos=%.3f dz_neg=%.3f min_pos=%.3f min_neg=%.3f)",
                deadzone_vx_pos_, deadzone_vx_neg_, min_effective_vx_pos_, min_effective_vx_neg_,
                deadzone_vy_pos_, deadzone_vy_neg_, min_effective_vy_pos_, min_effective_vy_neg_,
                deadzone_wz_pos_, deadzone_wz_neg_, min_effective_wz_pos_, min_effective_wz_neg_);
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

    // 发布补偿后的速度，方便观测死区补偿是否生效
    compensated_pub_ = create_publisher<geometry_msgs::msg::Twist>("cmd_vel_compensated", 10);

    if (!estop_topic_.empty()) {
      estop_sub_ = create_subscription<std_msgs::msg::Bool>(
          estop_topic_, rclcpp::QoS(10),
          [this](const std_msgs::msg::Bool::SharedPtr msg) {
            estop_latched_ = msg->data;
          });
    }
  }

  // 死区补偿（对称版本）：将低于死区阈值的非零速度提升到最小有效速度
  // 这样可以避免"控制器输出了小速度 → 机器人不动 → 误差不减小 → 控制器继续输出小速度"的死循环
  double apply_deadzone_compensation(double value, double deadzone, double min_effective) {
    if (value == 0.0) {
      return 0.0;  // 保持零速度
    }
    double abs_v = std::fabs(value);
    if (abs_v < deadzone) {
      // 在死区内：提升到最小有效速度，保持方向
      double boosted = std::copysign(min_effective, value);
      RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000,
                            "Deadzone compensation: %.4f -> %.4f (deadzone=%.3f, min_eff=%.3f)",
                            value, boosted, deadzone, min_effective);
      return boosted;
    }
    return value;  // 高于死区，保持不变
  }

  // 死区补偿（非对称版本）：正负方向使用独立的死区和最小有效速度
  double apply_deadzone_compensation_asymmetric(double value,
                                                double deadzone_pos, double deadzone_neg,
                                                double min_effective_pos, double min_effective_neg) {
    if (value == 0.0) {
      return 0.0;
    }
    if (value > 0.0) {
      if (value < deadzone_pos) {
        double boosted = min_effective_pos;
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000,
                              "Deadzone compensation (+): %.4f -> %.4f (dz_pos=%.3f, min_eff_pos=%.3f)",
                              value, boosted, deadzone_pos, min_effective_pos);
        return boosted;
      }
    } else {
      if (value > -deadzone_neg) {
        double boosted = -min_effective_neg;
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000,
                              "Deadzone compensation (-): %.4f -> %.4f (dz_neg=%.3f, min_eff_neg=%.3f)",
                              value, boosted, deadzone_neg, min_effective_neg);
        return boosted;
      }
    }
    return value;
  }

  void handle_twist(const geometry_msgs::msg::Twist &msg) {
    UdpCommand cmd;
    cmd.mode = mode_;
    cmd.e_stop = estop_latched_ ? 1 : 0;

    // 先应用死区补偿，再转换为比例值
    // vx 使用非对称死区（正负方向独立设置）
    double vx_compensated = apply_deadzone_compensation_asymmetric(
        msg.linear.x,
        deadzone_vx_pos_, deadzone_vx_neg_,
        min_effective_vx_pos_, min_effective_vx_neg_);
    double vy_compensated = apply_deadzone_compensation_asymmetric(
        msg.linear.y,
        deadzone_vy_pos_, deadzone_vy_neg_,
        min_effective_vy_pos_, min_effective_vy_neg_);
    // 暂时关闭 wz 死区补偿，原样转发 angular.z
    double wz_compensated = apply_deadzone_compensation(msg.angular.z, deadzone_wz_, min_effective_wz_);
    // double wz_compensated = msg.angular.z;

    // 发布补偿后的速度供观测
    if (publish_compensated_) {
      auto comp_msg = std::make_unique<geometry_msgs::msg::Twist>();
      comp_msg->linear.x = vx_compensated;
      comp_msg->linear.y = vy_compensated;
      comp_msg->angular.z = wz_compensated;
      compensated_pub_->publish(std::move(comp_msg));
    }

    cmd.vx = static_cast<float>(scale_ratio(vx_compensated, cmd_vx_min_, cmd_vx_max_));
    cmd.vy = static_cast<float>(scale_ratio(vy_compensated, cmd_vy_min_, cmd_vy_max_));
    cmd.yaw = static_cast<float>(scale_ratio(wz_compensated, cmd_yaw_min_, cmd_yaw_max_));

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

  // 死区补偿参数
  double deadzone_vx_ = 1.8;
  double deadzone_vy_ = 0.80;
  double deadzone_wz_ = 0.09;
  double min_effective_vx_ = 1.8;
  double min_effective_vy_ = 0.80;
  double min_effective_wz_ = 0.09;
  // 非对称死区（正负方向独立）
  double deadzone_vx_pos_ = 1.8;
  double deadzone_vx_neg_ = 1.8;
  double deadzone_vy_pos_ = 0.80;
  double deadzone_vy_neg_ = 0.80;
  double deadzone_wz_pos_ = 0.09;
  double deadzone_wz_neg_ = 0.09;
  double min_effective_vx_pos_ = 1.8;
  double min_effective_vx_neg_ = 1.8;
  double min_effective_vy_pos_ = 0.80;
  double min_effective_vy_neg_ = 0.80;
  double min_effective_wz_pos_ = 0.09;
  double min_effective_wz_neg_ = 0.09;
  bool publish_compensated_ = true;

  // 补偿后速度发布者
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr compensated_pub_;

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
