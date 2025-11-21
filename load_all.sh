#!/bin/bash
# 路径：~/SCURC_Nav_Sim/load_all.sh

# 按依赖顺序加载所有 install 目录
# source ~/SCURC_Nav_Sim/install/setup.bash
source ~/SCURC_Nav_Sim/src/dependencies_and_tools/BehaviorTree.CPP/install/setup.sh
source ~/SCURC_Nav_Sim/src/core_navigation/navigation2/install/setup.bash
source ~/SCURC_Nav_Sim/src/dependencies_and_tools/fast_livo2_relocation/install/setup.sh
source ~/SCURC_Nav_Sim/src/dependencies_and_tools/BehaviorTree.CPP/install/setup.sh
source ~/SCURC_Nav_Sim/src/dependencies_and_tools/autonomous_exploration_development_environment/install/setup.sh
source ~/SCURC_Nav_Sim/src/navigation_plugins/r2_waypoint_loader_cpp/install/setup.sh
source ~/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/costmap_intensity/install/setup.sh
source ~/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/install/setup.sh
source ~/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/velocity_smoother_ext/install/setup.sh
source ~/SCURC_Nav_Sim/src/robot_functionality/r2_bringup/install/setup.sh
source ~/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/livox_laser_simulation_RO2/install/setup.sh
source ~/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/pangolin_simulation/install/setup.sh
echo "所有模块环境已加载"
