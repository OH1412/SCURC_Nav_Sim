#ifndef USART_PKG__USART_NODE_HPP_
#define USART_PKG__USART_NODE_HPP_

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "usart_pkg/msg/action.hpp" 
#include "std_msgs/msg/bool.hpp"
#include <libserial/SerialPort.h>

namespace usart_pkg
{

/**
 * 串口通信协议定义 (双向对称)
 * 帧头: 0x55 0xAA
 * 数据位1: (ROS->STM32: ActionID | STM32->ROS: Status)
 * 数据位2: (ROS->STM32: Speed    | STM32->ROS: Reserved)
 * 校验位: (数据1 + 数据2) % 256
 * 帧尾: 0x0D 0x0A
 */
class UsartNode : public rclcpp::Node
{
public:
  explicit UsartNode();
  virtual ~UsartNode();

private:
  /**
   * @brief 处理雷达指令请求
   */
  void action_callback(const usart_pkg::msg::Action::SharedPtr msg);

  /**
   * @brief 定时器任务：读取串口反馈
   */
  void receive_serial_data();

  /**
   * @brief 打包并发送串口数据
   */
  void send_serial_data(uint8_t action, uint8_t speed);

  LibSerial::SerialPort serial_port_;
  rclcpp::Subscription<usart_pkg::msg::Action>::SharedPtr subscription_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr status_publisher_;
  rclcpp::TimerBase::SharedPtr receive_timer_;

  // 串口接收相关变量
  std::vector<uint8_t> rx_buffer_;
};

}  // namespace usart_pkg

#endif  // USART_PKG__USART_NODE_HPP_