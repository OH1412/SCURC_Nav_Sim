#ifndef PROTOCOL_DEFS_HPP
#define PROTOCOL_DEFS_HPP

#include <cstdint>
#include <vector>

namespace protocol {

constexpr uint8_t FRAME_HEAD = 0x0F;
constexpr uint8_t FRAME_HEAD_SEND = 0xF0;
constexpr uint8_t FRAME_HEAD_READ = 0xFF;

inline uint8_t calcChecksum(const std::vector<uint8_t>& data) {
    uint32_t sum = 0;
    for (uint8_t byte : data) {
        sum += byte;
    }
    return static_cast<uint8_t>(sum & 0xFF);
}

}
#endif
