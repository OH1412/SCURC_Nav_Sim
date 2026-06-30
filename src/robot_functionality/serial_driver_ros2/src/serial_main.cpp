#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/point.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "std_msgs/msg/u_int8_multi_array.hpp"
#include "serial_driver/serial_comm.hpp"
#include "serial_driver/protocol_defs.hpp"
#include <cmath>

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
        comm_ = std::make_unique<SerialComm>(port, baudrate);

        // ====================================================================
        // 订阅者
        // ====================================================================

        // /arm_target -> 机械臂目标坐标 (geometry_msgs/msg/Point, 单位: mm)
        // 协议帧: FD FD 07 ctrl X_L X_H Y_L Y_H Z_L Z_H CHECKSUM (int16 mm, 小端序)
        sub_arm_target_ = this->create_subscription<geometry_msgs::msg::Point>(
            "/arm_target", 10,
            std::bind(&SerialCmdSender::armTargetCallback, this, _1));

        // /arm_command -> 机械臂指令 (Float64MultiArray, 格式: [x, y, z, yaw, action])
        // action: 1=Pick(0x01), 2=Place(0x02)
        sub_arm_command_ = this->create_subscription<std_msgs::msg::Float64MultiArray>(
            "/arm_command", 10,
            std::bind(&SerialCmdSender::armCommandCallback, this, _1));

        // ====================================================================
        // 发布者
        // ====================================================================

        // /arm_status -> ACK 状态 [state, result]
        arm_status_pub_ = this->create_publisher<std_msgs::msg::UInt8MultiArray>(
            "/arm_status", 10);

        // ====================================================================
        // ACK 轮询定时器 (10 Hz)
        // ====================================================================
        ack_poll_timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100),
            std::bind(&SerialCmdSender::ackPollCallback, this));

        RCLCPP_INFO(this->get_logger(),
            "Serial ready. Listening on /arm_target, /arm_command | "
            "Publishing ACK on /arm_status @ 10Hz");
    }

private:
    // ========================================================================
    // 机械臂目标坐标回调 (Point, 单位: mm)
    // 使用 default_control_ 作为控制位
    // ========================================================================
    void armTargetCallback(const geometry_msgs::msg::Point::SharedPtr msg)
    {
        int16_t x_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->x, -32768.0, 32767.0)));
        int16_t y_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->y, -32768.0, 32767.0)));
        int16_t z_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->z, -32768.0, 32767.0)));

        RCLCPP_INFO(this->get_logger(),
            "[ARM] /arm_target received: (%d, %d, %d) mm | control=0x%02X",
            x_mm, y_mm, z_mm, default_control_);

        bool success = comm_->sendArmTargetCommand(
            default_control_, x_mm, y_mm, z_mm, arm_checksum_offset_);
        if (!success) {
            RCLCPP_WARN(this->get_logger(), "Send Error (arm_target)");
        }
    }

    // ========================================================================
    // 机械臂指令回调 (Float64MultiArray, 来自 arm_control_server.py)
    // 格式: [x, y, z, yaw, action]
    //   x, y, z: arm_base 坐标 (米)
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
            std::round(std::clamp(msg->data[0] * 1000.0, -32768.0, 32767.0)));
        int16_t y_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->data[1] * 1000.0, -32768.0, 32767.0)));
        int16_t z_mm = static_cast<int16_t>(
            std::round(std::clamp(msg->data[2] * 1000.0, -32768.0, 32767.0)));

        RCLCPP_INFO(this->get_logger(),
            "[ARM] /arm_command: base_link=(%.3f, %.3f, %.3f)m → (%d, %d, %d)mm | control=0x%02X",
            msg->data[0], msg->data[1], msg->data[2],
            x_mm, y_mm, z_mm, control);

        bool success = comm_->sendArmTargetCommand(
            control, x_mm, y_mm, z_mm, arm_checksum_offset_);
        if (!success) {
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

            const char* state_str = (ack.state == protocol::ARM_CTRL_PICK)  ? "PICK" :
                                    (ack.state == protocol::ARM_CTRL_PLACE) ? "PLACE" : "?";
            const char* result_str = (ack.result == protocol::ARM_ACK_OK)   ? "OK" :
                                     (ack.result == protocol::ARM_ACK_FAIL) ? "FAIL" : "?";

            RCLCPP_INFO(this->get_logger(),
                "[ARM STATUS] Published: state=0x%02X(%s) result=0x%02X(%s)",
                ack.state, state_str, ack.result, result_str);

            arm_status_pub_->publish(msg);
        }
    }

    // ------------------------------------------------------------------
    // 成员变量
    // ------------------------------------------------------------------
    int arm_checksum_offset_;
    uint8_t default_control_;
    rclcpp::Subscription<geometry_msgs::msg::Point>::SharedPtr sub_arm_target_;
    rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr sub_arm_command_;
    rclcpp::Publisher<std_msgs::msg::UInt8MultiArray>::SharedPtr arm_status_pub_;
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
