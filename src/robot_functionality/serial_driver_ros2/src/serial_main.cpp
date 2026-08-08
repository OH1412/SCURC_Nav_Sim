#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "std_msgs/msg/u_int8_multi_array.hpp"
#include "serial_driver/serial_comm.hpp"
#include "serial_driver/protocol_defs.hpp"
#include "legged_bringup/mission_log.hpp"
#include <cmath>
#include <sstream>

using std::placeholders::_1;

class SerialCmdSender : public rclcpp::Node
{
public:
    SerialCmdSender() : Node("serial_cmd_sender")
    {
        // 声明参数
        this->declare_parameter<std::string>("port", "/dev/ttyUSB2");
        this->declare_parameter<int>("baudrate", 115200);
        this->declare_parameter<int>("arm_checksum_offset", 0);
        this->declare_parameter<int>("default_control", 0x01);  // 默认 Pick

        // 获取参数
        std::string port = this->get_parameter("port").as_string();
        int baudrate = this->get_parameter("baudrate").as_int();
        arm_checksum_offset_ = this->get_parameter("arm_checksum_offset").as_int();
        default_control_ = static_cast<uint8_t>(
            this->get_parameter("default_control").as_int());
        RCLCPP_INFO(this->get_logger(),
            "Arm checksum offset: %d (0=standard) | default_control: 0x%02X (%s)",
            arm_checksum_offset_, default_control_,
            default_control_ == protocol::ARM_CTRL_PICK  ? "PICK" :
            default_control_ == protocol::ARM_CTRL_PLACE ? "PLACE" : "UNKNOWN");

        // 初始化串口通信类
        comm_ = std::make_unique<SerialComm>(port, baudrate, this);

        legged_bringup::mission_log::publish(
            *this, "serial_cmd_sender", "SERIAL_READY",
            "INFO", "监听话题=/arm_command 发布话题=/arm_status /arm_serial_ack");

        // ====================================================================
        // 订阅者
        // ====================================================================

        // /arm_command -> 机械臂指令 (Float64MultiArray, 格式: [x, y, z, yaw, action])
        // x, y, z: arm_base 坐标 (mm); action: 1=Pick(0x01), 2=Place(0x02)
        sub_arm_command_ = this->create_subscription<std_msgs::msg::Float64MultiArray>(
            "/arm_command", 10,
            std::bind(&SerialCmdSender::armCommandCallback, this, _1));

        // ====================================================================
        // 发布者
        // ====================================================================

        // /arm_status -> 机械臂行为ACK [state, result] (state=0x01 Pick / 0x02 Place)
        arm_status_pub_ = this->create_publisher<std_msgs::msg::UInt8MultiArray>(
            "/arm_status", 10);

        // /arm_serial_ack -> 串口接收确认 (state=0x03 Serial Done → 停止重发)
        arm_serial_ack_pub_ = this->create_publisher<std_msgs::msg::UInt8MultiArray>(
            "/arm_serial_ack", 10);

        // ====================================================================
        // ACK 轮询定时器 (10 Hz)
        // ====================================================================
        ack_poll_timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100),
            std::bind(&SerialCmdSender::ackPollCallback, this));

        RCLCPP_INFO(this->get_logger(),
            "Serial ready. Listening on /arm_command | "
            "Publishing: /arm_status (行为ACK) /arm_serial_ack (串口ACK) @ 10Hz");
    }

private:
    // ========================================================================
    // 机械臂指令回调 (Float64MultiArray)
    // 格式: [x, y, z, yaw, action]
    //   x, y, z: arm_base 坐标 (mm)
    //   action: 1→0x01(Pick), 2→0x02(Place)
    // ========================================================================
    void armCommandCallback(const std_msgs::msg::Float64MultiArray::SharedPtr msg)
    {
        if (msg->data.size() < 3) {
            RCLCPP_WARN(this->get_logger(),
                "arm_command array has <3 elements, ignoring");
            return;
        }

        // 控制位: 从 data[4] 获取 action (若数组长度足够)
        uint8_t control = default_control_;
        if (msg->data.size() >= 5) {
            int action = static_cast<int>(std::round(msg->data[4]));
            if (action == 2) {
                control = protocol::ARM_CTRL_PLACE;  // 0x02
            } else {
                control = protocol::ARM_CTRL_PICK;   // 0x01 (default)
            }
        }

        int16_t x_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->data[0], -32768.0, 32767.0)));
        int16_t y_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->data[1], -32768.0, 32767.0)));
        int16_t z_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->data[2], -32768.0, 32767.0)));

        RCLCPP_INFO(this->get_logger(),
            "[ARM] /arm_command: (%.1f, %.1f, %.1f) mm → (%d, %d, %d) mm | control=0x%02X",
            msg->data[0], msg->data[1], msg->data[2],
            x_mm, y_mm, z_mm, control);

        std::ostringstream detail;
        detail << "输入(mm)=(" << msg->data[0] << ',' << msg->data[1] << ',' << msg->data[2]
               << ") 输出(mm)=(" << x_mm << ',' << y_mm << ',' << z_mm
               << ") 控制字节=0x" << std::hex << static_cast<int>(control) << std::dec;
        legged_bringup::mission_log::publish(
            *this, "serial_cmd_sender", "ARM_COMMAND_RECEIVED", "INFO", detail.str());

        bool success = comm_->sendArmTargetCommand(
            control, x_mm, y_mm, z_mm, arm_checksum_offset_);
        if (!success) {
            legged_bringup::mission_log::publish(
                *this, "serial_cmd_sender", "ARM_COMMAND_SEND_FAILED", "ERROR",
                detail.str());
            RCLCPP_WARN(this->get_logger(), "Send Error (arm_command)");
        }
    }

    // ========================================================================
    // ACK 轮询回调 (10Hz)
    // 非阻塞读取串口缓冲区，解析 FE FE 03 state result CHECKSUM 帧
    // 发布到 /arm_status
    // ========================================================================
    void ackPollCallback()
    {
        ArmAck ack = comm_->readArmAck();
        if (ack.valid) {
            auto msg = std_msgs::msg::UInt8MultiArray();
            msg.data = {ack.state, ack.result};

            // state=0x03: 串口接收完成 → 发布到 /arm_serial_ack（通知BT停止重发）
            // state=0x01/0x02: 机械臂动作完成 → 发布到 /arm_status
            if (ack.state == 0x03) {
                const char* result_cn = (ack.result == protocol::ARM_ACK_OK) ? "成功" :
                                        (ack.result == protocol::ARM_ACK_FAIL) ? "失败" : "未知";
                std::ostringstream detail;
                detail << "串口接收完成 结果=0x" << std::hex
                       << static_cast<int>(ack.result) << std::dec << '(' << result_cn << ')';
                legged_bringup::mission_log::publish(
                    *this, "serial_cmd_sender", "ARM_SERIAL_ACK_PUBLISHED", "INFO", detail.str());

                arm_serial_ack_pub_->publish(msg);
                RCLCPP_INFO(this->get_logger(),
                    "[ARM SERIAL ACK] state=0x03(Serial Done) result=0x%02X(%s)",
                    ack.result, result_cn);
            } else {
                const char* state_cn = (ack.state == protocol::ARM_CTRL_PICK) ? "抓取" :
                                       (ack.state == protocol::ARM_CTRL_PLACE) ? "放置" : "未知";
                const char* result_cn = (ack.result == protocol::ARM_ACK_OK) ? "成功" :
                                        (ack.result == protocol::ARM_ACK_FAIL) ? "失败" : "未知";

                std::ostringstream detail;
                detail << "状态=0x" << std::hex << static_cast<int>(ack.state) << std::dec
                       << '(' << state_cn << ") 结果=0x" << std::hex
                       << static_cast<int>(ack.result) << std::dec << '(' << result_cn << ')';
                legged_bringup::mission_log::publish(
                    *this, "serial_cmd_sender", "ARM_STATUS_PUBLISHED", "INFO", detail.str());

                arm_status_pub_->publish(msg);
            }
        }
    }

    // ------------------------------------------------------------------
    // 成员变量
    // ------------------------------------------------------------------
    int arm_checksum_offset_;
    uint8_t default_control_;
    rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr sub_arm_command_;
    rclcpp::Publisher<std_msgs::msg::UInt8MultiArray>::SharedPtr arm_status_pub_;
    rclcpp::Publisher<std_msgs::msg::UInt8MultiArray>::SharedPtr arm_serial_ack_pub_;
    rclcpp::TimerBase::SharedPtr ack_poll_timer_;
    std::unique_ptr<SerialComm> comm_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SerialCmdSender>());
    rclcpp::shutdown();
    return 0;
}
