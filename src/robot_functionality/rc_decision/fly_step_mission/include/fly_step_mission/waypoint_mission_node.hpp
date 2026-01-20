#pragma once

#include <string>

namespace fly_step_mission
{

/**
 * @brief 航点任务信息结构体
 */
struct WaypointTaskInfo
{
  std::string action;    // "ascend" 或 "delayed_descend"
  int height_mm{0};      // 高度（毫米）
};

/**
 * @brief 航点关系枚举
 */
enum class WaypointRelation
{
  RELATION_PLUS_3,   // +3: 向前移动（Y+）
  RELATION_MINUS_3,  // -3: 向后移动（Y-）
  RELATION_PLUS_1,   // +1: 向左移动（X-）
  RELATION_MINUS_1,  // -1: 向右移动（X+）
  RELATION_ERROR     // 无效关系
};

}  // namespace fly_step_mission
