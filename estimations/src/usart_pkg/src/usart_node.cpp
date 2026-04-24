#include "usart_pkg/usart_node.hpp"

namespace usart_pkg
{

UsartNode::UsartNode()
: Node("usart_node")
{
  // 声明并获取参数
  this->declare_parameter("port", "/dev/ttyACM0");      // USB串口默认路径

  std::string port_name = this->get_parameter("port").as_string();

  try {
    serial_port_.Open(port_name);
    
    serial_port_.SetBaudRate(LibSerial::BaudRate::BAUD_115200);     // 设置波特率
    serial_port_.SetCharacterSize(LibSerial::CharacterSize::CHAR_SIZE_8);
    serial_port_.SetStopBits(LibSerial::StopBits::STOP_BITS_1);
    serial_port_.SetParity(LibSerial::Parity::PARITY_NONE);
    RCLCPP_INFO(this->get_logger(), "Successfully opened serial port: %s", port_name.c_str());
  } catch (const std::exception &e) {
    RCLCPP_ERROR(this->get_logger(), "Failed to open serial port: %s, Error: %s", port_name.c_str(), e.what());
  }

  // 订阅雷达发来的话题，目前假设话题名称为 "cmd_action"，消息类型为 usart_pkg::msg::Action，需要根据实际情况修改
  subscription_ = this->create_subscription<usart_pkg::msg::Action>(
    "/dog_step_cmd", 10, std::bind(&UsartNode::action_callback, this, std::placeholders::_1));
  
  // 发布DOG状态的话题，假设话题名称是dog_status，消息类型为 usart_pkg::msg::Status
  status_publisher_ = this->create_publisher<std_msgs::msg::Bool>("/dog_status/is_stepping", 10);

  // 增加：定时器读取串口接收缓冲区 (20ms 频率)
  receive_timer_ = this->create_wall_timer(
    std::chrono::milliseconds(20), std::bind(&UsartNode::receive_serial_data, this));

  RCLCPP_INFO(this->get_logger(), "Usart Node initialized. Listening on topic 'cmd_action' and reporting state.");
}

UsartNode::~UsartNode() {
  if (serial_port_.IsOpen()) {
    serial_port_.Close();
  }
}

void UsartNode::receive_serial_data() {
  if (!serial_port_.IsOpen() || serial_port_.GetNumberOfBytesAvailable() == 0) {
    return;
  }

  try {
    while (serial_port_.GetNumberOfBytesAvailable() > 0) {
      uint8_t byte;
      serial_port_.ReadByte(byte, 1); // 逐字节读取

      if (rx_buffer_.empty()) {
        if (byte == 0x55) rx_buffer_.push_back(byte); // 找帧头1
      } else if (rx_buffer_.size() == 1) {
        if (byte == 0xAA) rx_buffer_.push_back(byte); // 找帧头2
        else rx_buffer_.clear(); // 没对上，重置
      } else {
        rx_buffer_.push_back(byte); // 填充后续字节
        
        // 凑齐一帧 (7 字节) 开始校验
        if (rx_buffer_.size() == 7) {
          if (rx_buffer_[5] == 0x0D && rx_buffer_[6] == 0x0A) { // 检查帧尾
            uint8_t action_or_status = rx_buffer_[2];
            uint8_t speed_or_reserve = rx_buffer_[3];
            uint8_t checksum = static_cast<uint8_t>((action_or_status + speed_or_reserve) % 256);

            if (checksum == rx_buffer_[4]) {
              // 注意：你需要根据你的底层单片机协议来修改这个判断条件！
              // 假设底层发来 0 表示处于站立/空闲状态，其他数字表示正在执行步态
           if (action_or_status == 0xAA || action_or_status == 0xFF) {
                
                auto status_msg = std_msgs::msg::Bool();
                
                if (action_or_status == 0xAA) { 
                  status_msg.data = true;    // true: 未完成一个周期，锁住状态


                } else if (action_or_status == 0xFF) {
                  status_msg.data = false;   // false: 动作已完成，释放锁，可以接新指令
                  RCLCPP_INFO(this->get_logger(), "收到底层反馈: 0xFF (动作已完成，系统释放)");
                }
                
                // 只有收到明确的 AA 或 FF 时，才发布状态
                status_publisher_->publish(status_msg);  

              } else {
                // 如果收到其他的未知数据（比如 0x00），直接忽略，防止上层逻辑混乱
                // 你也可以在这里加一句打印，方便后期调试硬件：
                RCLCPP_DEBUG(this->get_logger(), "收到未知的底层状态码: 0x%02X", action_or_status);
              }
                                                                                                                                 
            }
          }
          rx_buffer_.clear(); // 处理完毕或帧尾校验失败，清空缓冲区
        }
      }
    }
  } catch (...) { }
}

void UsartNode::action_callback(const usart_pkg::msg::Action::SharedPtr msg)
{
  RCLCPP_INFO(this->get_logger(), "Received action request: ID=%d, Speed=%d", 
              msg->action_id, msg->speed_level);
  
  send_serial_data(msg->action_id, msg->speed_level);
}

void UsartNode::send_serial_data(uint8_t action, uint8_t speed) {
  if (!serial_port_.IsOpen()) {
    return;
  }

  std::vector<uint8_t> frame;
  frame.push_back(0x55); 
  frame.push_back(0xAA); 
  frame.push_back(action);
  frame.push_back(speed);
  frame.push_back(static_cast<uint8_t>((action + speed) % 256));
  frame.push_back(0x0D);
  frame.push_back(0x0A);

  serial_port_.Write(frame);
  RCLCPP_INFO(this->get_logger(), "Sent frame: 55 AA %02X %02X %02X 0D 0A", action, speed, frame[4]);
}

}  // namespace usart_pkg

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<usart_pkg::UsartNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}