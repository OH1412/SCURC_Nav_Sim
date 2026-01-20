#pragma once

#include <behaviortree_cpp_v3/bt_factory.h>
#include <vector>
#include <string>
#include <sstream>

// 为 std::vector<int> 添加 BT 类型转换支持
// 支持格式: "[-1,2,3]" 或 "-1,2,3" 或 "-1;2;3"
// 必须在头文件中定义，以便 BT 库能正确使用
namespace BT
{
template <>
inline std::vector<int> convertFromString(StringView str)
{
    std::vector<int> result;
    std::string s(str.data(), str.size());
    
    // 移除可能的括号
    if (!s.empty() && s.front() == '[') {
        s.erase(0, 1);
    }
    if (!s.empty() && s.back() == ']') {
        s.pop_back();
    }
    
    // 使用 stringstream 按逗号分隔
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, ',')) {
        // 去除首尾空格
        size_t start = item.find_first_not_of(" \t");
        size_t end = item.find_last_not_of(" \t");
        
        if (start != std::string::npos && end != std::string::npos) {
            item = item.substr(start, end - start + 1);
        } else if (start != std::string::npos) {
            item = item.substr(start);
        } else {
            item.clear();
        }
        
        if (!item.empty()) {
            try {
                result.push_back(std::stoi(item));
            } catch (const std::exception& e) {
                // 解析失败，跳过这个元素
            }
        }
    }
    return result;
}
}  // namespace BT
