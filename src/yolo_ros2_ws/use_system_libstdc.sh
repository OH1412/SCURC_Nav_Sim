#!/bin/bash

# 脚本作用：
# 该脚本用于确保指定的 Conda 环境使用系统的 libstdc++ 库，而不是 Conda 环境中可能存在的旧版本库。
# 主要的步骤包括：
# 1. 检查是否传递了 Conda 环境名称。
# 2. 检查系统中是否存在 libstdc++ 库。
# 3. 检查指定的 Conda 环境是否存在。
# 4. 备份 Conda 环境中的 libstdc++ 文件。
# 5. 创建软链接，将 Conda 环境中的 libstdc++ 指向系统 libstdc++ 库。
# 这样可以解决因为 Conda 环境中的 libstdc++ 版本过旧，导致与 ROS2 等软件不兼容的问题。

# 使用方法如下：
# ./use_system_libstdc.sh <conda_env_name>



set -e

# 检查是否传递了环境名称
if [ -z "$1" ]; then
    echo "Usage: $0 <conda_env_name>"
    exit 1
fi

ENV_NAME="$1"
CONDA_BASE=$(conda info --base)
ENV_PATH="$CONDA_BASE/envs/$ENV_NAME/lib"

SYSTEM_LIB="/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

# 检查系统 libstdc++ 是否存在
if [ ! -f "$SYSTEM_LIB" ]; then
    echo "Error: System libstdc++ not found at $SYSTEM_LIB"
    exit 1
fi

# 检查 Conda 环境是否存在
if [ ! -d "$ENV_PATH" ]; then
    echo "Error: Conda environment '$ENV_NAME' not found at $ENV_PATH"
    exit 1
fi

cd "$ENV_PATH"

# 备份现有的 libstdc++ 库文件
for f in libstdc++.so libstdc++.so.6; do
    if [ -e "$f" ]; then
        echo "Backing up $f -> ${f}.bak"
        mv "$f" "${f}.bak"
    fi
done

# 创建软链接，指向系统的 libstdc++ 库
ln -s "$SYSTEM_LIB" libstdc++.so.6
ln -s "$SYSTEM_LIB" libstdc++.so

echo "✅ Conda environment '$ENV_NAME' now uses system libstdc++ at $SYSTEM_LIB"
