#ifndef STEP_MASK_PUBLISHER__STEP_MASK_PUBLISHER_HPP_
#define STEP_MASK_PUBLISHER__STEP_MASK_PUBLISHER_HPP_

#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <opencv2/opencv.hpp>
#include <yaml-cpp/yaml.h>
#include <memory>
#include <string>
#include <vector>

namespace step_mask_publisher
{

class StepMaskPublisher : public rclcpp::Node
{
public:
  explicit StepMaskPublisher(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
  
  virtual ~StepMaskPublisher() = default;

private:
  void loadMask();
  void timerCallback();
  void publishMask();
  
  // ROS2组件
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  
  // 消息
  nav_msgs::msg::OccupancyGrid mask_msg_;
  
  // 参数
  std::string mask_yaml_path_;
  double publish_rate_;
  std::string frame_id_;
  bool debug_mode_;
};

}  // namespace step_mask_publisher

#endif  // STEP_MASK_PUBLISHER__STEP_MASK_PUBLISHER_HPP_