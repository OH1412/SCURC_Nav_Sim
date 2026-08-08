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
_source_if_exists "$HOME/SCURC_Nav_Sim/install/setup.bash"

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
