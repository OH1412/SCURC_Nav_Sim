/*********************************************************************
 *
 * Software License Agreement (BSD License)
 *
 *********************************************************************/
#ifndef COSTMAP_INTENSITY__STATIC_LAYER_NON_LETHAL_HPP_
#define COSTMAP_INTENSITY__STATIC_LAYER_NON_LETHAL_HPP_

#include <mutex>
#include <string>
#include "nav2_costmap_2d/costmap_layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "rclcpp/rclcpp.hpp"

namespace costmap_intensity
{

/**
 * @class StaticLayerNonLethal
 * @brief A static map layer where occupied cells are marked with a
 *        configurable cost value instead of hardcoded LETHAL_OBSTACLE (254).
 *
 * Set occupied_cost_value below INSCRIBED_INFLATED_OBSTACLE (253) to keep
 * the static map visible in RViz (orange, not red) while preventing local
 * planner collision detection.
 *
 * Default occupied_cost_value = 200.
 */
class StaticLayerNonLethal : public nav2_costmap_2d::CostmapLayer
{
public:
  StaticLayerNonLethal();
  virtual ~StaticLayerNonLethal();

  void onInitialize() override;
  void activate() override;
  void deactivate() override;
  void reset() override;
  bool isClearable() override { return false; }

  void updateBounds(
    double robot_x, double robot_y, double robot_yaw,
    double * min_x, double * min_y,
    double * max_x, double * max_y) override;

  void updateCosts(
    nav2_costmap_2d::Costmap2D & master_grid,
    int min_i, int min_j, int max_i, int max_j) override;

  void matchSize() override;

protected:
  void getParameters();

  /**
   * @brief Interpret map occupancy value (0-100) → costmap cost (0-255).
   *        Occupied (>= lethal_threshold) → occupied_cost_value_ instead of 254.
   */
  unsigned char interpretValue(unsigned char value);

  void incomingMap(const nav_msgs::msg::OccupancyGrid::SharedPtr new_map);

  std::string global_frame_;
  std::string map_frame_;

  bool has_updated_data_{false};
  bool map_received_{false};
  bool map_received_in_update_bounds_{false};

  unsigned int x_{0}, y_{0}, width_{0}, height_{0};

  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;

  // Parameters
  std::string map_topic_;
  bool map_subscribe_transient_local_;
  bool track_unknown_space_;
  bool use_maximum_;
  int lethal_threshold_;           // map value threshold for "occupied" (default 100)
  int unknown_cost_value_;         // map value for "unknown" (default -1)
  int occupied_cost_value_{200};   // costmap value for occupied cells (default 200)
  bool trinary_costmap_;
  double transform_tolerance_;
};

}  // namespace costmap_intensity

#endif  // COSTMAP_INTENSITY__STATIC_LAYER_NON_LETHAL_HPP_
