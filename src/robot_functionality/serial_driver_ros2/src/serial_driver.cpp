#include "rclcpp/rclcpp.hpp"
#include "serial_driver/serial_comm.hpp"
#include "serial_driver/protocol_defs.hpp"
#include <iostream>

SerialComm::SerialComm(const std::string& port, unsigned long baudrate)
    : port_(port),
      baudrate_(baudrate),
      running_(true) {
    
    // 尝试初始化串口，失败也不影响程序启动
    try {
        serial_port_.setPort(port_);
        serial_port_.setBaudrate(baudrate_);
        serial::Timeout timeout = serial::Timeout::simpleTimeout(1000);
        serial_port_.setTimeout(timeout);
        serial_port_.open();
        
        if (serial_port_.isOpen()) {
            RCLCPP_INFO(rclcpp::get_logger("SerialComm"), "✅ Serial Open at: %s @ %lu bps", port.c_str(), baudrate);
        }
    } catch (const std::exception& e) {
        RCLCPP_WARN(rclcpp::get_logger("SerialComm"), "⚠️ Serial Open failed: %s, will auto-reconnect...", e.what());
    }
    
    // 启动自动重连线程
    reconnect_thread_ = std::thread(&SerialComm::reconnectLoop, this);
}

SerialComm::~SerialComm() {
    running_ = false;
    if (reconnect_thread_.joinable()) {
        reconnect_thread_.join();
    }
    
    std::lock_guard<std::mutex> lock(serial_mutex_);
    if (serial_port_.isOpen()) {
        serial_port_.close();
    }
}

bool SerialComm::isOpen() {
    std::lock_guard<std::mutex> lock(serial_mutex_);
    return serial_port_.isOpen();
}

void SerialComm::reconnectLoop() {
    while (running_) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        {
            std::lock_guard<std::mutex> lock(serial_mutex_);
            if (!serial_port_.isOpen()) {
                attemptReconnect();
            }
        }
    }
}

bool SerialComm::attemptReconnect() {
    try {
        serial_port_.setPort(port_);
        serial_port_.setBaudrate(baudrate_);
        serial::Timeout timeout = serial::Timeout::simpleTimeout(1000);
        serial_port_.setTimeout(timeout);
        serial_port_.open();
        
        if (serial_port_.isOpen()) {
            RCLCPP_INFO(rclcpp::get_logger("SerialComm"), "✅ Serial reconnected: %s @ %lu bps", port_.c_str(), baudrate_);
            return true;
        }
    } catch (const std::exception& e) {
        // 静默失败，继续尝试
    }
    return false;
}

bool SerialComm::sendFloatArrayCommand(const std::vector<float>& values, uint8_t cmd_id) {
    std::lock_guard<std::mutex> lock(serial_mutex_);
    
    if (!serial_port_.isOpen()) return false;

    // 现在 encodeFloatArray 接受 cmd_id 并返回最终帧（第三位为 cmd_id，第四位为数据长度固定为 10）
    std::vector<uint8_t> frame = encodeFloatArray(values, cmd_id);
    
    // Debug: 打印发送的数据
    std::string val_str;
    for (float v : values) val_str += std::to_string(v) + " ";
    
    std::string hex_str;
    char buf[4];
    // 打印每个字节的十六进制表示
    for (uint8_t b : frame) {
        snprintf(buf, sizeof(buf), "%02X ", b);
        hex_str += buf;
    }
    RCLCPP_INFO(rclcpp::get_logger("SerialComm"), "[DEBUG] Sending CMD_ID: %d | Data: %s| Raw: %s", cmd_id, val_str.c_str(), hex_str.c_str());
    
    try {
        size_t bytes_written = serial_port_.write(frame);
        return bytes_written == frame.size();
    } catch (const std::exception& e) {
        RCLCPP_ERROR(rclcpp::get_logger("SerialComm"), "Send error: %s", e.what());
        // 关闭串口以触发重连
        if (serial_port_.isOpen()) {
            serial_port_.close();
        }
        return false;
    }
}

std::vector<uint8_t> SerialComm::encodeFloatArray(const std::vector<float>& values, uint8_t cmd_id) {
    std::vector<uint8_t> frame;

    // 1. 编码 float 数组为 int16_t（缩放 1000）后拆成字节
    std::vector<uint8_t> data;
    for (float val : values) {
        int16_t scaled = static_cast<int16_t>(val * 1000);
        data.push_back(static_cast<uint8_t>((scaled >> 8) & 0xFF)); // 高字节
        data.push_back(static_cast<uint8_t>(scaled & 0xFF));        // 低字节
    }

    // 把数据长度固定为 10 字节：不足补 0，多余截断
    const size_t FIXED_DATA_LEN = 10;
    if (data.size() < FIXED_DATA_LEN) {
        data.resize(FIXED_DATA_LEN, 0);
    } else if (data.size() > FIXED_DATA_LEN) {
        data.resize(FIXED_DATA_LEN);
    }

    // 2. 帧头
    frame.push_back(protocol::FRAME_HEAD);
    frame.push_back(protocol::FRAME_HEAD_SEND);

    // 3. 第三位为 cmd_id（用户要求）
    frame.push_back(cmd_id);

    // 4. 数据长度固定写入为 10
    frame.push_back(static_cast<uint8_t>(FIXED_DATA_LEN));

    // 5. 数据内容（固定 10 字节）
    frame.insert(frame.end(), data.begin(), data.end());

    // 6. 校验和
    uint8_t checksum = protocol::calcChecksum(frame);
    frame.push_back(checksum);

    return frame;
}

// ============================================================================
// 机械臂坐标抓取控制协议 (FD FD 06 X_L X_H Y_L Y_H Z_L Z_H CHECKSUM)
// 帧长固定 10 字节，X/Y/Z 为 int16 小端序，单位 mm
// ============================================================================
std::vector<uint8_t> SerialComm::encodeArmTarget(int16_t x_mm, int16_t y_mm, int16_t z_mm,
                                                  int checksum_offset) {
    std::vector<uint8_t> frame;

    // 帧头 1, 2
    frame.push_back(0xFD);
    frame.push_back(0xFD);

    // 数据区长度 (固定 6 字节: X_L X_H Y_L Y_H Z_L Z_H)
    frame.push_back(0x06);

    // X 坐标 (int16, 小端序: 低字节在前)
    frame.push_back(static_cast<uint8_t>(x_mm & 0xFF));
    frame.push_back(static_cast<uint8_t>((x_mm >> 8) & 0xFF));

    // Y 坐标 (int16, 小端序)
    frame.push_back(static_cast<uint8_t>(y_mm & 0xFF));
    frame.push_back(static_cast<uint8_t>((y_mm >> 8) & 0xFF));

    // Z 坐标 (int16, 小端序)
    frame.push_back(static_cast<uint8_t>(z_mm & 0xFF));
    frame.push_back(static_cast<uint8_t>((z_mm >> 8) & 0xFF));

    // 校验和 = (前 9 字节累加和 + offset) 取低 8 位
    // offset 默认 0；调试时可设为非零值来匹配不同下位机实现
    uint8_t checksum = 0;
    for (size_t i = 0; i < 9; i++) {
        checksum += frame[i];
    }
    checksum = static_cast<uint8_t>((checksum + checksum_offset) & 0xFF);
    frame.push_back(checksum);

    return frame;
}

bool SerialComm::sendArmTargetCommand(int16_t x_mm, int16_t y_mm, int16_t z_mm,
                                       int checksum_offset) {
    std::lock_guard<std::mutex> lock(serial_mutex_);

    if (!serial_port_.isOpen()) return false;

    std::vector<uint8_t> frame = encodeArmTarget(x_mm, y_mm, z_mm, checksum_offset);

    // Debug: 打印发送的帧数据
    char buf[4];
    std::string hex_str;
    for (uint8_t b : frame) {
        snprintf(buf, sizeof(buf), "%02X ", b);
        hex_str += buf;
    }
    RCLCPP_INFO(rclcpp::get_logger("SerialComm"),
        "[ARM] Sending target: (%d, %d, %d) mm | checksum_offset=%d | Raw: %s",
        x_mm, y_mm, z_mm, checksum_offset, hex_str.c_str());

    try {
        size_t bytes_written = serial_port_.write(frame);
        return bytes_written == frame.size();
    } catch (const std::exception& e) {
        RCLCPP_ERROR(rclcpp::get_logger("SerialComm"), "Arm send error: %s", e.what());
        if (serial_port_.isOpen()) {
            serial_port_.close();
        }
        return false;
    }
}

std::vector<float> SerialComm::readFloatArrayResponse() {
    std::vector<float> result;
    
    std::lock_guard<std::mutex> lock(serial_mutex_);
    
    if (!serial_port_.isOpen()) return result;

    try {
        size_t available = serial_port_.available();
        if (available < 5) return result;  // 至少包含帧头+长度+校验

        std::vector<uint8_t> buffer;
        serial_port_.read(buffer, available);

        for (size_t i = 0; i + 4 < buffer.size(); ++i) {
            if (buffer[i] == protocol::FRAME_HEAD) {
                uint8_t frame_type = buffer[i + 1];
                if (frame_type == protocol::FRAME_HEAD_READ) {  // 接收帧
                    uint8_t len = buffer[i + 2];
                    if (i + 3 + len >= buffer.size()) break;  // 数据未接收完整

                    std::vector<uint8_t> frame(buffer.begin() + i, buffer.begin() + i + 4 + len);

                    // 校验校验和
                    uint8_t expected_checksum = frame.back();
                    frame.pop_back();
                    uint8_t calc = protocol::calcChecksum(frame);
                    if (expected_checksum != calc) {
                        std::cerr << "❌ Checksum mismatch\n";
                        continue;
                    }

                    // 解析 float 数组
                    for (size_t j = 3; j < 3 + len; j += 2) {
                        int16_t raw = (frame[j] << 8) | frame[j + 1];
                        float val = static_cast<float>(raw) / 1000.0f;
                        result.push_back(val);
                    }

                    break;  // 找到一帧后退出
                }
            }
        }
    } catch (const std::exception& e) {
        RCLCPP_ERROR(rclcpp::get_logger("SerialComm"), "Read error: %s", e.what());
        // 关闭串口以触发重连
        if (serial_port_.isOpen()) {
            serial_port_.close();
        }
    }

    return result;
}
