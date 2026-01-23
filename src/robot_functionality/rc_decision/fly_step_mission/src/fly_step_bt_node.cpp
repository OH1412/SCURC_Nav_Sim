#include <memory>
#include <string>
#include <chrono>
#include <vector>
#include <sstream>
#include <mutex>
#include <thread>
#include <fstream>
#include <iostream>
#include <cstdio>
#include <rclcpp/rclcpp.hpp>
#include <behaviortree_cpp_v3/bt_factory.h>

#include "fly_step_msgs/srv/set_main_wps.hpp"

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

  // 提供运行时接口：通过 service 更新 BT 黑板中的 MainWPs（线程安全）
  std::mutex bb_mutex;
  

  // 等待 planner（或外部）通过 service 提供 MainWPs（可配置超时时间），如果在超时前收到了就把 XML 中的 SetBlackboard 替换为接收到的值
  int wait_sec = 10; // 默认等待时间，增加到10秒确保Planner有足够时间完成规划并调用service
  node->declare_parameter<int>("main_wps_wait_sec", wait_sec);
  node->get_parameter("main_wps_wait_sec", wait_sec);

  std::mutex recv_mutex;
  std::vector<int> received_wps;
  bool main_wps_received = false;

  // 修改 service 回调以写入 received_wps 并标记已收到
  using SetMainWps = fly_step_msgs::srv::SetMainWps;
  auto set_main_wps_cb = [blackboard, &bb_mutex, node, &recv_mutex, &received_wps, &main_wps_received](
    const std::shared_ptr<SetMainWps::Request> req,
    std::shared_ptr<SetMainWps::Response> res) -> void
  {
    try {
      std::lock_guard<std::mutex> lk(bb_mutex);
      std::vector<int> wps(req->wps.begin(), req->wps.end());
      blackboard->set<std::vector<int>>("MainWPs", wps);
      res->success = true;
      res->message = "MainWPs updated";
      RCLCPP_INFO(node->get_logger(), "Service set_main_wps: received and set %zu MainWPs in blackboard: [%s]", wps.size(),
                  wps.empty() ? "" : std::to_string(wps[0]).c_str());

      // also record for startup-time replacement
      {
        std::lock_guard<std::mutex> rlk(recv_mutex);
        received_wps = wps;
        main_wps_received = true;
      }
    } catch (const std::exception & e) {
      res->success = false;
      res->message = std::string("Exception: ") + e.what();
      RCLCPP_ERROR(node->get_logger(), "Exception in set_main_wps service: %s", e.what());
    }
  };
  auto service = node->create_service<SetMainWps>("/fly_step_bt/set_main_wps", set_main_wps_cb);

  // 等待 MainWPs 到达（在等待期间要处理回调以接收 service 调用）
  RCLCPP_INFO(node->get_logger(), "Waiting up to %d s for external MainWPs (service /fly_step_bt/set_main_wps)", wait_sec);
  auto wait_deadline = std::chrono::steady_clock::now() + std::chrono::seconds(wait_sec);
  while (rclcpp::ok() && std::chrono::steady_clock::now() < wait_deadline) {
    rclcpp::spin_some(node);
    {
      std::lock_guard<std::mutex> rlk(recv_mutex);
      if (main_wps_received) break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }

  // 如果收到了外部 main_wps，则在内存中替换 XML 中的 SetBlackboard 的 value 字段并直接从字符串创建树（避免临时文件）
  bool used_in_memory_xml = false;
  std::string in_memory_xml;
  {
    std::lock_guard<std::mutex> rlk(recv_mutex);
    if (main_wps_received && !received_wps.empty()) {
      RCLCPP_INFO(node->get_logger(), "Received external MainWPs at startup, patching BT xml in-memory before loading");
      // 读取原始 xml
      std::ifstream in(bt_xml_file);
      if (in.is_open()) {
        std::stringstream buf;
        buf << in.rdbuf();
        in_memory_xml = buf.str();
        in.close();

        // 构造新的 value 字符串
        std::ostringstream oss;
        oss << "[";
        for (size_t i = 0; i < received_wps.size(); ++i) {
          if (i) oss << ", ";
          oss << received_wps[i];
        }
        oss << "]";
        std::string new_value = oss.str();

        // 找到包含 output_key="MainWPs" 的 SetBlackboard 标签并替换整个标签为带有 new_value 的自闭合节点
        std::string needle = "<SetBlackboard";
        size_t pos = in_memory_xml.find(needle);
        bool replaced = false;
        while (pos != std::string::npos) {
          size_t end_tag = in_memory_xml.find("/>", pos);
          if (end_tag == std::string::npos) break;
          std::string tag = in_memory_xml.substr(pos, end_tag - pos + 2);
          if (tag.find("output_key=\"MainWPs\"") != std::string::npos) {
            // 构造替换标签
            std::ostringstream newtag;
            newtag << "<SetBlackboard output_key=\"MainWPs\" value=\"" << new_value << "\" />";
            in_memory_xml.replace(pos, end_tag - pos + 2, newtag.str());
            replaced = true;
            break;
          }
          pos = in_memory_xml.find(needle, pos + 1);
        }

        if (replaced) {
          used_in_memory_xml = true;
          RCLCPP_INFO(node->get_logger(), "Patched BT xml in-memory and will load from memory");
        } else {
          RCLCPP_WARN(node->get_logger(), "Could not find SetBlackboard for MainWPs in XML; using original xml");
          in_memory_xml.clear();
        }
      } else {
        RCLCPP_WARN(node->get_logger(), "Failed to open BT xml file to patch: %s; using original xml", bt_xml_file.c_str());
      }
    } else {
      RCLCPP_INFO(node->get_logger(), "No external MainWPs received within %d s; using XML default", wait_sec);
    }
  }

  // create tree with injected blackboard (either from memory or file)
  BT::Tree tree = used_in_memory_xml ? factory.createTreeFromText(in_memory_xml, blackboard)
                                      : factory.createTreeFromFile(bt_xml_file, blackboard);
  RCLCPP_INFO(node->get_logger(), "Loaded BT xml: %s", used_in_memory_xml ? "<in-memory>" : bt_xml_file.c_str());

  // 检查从XML加载的MainWPs
  if (blackboard->getEntry("MainWPs")) {
    auto entry = blackboard->getEntry("MainWPs");
    if (entry) {
      try {
        auto wps = entry->value.cast<std::vector<int>>();
        RCLCPP_INFO(node->get_logger(), "Loaded MainWPs from XML with %zu waypoints: [%s]",
                    wps.size(), wps.empty() ? "" : std::to_string(wps[0]).c_str());
      } catch (const std::exception& e) {
        RCLCPP_WARN(node->get_logger(), "Failed to cast MainWPs from XML: %s", e.what());
      }
    }
  } else {
    RCLCPP_WARN(node->get_logger(), "No MainWPs found in XML blackboard");
  }

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