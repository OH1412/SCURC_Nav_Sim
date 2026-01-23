#!/bin/bash
# 路径：~/SCURC_Nav_Sim/load_all.sh

# 按依赖顺序加载所有 install 目录（改为仅在存在时 source，避免错误）
_source_if_exists() {
	if [ -f "$1" ]; then
		# shellcheck disable=SC1090
		source "$1"
		SOURCED+=("$1")
		echo "sourced: $1"
	else
		MISSING+=("$1")
		echo "not found: \"$1\""
	fi
}

# 优先尝试整体 workspace 的 setup（如果你有在根目录构建过）
# _source_if_exists "$HOME/SCURC_Nav_Sim/install/setup.bash"

_source_if_exists "$HOME/SCURC_Nav_Sim/src/core_navigation/navigation2/install/setup.bash"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/dependencies_and_tools/BehaviorTree.CPP/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/dependencies_and_tools/fast_livo2_relocation/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/dependencies_and_tools/livox_ros_driver2/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/dependencies_and_tools/elevation_mapping_cupy_ros2/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/dependencies_and_tools/autonomous_exploration_development_environment/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/costmap_intensity/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/velocity_smoother_ext/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/grid_map/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/rc_decision/fly_step_mission/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/kfs_detection_nav/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/yolo_simulator/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/rc_interfaces/yolov8_ros2_msgs/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/rc_interfaces/fly_step_msgs/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/robot_functionality/serial_twist_bridge/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/livox_laser_simulation_RO2/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/pangolin_simulation/install/setup.sh"
_source_if_exists "$HOME/SCURC_Nav_Sim/src/yolo_ros2_ws/yolov8_ros2/install/setup.sh"

# Summary: print which files were sourced and which were missing
echo
if [ ${#MISSING[@]} -gt 0 ]; then
	echo "Missing setup files (${#MISSING[@]}):"
	for f in "${MISSING[@]}"; do
		echo "  - $f"
	done
else
	echo "No missing setup files detected."
fi

echo "所有模块环境已尝试加载"
