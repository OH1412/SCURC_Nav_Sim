#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
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
        this->declare_parameter<std::string>("port", "/dev/ttyUSB0");
        this->declare_parameter<int>("baudrate", 115200);

        // 获取参数
        std::string port = this->get_parameter("port").as_string();
        int baudrate = this->get_parameter("baudrate").as_int();

        // 初始化串口通信类
        comm_ = std::make_unique<SerialComm>(port, baudrate);

        // 创建订阅者：/cmd_vel
        sub_cmd_vel_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10, std::bind(&SerialCmdSender::cmdVelCallback, this, _1));

        // 创建订阅者：/LIVO2/pose_offset -> 发送 [x, y, yaw]
        sub_pose_offset_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
            "/LIVO2/pose_offset", 10, std::bind(&SerialCmdSender::poseOffsetCallback, this, _1));

        // 创建订阅者：/LIVO2/specific_distances -> 发送两个距离数据
        sub_specific_distances_ = this->create_subscription<std_msgs::msg::Float64MultiArray>(
            "/LIVO2/specific_distances", 10, std::bind(&SerialCmdSender::specificDistancesCallback, this, _1));
      
    }

private:
    // 从四元数计算偏航角（Z 轴），返回弧度
    static float quatToYaw(const geometry_msgs::msg::Quaternion &q)
    {
        // yaw (Z) = atan2(2(w*z + x*y), 1 - 2(y*y + z*z))
        const double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
        const double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
        return static_cast<float>(std::atan2(siny_cosp, cosy_cosp));
    }

    void cmdVelCallback(const geometry_msgs::msg::Twist::SharedPtr msg)
    {
        float vx = static_cast<float>(msg->linear.x);
        float vy = static_cast<float>(msg->linear.y);
        float wz = static_cast<float>(msg->angular.z);

    std::vector<float> speeds = {vx, vy, wz};
    // 使用命令 ID 0 表示速度命令（可根据需要调整）
    bool success = comm_->sendFloatArrayCommand(speeds, 0);
        if (!success)
        {
            RCLCPP_WARN(this->get_logger(), "Send Error (cmd_vel)");
        }
    }

    void poseOffsetCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
    {
        const float x = static_cast<float>(msg->pose.position.x);
        const float y = static_cast<float>(msg->pose.position.y);
        const float yaw = quatToYaw(msg->pose.orientation);

        std::vector<float> payload = {x, y, yaw};
        const bool ok = comm_->sendFloatArrayCommand(payload, 1); // 使用命令ID 0x02 代表 pose_offset
        if (!ok)
        {
            RCLCPP_WARN(this->get_logger(), "Send Error (pose_offset)");
        }
    }

    void specificDistancesCallback(const std_msgs::msg::Float64MultiArray::SharedPtr msg)
    {
        if (msg->data.size() < 2)
        {
            RCLCPP_WARN(this->get_logger(), "specific_distances数组元素少于2个");
            return;
        }

        // Float64MultiArray 中的 data 是 std::vector<double>
        // 需要显式转换为 float，注意精度损失
        float dist1 = static_cast<float>(msg->data[0]);
        float dist2 = static_cast<float>(msg->data[1]);

        std::vector<float> distances = {dist1, dist2};
        bool success = comm_->sendFloatArrayCommand(distances, 2); // 使用命令ID 0x02 代表 specific_distances
        if (!success)
        {
            RCLCPP_WARN(this->get_logger(), "Send Error (specific_distances)");
        }
    }

    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_vel_;
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr sub_pose_offset_;
    rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr sub_specific_distances_;
    std::unique_ptr<SerialComm> comm_;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SerialCmdSender>());
    rclcpp::shutdown();
    return 0;
}
