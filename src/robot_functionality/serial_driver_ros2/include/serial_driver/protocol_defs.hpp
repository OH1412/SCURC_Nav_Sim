#ifndef PROTOCOL_DEFS_HPP
#define PROTOCOL_DEFS_HPP

#include <cstdint>
#include <vector>

namespace protocol {

// 通用帧头 (旧 float 数组协议)
constexpr uint8_t FRAME_HEAD = 0x0F;
constexpr uint8_t FRAME_HEAD_SEND = 0xF0;
constexpr uint8_t FRAME_HEAD_READ = 0xFF;

// 机械臂协议帧头
constexpr uint8_t FRAME_HEAD_ARM_CMD = 0xFD;  // 命令帧 (上位机→下位机)
constexpr uint8_t FRAME_HEAD_ARM_ACK = 0xFE;  // ACK帧  (下位机→上位机)

// 机械臂控制位
constexpr uint8_t ARM_CTRL_PICK  = 0x01;  // 吸取
constexpr uint8_t ARM_CTRL_PLACE = 0x02;  // 放置

// 机械臂 ACK 结果码
constexpr uint8_t ARM_ACK_OK   = 0x00;  // 成功
constexpr uint8_t ARM_ACK_FAIL = 0x01;  // 失败

inline uint8_t calcChecksum(const std::vector<uint8_t>& data) {
    uint32_t sum = 0;
    for (uint8_t byte : data) {
        sum += byte;
    }
    return static_cast<uint8_t>(sum & 0xFF);
}

}
#endif
