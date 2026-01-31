#pragma once

#include <memory>
#include <string>

#include <behaviortree_cpp_v3/action_node.h>
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

class DescendNode : public BT::StatefulActionNode
{
    public:
    DescendNode(
        const std::string & name,
        const BT::NodeConfiguration & config,
        std::shared_ptr<rclcpp::Node> node
    );

    static BT::PortsList providedPorts();

    BT::NodeStatus onStart() override;
    BT::NodeStatus onRunning() override;
    void onHalted() override;

    private:
    bool getCurrentZ(double & z_out);
    void publishZ(double z_vel);
    std::shared_ptr<rclcpp::Node> node_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr vel_pub_;
    std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
    std::string global_frame_{"map"};
    std::string robot_frame_{"base_link"};
    rclcpp::Time start_time_;
    double z_target_{0.0};
    double z_speed_{0.0};
    double max_duration_{0.0};
};