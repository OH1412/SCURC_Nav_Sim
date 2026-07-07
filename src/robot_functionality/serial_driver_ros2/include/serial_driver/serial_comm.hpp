#ifndef SERIAL_COMM_HPP
#define SERIAL_COMM_HPP

#include <string>
#include <vector>
#include <cstdint>
#include <serial/serial.h>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>

namespace rclcpp {
class Node;
}

// 机械臂 ACK 帧解析结果
struct ArmAck {
    bool valid = false;       // 帧解析成功
    uint8_t state = 0x00;     // 0x01=Pick完成, 0x02=Place完成
    uint8_t result = 0x00;    // 0x00=成功, 0x01=失败
};

class SerialComm {
public:
    SerialComm(const std::string& port, unsigned long baudrate, rclcpp::Node * log_node = nullptr);
    ~SerialComm();

    // send (existing protocol)
    bool sendFloatArrayCommand(const std::vector<float>& values, uint8_t cmd_id);
    // receive
    std::vector<float> readFloatArrayResponse();

    // arm control protocol (FD FD 07 ctrl X_L X_H Y_L Y_H Z_L Z_H CHECKSUM)
    // control: 0x01=Pick(吸取), 0x02=Place(放置)
    // checksum_offset: 调试验证用，默认 0。非零时校验和 = (累加和 + offset) & 0xFF
    bool sendArmTargetCommand(uint8_t control, int16_t x_mm, int16_t y_mm, int16_t z_mm,
                              int checksum_offset = 0);

    // ACK 接收 (FE FE 03 state result CHECKSUM)
    ArmAck readArmAck();

    // 清空接收缓冲区 (发送新命令前调用，丢弃陈旧 ACK)
    void flushReceiveBuffer();


private:
    serial::Serial serial_port_;
    std::string port_;
    unsigned long baudrate_;
    
    // 自动重连相关
    std::thread reconnect_thread_;
    std::atomic<bool> running_;
    std::mutex serial_mutex_;
    rclcpp::Node * log_node_ = nullptr;
    
    bool isOpen();
    void reconnectLoop();
    bool attemptReconnect();
    std::vector<uint8_t> encodeFloatArray(const std::vector<float>& values, uint8_t cmd_id);
    std::vector<uint8_t> encodeArmTarget(uint8_t control, int16_t x_mm, int16_t y_mm, int16_t z_mm,
                                        int checksum_offset = 0);
};

#endif
