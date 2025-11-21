# generated from colcon_zsh/shell/template/prefix_chain.zsh.em

# This script extends the environment with the environment of other prefix
# paths which were sourced when this file was generated as well as all packages
# contained in this prefix path.

# function to source another script with conditional trace output
# first argument: the path of the script
_colcon_prefix_chain_zsh_source_script() {
  if [ -f "$1" ]; then
    if [ -n "$COLCON_TRACE" ]; then
      echo "# . \"$1\""
    fi
    . "$1"
  else
    echo "not found: \"$1\"" 1>&2
  fi
}

# source chained prefixes
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/opt/ros/humble"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/fast_livo2_relocation/install"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/BehaviorTree.CPP/install"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/home/oh/SCURC_Nav_Sim/src/dependencies_and_tools/autonomous_exploration_development_environment/install"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/home/oh/SCURC_Nav_Sim/src/navigation_plugins/r2_waypoint_loader_cpp/install"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="/home/oh/SCURC_Nav_Sim/src/core_navigation/navigation2/install"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"

# source this prefix
# setting COLCON_CURRENT_PREFIX avoids determining the prefix in the sourced script
COLCON_CURRENT_PREFIX="$(builtin cd -q "`dirname "${(%):-%N}"`" > /dev/null && pwd)"
_colcon_prefix_chain_zsh_source_script "$COLCON_CURRENT_PREFIX/local_setup.zsh"

unset COLCON_CURRENT_PREFIX
unset _colcon_prefix_chain_zsh_source_script
