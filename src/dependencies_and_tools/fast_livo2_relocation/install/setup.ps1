# generated from colcon_powershell/shell/template/prefix_chain.ps1.em

# This script extends the environment with the environment of other prefix
# paths which were sourced when this file was generated as well as all packages
# contained in this prefix path.

# function to source another script with conditional trace output
# first argument: the path of the script
function _colcon_prefix_chain_powershell_source_script {
  param (
    $_colcon_prefix_chain_powershell_source_script_param
  )
  # source script with conditional trace output
  if (Test-Path $_colcon_prefix_chain_powershell_source_script_param) {
    if ($env:COLCON_TRACE) {
      echo ". '$_colcon_prefix_chain_powershell_source_script_param'"
    }
    . "$_colcon_prefix_chain_powershell_source_script_param"
  } else {
    Write-Error "not found: '$_colcon_prefix_chain_powershell_source_script_param'"
  }
}

# source chained prefixes
_colcon_prefix_chain_powershell_source_script "/opt/ros/humble\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/robot_functionality/r2_bringup/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/costmap_intensity/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/behavior_ext_plugins/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/BehaviorTree.CPP/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/autonomous_exploration_development_environment/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/navigation_plugins/r2_waypoint_loader_cpp/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/core_navigation/navigation2/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/navigation_plugins/nav2_ext_plugins/velocity_smoother_ext/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/livox_laser_simulation_RO2/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/simulation_environment/rc_robot_simulation/pangolin_simulation/install\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/elevation_mapping_cupy_ros2/install\local_setup.ps1"

# source this prefix
$env:COLCON_CURRENT_PREFIX=(Split-Path $PSCommandPath -Parent)
_colcon_prefix_chain_powershell_source_script "$env:COLCON_CURRENT_PREFIX\local_setup.ps1"
