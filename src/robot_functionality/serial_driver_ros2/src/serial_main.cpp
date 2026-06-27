#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/point.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"
#include "serial_driver/serial_comm.hpp"
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

        // 获取参数
        std::string port = this->get_parameter("port").as_string();
        int baudrate = this->get_parameter("baudrate").as_int();
        arm_checksum_offset_ = this->get_parameter("arm_checksum_offset").as_int();
        RCLCPP_INFO(this->get_logger(),
            "Arm checksum offset: %d (0=algorithm standard)", arm_checksum_offset_);

        // 初始化串口通信类
        comm_ = std::make_unique<SerialComm>(port, baudrate);

        // 创建订阅者：/arm_target -> 机械臂目标坐标 (geometry_msgs/msg/Point, 单位: mm)
        // 协议帧: FD FD 06 X_L X_H Y_L Y_H Z_L Z_H CHECKSUM (int16 mm, 小端序)
        sub_arm_target_ = this->create_subscription<geometry_msgs::msg::Point>(
            "/arm_target", 10, std::bind(&SerialCmdSender::armTargetCallback, this, _1));

        // 创建订阅者：/arm_command -> 机械臂指令 (Float64MultiArray, 格式: [x, y, z, yaw, action])
        // 由 arm_control_server.py 发布，取前 3 个值作为 base_link 坐标
        sub_arm_command_ = this->create_subscription<std_msgs::msg::Float64MultiArray>(
            "/arm_command", 10, std::bind(&SerialCmdSender::armCommandCallback, this, _1));

        RCLCPP_INFO(this->get_logger(),
            "Serial ready for arm control. Listening on /arm_target and /arm_command");
    }

private:
    // ========================================================================
    // 机械臂目标坐标回调
    // 接收 geometry_msgs/msg/Point (单位: mm, base_link 坐标系)
    // 直接按协议帧 FD FD 06 X_L X_H Y_L Y_H Z_L Z_H CHECKSUM 发送
    // ========================================================================
    void armTargetCallback(const geometry_msgs::msg::Point::SharedPtr msg)
    {
        // Point 消息中的值已经是 mm（协议规定），直接转为 int16
        int16_t x_mm = static_cast<int16_t>(std::round(std::clamp(msg->x, -32768.0, 32767.0)));
        int16_t y_mm = static_cast<int16_t>(std::round(std::clamp(msg->y, -32768.0, 32767.0)));
        int16_t z_mm = static_cast<int16_t>(std::round(std::clamp(msg->z, -32768.0, 32767.0)));

        RCLCPP_INFO(this->get_logger(),
            "[ARM] /arm_target received: (%d, %d, %d) mm", x_mm, y_mm, z_mm);

        bool success = comm_->sendArmTargetCommand(x_mm, y_mm, z_mm, arm_checksum_offset_);
        if (!success)
        {
            RCLCPP_WARN(this->get_logger(), "Send Error (arm_target)");
        }
    }

    // ========================================================================
    // 机械臂指令回调 (来自 arm_control_server.py)
    // 接收 std_msgs/msg/Float64MultiArray (格式: [x, y, z, yaw, action])
    // 取前 3 个值 (base_link 坐标, 单位: 米) 转换为 mm 发送
    // ========================================================================
    void armCommandCallback(const std_msgs::msg::Float64MultiArray::SharedPtr msg)
    {
        if (msg->data.size() < 3)
        {
            RCLCPP_WARN(this->get_logger(), "arm_command 数组元素少于3个，忽略");
            return;
        }

        int16_t x_mm = static_cast<int16_t>(std::round(std::clamp(msg->data[0] * 1000.0, -32768.0, 32767.0)));
        int16_t y_mm = static_cast<int16_t>(std::round(std::clamp(msg->data[1] * 1000.0, -32768.0, 32767.0)));
        int16_t z_mm = static_cast<int16_t>(std::round(std::clamp(msg->data[2] * 1000.0, -32768.0, 32767.0)));

        RCLCPP_INFO(this->get_logger(),
            "[ARM] /arm_command received: base_link=(%.3f, %.3f, %.3f) m -> (%d, %d, %d) mm",
            msg->data[0], msg->data[1], msg->data[2], x_mm, y_mm, z_mm);

        bool success = comm_->sendArmTargetCommand(x_mm, y_mm, z_mm, arm_checksum_offset_);
        if (!success)
        {
            RCLCPP_WARN(this->get_logger(), "Send Error (arm_command)");
        }
    }

    int arm_checksum_offset_;
    rclcpp::Subscription<geometry_msgs::msg::Point>::SharedPtr sub_arm_target_;
    rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr sub_arm_command_;
    std::unique_ptr<SerialComm> comm_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SerialCmdSender>());
    rclcpp::shutdown();
    return 0;
}
