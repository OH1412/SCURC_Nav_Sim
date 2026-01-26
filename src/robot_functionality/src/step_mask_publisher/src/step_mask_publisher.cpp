#include "step_mask_publisher/step_mask_publisher.hpp"
#include <chrono>
#include <fstream>
#include <filesystem>

using namespace std::chrono_literals;

namespace step_mask_publisher
{

StepMaskPublisher::StepMaskPublisher(const rclcpp::NodeOptions & options)
: Node("step_mask_publisher", options),
  mask_yaml_path_(""),
  publish_rate_(1.0),
  frame_id_("map"),
  debug_mode_(false)
{
  // 声明参数
  this->declare_parameter<std::string>("mask_yaml", mask_yaml_path_);
  this->declare_parameter<double>("publish_rate", publish_rate_);
  this->declare_parameter<std::string>("frame_id", frame_id_);
  this->declare_parameter<bool>("debug", debug_mode_);
  
  // 获取参数
  this->get_parameter("mask_yaml", mask_yaml_path_);
  this->get_parameter("publish_rate", publish_rate_);
  this->get_parameter("frame_id", frame_id_);
  this->get_parameter("debug", debug_mode_);
  
  // 参数验证
  if (mask_yaml_path_.empty()) {
    RCLCPP_ERROR(this->get_logger(), "参数 mask_yaml 不能为空!");
    throw std::runtime_error("mask_yaml 参数未设置");
  }
  
  RCLCPP_INFO(this->get_logger(), "台阶掩码发布器初始化");
  RCLCPP_INFO(this->get_logger(), "掩码文件: %s", mask_yaml_path_.c_str());
  RCLCPP_INFO(this->get_logger(), "发布频率: %.1f Hz", publish_rate_);
  RCLCPP_INFO(this->get_logger(), "坐标系: %s", frame_id_.c_str());
  
  // 加载掩码图
  try {
    loadMask();
  } catch (const std::exception & e) {
    RCLCPP_FATAL(this->get_logger(), "加载掩码图失败: %s", e.what());
    throw;
  }
  
  // 创建发布器 (QoS: 保持最后1条，持久化)
  publisher_ = this->create_publisher<nav_msgs::msg::OccupancyGrid>(
    "/step_mask",
    rclcpp::QoS(1).transient_local().reliable());
  
  // 创建定时器
  auto period = std::chrono::duration<double>(1.0 / publish_rate_);
  timer_ = this->create_wall_timer(
    period, std::bind(&StepMaskPublisher::timerCallback, this));
    
  RCLCPP_INFO(this->get_logger(), "台阶掩码发布器启动成功，话题: /step_mask");
}

void StepMaskPublisher::loadMask()
{
  RCLCPP_INFO(this->get_logger(), "正在加载掩码图...");
  
  // 检查文件是否存在
  if (!std::filesystem::exists(mask_yaml_path_)) {
    throw std::runtime_error("YAML文件不存在: " + mask_yaml_path_);
  }
  
  // 读取YAML文件
  YAML::Node config;
  try {
    config = YAML::LoadFile(mask_yaml_path_);
  } catch (const YAML::Exception & e) {
    throw std::runtime_error("YAML解析失败: " + std::string(e.what()));
  }
  
  // 获取必需参数
  if (!config["image"]) {
    throw std::runtime_error("YAML文件中缺少 'image' 字段");
  }
  
  if (!config["resolution"]) {
    throw std::runtime_error("YAML文件中缺少 'resolution' 字段");
  }
  
  std::string image_file = config["image"].as<std::string>();
  float resolution = config["resolution"].as<float>();
  
  // 构建PGM文件完整路径
  std::filesystem::path yaml_path(mask_yaml_path_);
  std::filesystem::path pgm_path = yaml_path.parent_path() / image_file;
  
  RCLCPP_DEBUG(this->get_logger(), "PGM文件路径: %s", pgm_path.string().c_str());
  
  // 检查PGM文件是否存在
  if (!std::filesystem::exists(pgm_path)) {
    throw std::runtime_error("PGM文件不存在: " + pgm_path.string());
  }
  
  // 使用OpenCV读取PGM文件
  cv::Mat mask_image = cv::imread(pgm_path.string(), cv::IMREAD_GRAYSCALE);
  if (mask_image.empty()) {
    throw std::runtime_error("无法读取PGM图像文件: " + pgm_path.string());
  }
  
  // 设置消息头
  mask_msg_.header.frame_id = frame_id_;
  
  // 设置地图信息
  mask_msg_.info.resolution = resolution;
  mask_msg_.info.width = mask_image.cols;
  mask_msg_.info.height = mask_image.rows;
  
  // 设置原点
  if (config["origin"]) {
    auto origin = config["origin"].as<std::vector<double>>();
    if (origin.size() >= 2) {
      mask_msg_.info.origin.position.x = origin[0];
      mask_msg_.info.origin.position.y = origin[1];
    }
  }
  
  // 设置默认方向
  mask_msg_.info.origin.position.z = 0.0;
  mask_msg_.info.origin.orientation.x = 0.0;
  mask_msg_.info.origin.orientation.y = 0.0;
  mask_msg_.info.origin.orientation.z = 0.0;
  mask_msg_.info.origin.orientation.w = 1.0;
  
  // 判断是否反转像素值
  int negate = 0;
  if (config["negate"]) {
    negate = config["negate"].as<int>();
  }
  
  // 转换像素数据：PGM(0-255) → OccupancyGrid(0-100)
  int total_pixels = mask_image.rows * mask_image.cols;
  mask_msg_.data.resize(total_pixels);
  
  const uint8_t* src_data = mask_image.data;
  int8_t* dst_data = mask_msg_.data.data();
  
  for (int i = 0; i < total_pixels; ++i) {
    int pixel_value = src_data[i];
    
    if (negate == 1) {
      pixel_value = 255 - pixel_value;
    }
    
    // 线性映射：0-255 → 0-100
    dst_data[i] = static_cast<int8_t>((pixel_value * 100) / 255);
  }
  
  // 统计信息
  int white_pixels = 0, black_pixels = 0;
  for (int i = 0; i < total_pixels; ++i) {
    int8_t val = dst_data[i];
    if (val > 70) white_pixels++;      // 高值认为是台阶区域
    else if (val < 30) black_pixels++;  // 低值认为是自由区域
  }
  
  RCLCPP_INFO(this->get_logger(), "掩码图加载成功:");
  RCLCPP_INFO(this->get_logger(), "  尺寸: %d x %d 像素", mask_image.cols, mask_image.rows);
  RCLCPP_INFO(this->get_logger(), "  分辨率: %.3f 米/像素", resolution);
  RCLCPP_INFO(this->get_logger(), "  台阶区域(>70): %d 像素 (%.1f%%)", 
              white_pixels, 100.0 * white_pixels / total_pixels);
  RCLCPP_INFO(this->get_logger(), "  自由区域(<30): %d 像素 (%.1f%%)", 
              black_pixels, 100.0 * black_pixels / total_pixels);
}

void StepMaskPublisher::timerCallback()
{
  publishMask();
}

void StepMaskPublisher::publishMask()
{
  mask_msg_.header.stamp = this->now();
  publisher_->publish(mask_msg_);
  
  static size_t publish_count = 0;
  publish_count++;
  
  if (debug_mode_ && (publish_count % 100 == 0)) {
    RCLCPP_DEBUG(this->get_logger(), "已发布 %zu 次掩码图", publish_count);
  }
}

}  // namespace step_mask_publisher

// 组件注册
#include "rclcpp_components/register_node_macro.hpp"
RCLCPP_COMPONENTS_REGISTER_NODE(step_mask_publisher::StepMaskPublisher)
