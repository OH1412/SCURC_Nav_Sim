#pragma once

#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace legged_mission_bt
{

struct NavWaypoint
{
  std::string frame_id{"map"};
  double x{0.0};
  double y{0.0};
  double yaw{0.0};
};

struct ArmWaypoint
{
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double yaw{0.0};
};

struct PlannedStep
{
  std::string nav_id;
  uint8_t arm_point_id{0};  // 0~7 pick, 8~15 place
  uint8_t arm_action{0};    // 0=none, 1=pick, 2=place
};

constexpr uint8_t kPickPointMin = 0;
constexpr uint8_t kPickPointMax = 7;
constexpr uint8_t kPlacePointMin = 8;
constexpr uint8_t kPlacePointMax = 15;

inline bool isValidArmPointForAction(uint8_t arm_point_id, uint8_t arm_action)
{
  if (arm_action == 1) {
    return arm_point_id >= kPickPointMin && arm_point_id <= kPickPointMax;
  }
  if (arm_action == 2) {
    return arm_point_id >= kPlacePointMin && arm_point_id <= kPlacePointMax;
  }
  return false;
}

inline std::string resolveArmSlotId(const PlannedStep & step)
{
  if (step.arm_point_id >= kPickPointMin && step.arm_point_id <= kPlacePointMax) {
    return std::to_string(step.arm_point_id);
  }
  return {};
}

class WaypointRegistry
{
public:
  static std::shared_ptr<WaypointRegistry> create();

  void seedFromFile(const std::string & path);

  void setNav(const std::string & id, NavWaypoint wp);
  void setArm(const std::string & id, ArmWaypoint wp);
  void clearArm(const std::string & id);
  void setMissionPlan(std::vector<PlannedStep> steps);
  void clearAll();

  bool hasNav(const std::string & id) const;
  bool hasArm(const std::string & id) const;
  bool hasMissionPlan() const;
  bool tryGetNav(const std::string & id, NavWaypoint & out) const;
  bool tryGetArm(const std::string & id, ArmWaypoint & out) const;
  bool tryGetMissionStep(size_t index, PlannedStep & out) const;

  size_t navCount() const;
  size_t armCount() const;
  size_t missionStepCount() const;

private:
  mutable std::mutex mutex_;
  std::unordered_map<std::string, NavWaypoint> nav_waypoints_;
  std::unordered_map<std::string, ArmWaypoint> arm_waypoints_;
  std::vector<PlannedStep> mission_plan_;
};

}  // namespace legged_mission_bt
