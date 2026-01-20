#include <memory>
#include <string>
#include <chrono>
#include <vector>
#include <sstream>
#include <rclcpp/rclcpp.hpp>
#include <behaviortree_cpp_v3/bt_factory.h>

// 必须在其他 fly_step_mission 头文件之前包含类型转换头文件
#include "fly_step_mission/bt_type_conversions.hpp"

#include "fly_step_mission/nav2_pose_node.hpp"
#include "fly_step_mission/ascend_node.hpp"
#include "fly_step_mission/descend_node.hpp"
#include "fly_step_mission/path_generator_node.hpp"
#include "fly_step_mission/dynamic_path_task_executor.hpp"

using namespace std::chrono_literals;
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  // 1. 创建 ROS2 节点
  auto node = std::make_shared<rclcpp::Node>("fly_step_bt_node");

  // 2. 从参数读取 BT XML 路径
  node->declare_parameter<std::string>("bt_xml_file", "");
  std::string bt_xml_file;
  node->get_parameter("bt_xml_file", bt_xml_file);

  // 读取 waypoints_file 参数（由 launch 提供）
  node->declare_parameter<std::string>("waypoints_file", "");
  std::string waypoints_file;
  node->get_parameter("waypoints_file", waypoints_file);

  if (bt_xml_file.empty()) {
    RCLCPP_ERROR(node->get_logger(),
      "Parameter 'bt_xml_file' is empty. Please set path to BT xml file.");
    return 1;
  }

  // 3. 创建 BT 工厂
  BT::BehaviorTreeFactory factory;


  // 注册 Deliberate set of nodes required by the two BTs
  // 3.x 注册 DynamicPathTaskExecutor
  BT::NodeBuilder dynamic_path_exec_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<fly_step_mission::DynamicPathTaskExecutor>(name, config, node);
    };
  factory.registerBuilder<fly_step_mission::DynamicPathTaskExecutor>("DynamicPathTaskExecutor", dynamic_path_exec_builder);

  // 注册 Nav2PoseNode
  BT::NodeBuilder nav2pose_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<Nav2PoseNode>(name, config, node);
    };
  factory.registerBuilder<Nav2PoseNode>("Nav2PoseNode", nav2pose_builder);

  // 注册 AscendNode
  BT::NodeBuilder ascend_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<AscendNode>(name, config, node);
    };
  factory.registerBuilder<AscendNode>("AscendNode", ascend_builder);

  // 注册 DescendNode
  BT::NodeBuilder descend_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<DescendNode>(name, config, node);
    };
  factory.registerBuilder<DescendNode>("DescendNode", descend_builder);

  // 注册 PathGeneratorNode
  BT::NodeBuilder path_gen_builder =
    [node](const std::string & name, const BT::NodeConfiguration & config)
    {
      return std::make_unique<fly_step_mission::PathGeneratorNode>(name, config, node);
    };
  factory.registerBuilder<fly_step_mission::PathGeneratorNode>("PathGeneratorNode", path_gen_builder);

  // 4. 将 waypoints_file 放入黑板并从 XML 创建行为树（使 BT 节点可以使用 {waypoints_file} 引用）
  BT::Blackboard::Ptr blackboard = BT::Blackboard::create();
  if (!waypoints_file.empty()) {
    blackboard->set<std::string>("waypoints_file", waypoints_file);
    RCLCPP_INFO(node->get_logger(), "Using waypoints_file from parameter: %s", waypoints_file.c_str());
  } else {
    RCLCPP_WARN(node->get_logger(), "Parameter 'waypoints_file' is empty; BT nodes will use their default path if any");
  }

  // create tree with injected blackboard
  BT::Tree tree = factory.createTreeFromFile(bt_xml_file, blackboard);
  RCLCPP_INFO(node->get_logger(), "Loaded BT xml: %s", bt_xml_file.c_str());

  rclcpp::Rate rate(10.0);  // 10 Hz tick

  // 5. 主循环：tick 行为树 + 处理 ROS 回调
  while (rclcpp::ok()) {
    auto status = tree.tickRoot();

    if (status == BT::NodeStatus::SUCCESS) {
      RCLCPP_INFO(node->get_logger(), "BT finished with SUCCESS, exit");
      break;
    } else if (status == BT::NodeStatus::FAILURE) {
      RCLCPP_WARN(node->get_logger(), "BT finished with FAILURE, exit");
      break;
    }

    rclcpp::spin_some(node);
    rate.sleep();
  }

  rclcpp::shutdown();
  return 0;
}