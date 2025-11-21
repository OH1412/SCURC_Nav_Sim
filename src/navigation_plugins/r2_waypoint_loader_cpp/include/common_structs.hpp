// common_structs.hpp
#ifndef R2_WAYPOINT_LOADER_CPP__COMMON_STRUCTS_HPP_
#define R2_WAYPOINT_LOADER_CPP__COMMON_STRUCTS_HPP_

#include <string>

namespace r2_waypoint_loader_cpp {

// 统一的任务信息结构体（主程序和插件共用）
struct WaypointTaskInfo {
    std::string action;    // "ascend" 或 "delayed_descend"
    int height_mm;         // 200 或 400
};

}  // namespace r2_waypoint_loader_cpp

#endif  // R2_WAYPOINT_LOADER_CPP__COMMON_STRUCTS_HPP_
