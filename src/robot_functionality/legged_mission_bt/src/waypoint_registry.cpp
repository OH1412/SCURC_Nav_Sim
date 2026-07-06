#include "legged_mission_bt/waypoint_registry.hpp"

#include <stdexcept>

#include <yaml-cpp/yaml.h>

namespace legged_mission_bt
{

namespace
{

std::string nodeKeyToString(const YAML::Node & key)
{
  if (key.IsScalar()) {
    return key.as<std::string>();
  }
  throw std::runtime_error("waypoint id must be a scalar key");
}

NavWaypoint parseNavWaypoint(const YAML::Node & node)
{
  NavWaypoint wp;
  if (node["frame_id"]) {
    wp.frame_id = node["frame_id"].as<std::string>();
  }
  if (!node["x"] || !node["y"]) {
    throw std::runtime_error("nav waypoint requires x and y");
  }
  wp.x = node["x"].as<double>();
  wp.y = node["y"].as<double>();
  wp.yaw = node["yaw"] ? node["yaw"].as<double>() : 0.0;
  return wp;
}

ArmWaypoint parseArmWaypoint(const YAML::Node & node)
{
  ArmWaypoint wp;
  if (!node["x"] || !node["y"] || !node["z"]) {
    throw std::runtime_error("arm waypoint requires x, y, and z");
  }
  wp.x = node["x"].as<double>();
  wp.y = node["y"].as<double>();
  wp.z = node["z"].as<double>();
  wp.yaw = node["yaw"] ? node["yaw"].as<double>() : 0.0;
  return wp;
}

}  // namespace

std::shared_ptr<WaypointRegistry> WaypointRegistry::create()
{
  return std::shared_ptr<WaypointRegistry>(new WaypointRegistry());
}

void WaypointRegistry::seedFromFile(const std::string & path)
{
  if (path.empty()) {
    return;
  }

  const YAML::Node root = YAML::LoadFile(path);
  if (root["nav"]) {
    for (const auto & item : root["nav"]) {
      setNav(nodeKeyToString(item.first), parseNavWaypoint(item.second));
    }
  }
  if (root["arm"]) {
    for (const auto & item : root["arm"]) {
      setArm(nodeKeyToString(item.first), parseArmWaypoint(item.second));
    }
  }
}

void WaypointRegistry::setNav(const std::string & id, NavWaypoint wp)
{
  std::lock_guard<std::mutex> lock(mutex_);
  nav_waypoints_[id] = std::move(wp);
}

void WaypointRegistry::setArm(const std::string & id, ArmWaypoint wp)
{
  std::lock_guard<std::mutex> lock(mutex_);
  arm_waypoints_[id] = std::move(wp);
}

void WaypointRegistry::clearArm(const std::string & id)
{
  std::lock_guard<std::mutex> lock(mutex_);
  arm_waypoints_.erase(id);
}

void WaypointRegistry::clearAll()
{
  std::lock_guard<std::mutex> lock(mutex_);
  nav_waypoints_.clear();
  arm_waypoints_.clear();
  mission_plan_.clear();
}

void WaypointRegistry::setMissionPlan(std::vector<PlannedStep> steps)
{
  std::lock_guard<std::mutex> lock(mutex_);
  mission_plan_ = std::move(steps);
}

bool WaypointRegistry::hasMissionPlan() const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return !mission_plan_.empty();
}

bool WaypointRegistry::tryGetMissionStep(size_t index, PlannedStep & out) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  if (index >= mission_plan_.size()) {
    return false;
  }
  out = mission_plan_[index];
  return true;
}

size_t WaypointRegistry::missionStepCount() const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return mission_plan_.size();
}

bool WaypointRegistry::hasNav(const std::string & id) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return nav_waypoints_.count(id) > 0;
}

bool WaypointRegistry::hasArm(const std::string & id) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return arm_waypoints_.count(id) > 0;
}

bool WaypointRegistry::tryGetNav(const std::string & id, NavWaypoint & out) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  const auto it = nav_waypoints_.find(id);
  if (it == nav_waypoints_.end()) {
    return false;
  }
  out = it->second;
  return true;
}

bool WaypointRegistry::tryGetArm(const std::string & id, ArmWaypoint & out) const
{
  std::lock_guard<std::mutex> lock(mutex_);
  const auto it = arm_waypoints_.find(id);
  if (it == arm_waypoints_.end()) {
    return false;
  }
  out = it->second;
  return true;
}

size_t WaypointRegistry::navCount() const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return nav_waypoints_.size();
}

size_t WaypointRegistry::armCount() const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return arm_waypoints_.size();
}

}  // namespace legged_mission_bt
