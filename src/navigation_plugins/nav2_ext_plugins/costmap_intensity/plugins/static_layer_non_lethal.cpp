/*********************************************************************
 *
 * A static map layer that marks occupied cells with a configurable
 * cost (default 200) instead of LETHAL_OBSTACLE (254).
 *
 * Occupied cells are visible in RViz (orange, not red) but do NOT
 * trigger DWB collision detection since cost < INSCRIBED (253).
 *
 *********************************************************************/
#include "costmap_intensity/static_layer_non_lethal.hpp"

#include <algorithm>
#include <string>

#include "nav2_costmap_2d/costmap_math.hpp"
#include "nav2_costmap_2d/cost_values.hpp"
#include "nav2_costmap_2d/footprint.hpp"
#include "pluginlib/class_list_macros.hpp"

PLUGINLIB_EXPORT_CLASS(costmap_intensity::StaticLayerNonLethal, nav2_costmap_2d::Layer)

using nav2_costmap_2d::FREE_SPACE;
using nav2_costmap_2d::LETHAL_OBSTACLE;
using nav2_costmap_2d::NO_INFORMATION;

namespace costmap_intensity
{

StaticLayerNonLethal::StaticLayerNonLethal()
  : CostmapLayer()
{
}

StaticLayerNonLethal::~StaticLayerNonLethal()
{
}

// ---------------------------------------------------------------------------
// interpretValue — the key change vs standard StaticLayer
// ---------------------------------------------------------------------------
unsigned char StaticLayerNonLethal::interpretValue(unsigned char value)
{
  // Standard map values: 0=free, 100=occupied, -1=unknown (255 in unsigned)
  if (track_unknown_space_ && static_cast<int>(value) == unknown_cost_value_) {
    return NO_INFORMATION;
  } else if (!track_unknown_space_ && static_cast<int>(value) == unknown_cost_value_) {
    return FREE_SPACE;
  } else if (static_cast<int>(value) >= lethal_threshold_) {
    // ── KEY CHANGE: configurable cost instead of hardcoded 254 ──
    return static_cast<unsigned char>(occupied_cost_value_);
  } else {
    return FREE_SPACE;
  }
}

// ---------------------------------------------------------------------------
// onInitialize
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::onInitialize()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error{"Failed to lock node in StaticLayerNonLethal"};
  }

  getParameters();

  // Subscribe to map topic
  rclcpp::QoS map_qos(10);
  map_qos.transient_local();
  map_qos.reliable();
  map_qos.keep_last(1);

  if (map_subscribe_transient_local_) {
    map_sub_ = node->create_subscription<nav_msgs::msg::OccupancyGrid>(
      map_topic_, map_qos,
      std::bind(&StaticLayerNonLethal::incomingMap, this, std::placeholders::_1));
  } else {
    rclcpp::QoS qos = rclcpp::QoS(rclcpp::KeepLast(1));
    qos.transient_local();
    qos.reliable();
    map_sub_ = node->create_subscription<nav_msgs::msg::OccupancyGrid>(
      map_topic_, qos,
      std::bind(&StaticLayerNonLethal::incomingMap, this, std::placeholders::_1));
  }

  global_frame_ = layered_costmap_->getGlobalFrameID();

  RCLCPP_INFO(
    logger_,
    "StaticLayerNonLethal: subscribed to %s, occupied_cost=%d (not lethal 254)",
    map_topic_.c_str(), occupied_cost_value_);

  current_ = true;
}

// ---------------------------------------------------------------------------
// getParameters
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::getParameters()
{
  auto node = node_.lock();
  if (!node) return;

  declareParameter("map_topic", rclcpp::ParameterValue(std::string("map")));
  declareParameter("map_subscribe_transient_local", rclcpp::ParameterValue(true));
  declareParameter("track_unknown_space", rclcpp::ParameterValue(false));
  declareParameter("use_maximum", rclcpp::ParameterValue(true));
  declareParameter("lethal_cost_threshold", rclcpp::ParameterValue(100));
  declareParameter("unknown_cost_value", rclcpp::ParameterValue(static_cast<int>(-1)));
  declareParameter("trinary_costmap", rclcpp::ParameterValue(true));
  declareParameter("transform_tolerance", rclcpp::ParameterValue(0.3));
  declareParameter("occupied_cost_value", rclcpp::ParameterValue(200));

  node->get_parameter(name_ + "." + "map_topic", map_topic_);
  node->get_parameter(
    name_ + "." + "map_subscribe_transient_local",
    map_subscribe_transient_local_);
  node->get_parameter(name_ + "." + "track_unknown_space", track_unknown_space_);
  node->get_parameter(name_ + "." + "use_maximum", use_maximum_);
  node->get_parameter(name_ + "." + "lethal_cost_threshold", lethal_threshold_);
  node->get_parameter(name_ + "." + "unknown_cost_value", unknown_cost_value_);
  node->get_parameter(name_ + "." + "trinary_costmap", trinary_costmap_);
  node->get_parameter(name_ + "." + "transform_tolerance", transform_tolerance_);
  node->get_parameter(name_ + "." + "occupied_cost_value", occupied_cost_value_);

  // Enforce trinary_costmap = true to keep things simple
  if (!trinary_costmap_) {
    RCLCPP_WARN(logger_, "StaticLayerNonLethal: forcing trinary_costmap to true");
    trinary_costmap_ = true;
  }
}

// ---------------------------------------------------------------------------
// incomingMap — process new map, respecting trinary interpretation
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::incomingMap(
  const nav_msgs::msg::OccupancyGrid::SharedPtr new_map)
{
  std::lock_guard<Costmap2D::mutex_t> guard(*getMutex());

  unsigned int size_x = new_map->info.width;
  unsigned int size_y = new_map->info.height;

  // Resize internal costmap if needed
  if (getSizeInCellsX() != size_x || getSizeInCellsY() != size_y) {
    resizeMap(size_x, size_y, new_map->info.resolution,
              new_map->info.origin.position.x,
              new_map->info.origin.position.y);
  } else if (origin_x_ != new_map->info.origin.position.x ||
             origin_y_ != new_map->info.origin.position.y) {
    updateOrigin(new_map->info.origin.position.x,
                 new_map->info.origin.position.y);
  }

  // Copy map data with custom interpretation
  for (unsigned int i = 0; i < size_y; ++i) {
    for (unsigned int j = 0; j < size_x; ++j) {
      unsigned char value = new_map->data[i * size_x + j];
      costmap_[i * size_x + j] = interpretValue(value);
    }
  }

  map_frame_ = new_map->header.frame_id;
  x_ = y_ = 0;
  width_ = size_x;
  height_ = size_y;
  map_received_ = true;
  has_updated_data_ = true;

  // Match layered costmap size to map
  layered_costmap_->resizeMap(
    size_x, size_y, new_map->info.resolution,
    new_map->info.origin.position.x,
    new_map->info.origin.position.y, true);

  RCLCPP_INFO(
    logger_,
    "StaticLayerNonLethal: received map %dx%d, lethal threshold=%d, "
    "occupied cost=%d",
    size_x, size_y, lethal_threshold_, occupied_cost_value_);
}

// ---------------------------------------------------------------------------
// updateBounds
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::updateBounds(
  double /*robot_x*/, double /*robot_y*/, double /*robot_yaw*/,
  double * min_x, double * min_y,
  double * max_x, double * max_y)
{
  std::lock_guard<Costmap2D::mutex_t> guard(*getMutex());

  if (!map_received_ || !has_updated_data_) {
    return;
  }

  useExtraBounds(min_x, min_y, max_x, max_y);

  double wx, wy;
  mapToWorld(x_, y_, wx, wy);
  *min_x = std::min(wx, *min_x);
  *min_y = std::min(wy, *min_y);

  mapToWorld(x_ + width_, y_ + height_, wx, wy);
  *max_x = std::max(wx, *max_x);
  *max_y = std::max(wy, *max_y);

  has_updated_data_ = false;
}

// ---------------------------------------------------------------------------
// updateCosts
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::updateCosts(
  nav2_costmap_2d::Costmap2D & master_grid,
  int min_i, int min_j, int max_i, int max_j)
{
  std::lock_guard<Costmap2D::mutex_t> guard(*getMutex());

  if (!enabled_ || !map_received_) {
    return;
  }

  if (use_maximum_) {
    updateWithMax(master_grid, min_i, min_j, max_i, max_j);
  } else {
    updateWithOverwrite(master_grid, min_i, min_j, max_i, max_j);
  }
}

// ---------------------------------------------------------------------------
// matchSize
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::matchSize()
{
  std::lock_guard<Costmap2D::mutex_t> guard(*getMutex());
  CostmapLayer::matchSize();
}

// ---------------------------------------------------------------------------
// activate / deactivate / reset
// ---------------------------------------------------------------------------
void StaticLayerNonLethal::activate()
{
  if (map_sub_ && !map_received_) {
    // Resubscribe may be needed if the map topic wasn't latched
  }
}

void StaticLayerNonLethal::deactivate()
{
  // Nothing to do — map_sub_ stays alive
}

void StaticLayerNonLethal::reset()
{
  std::lock_guard<Costmap2D::mutex_t> guard(*getMutex());
  resetMaps();
  current_ = false;
  map_received_ = false;
  has_updated_data_ = false;
}

}  // namespace costmap_intensity
