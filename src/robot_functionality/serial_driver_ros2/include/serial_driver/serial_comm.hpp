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

class SerialComm {
public:
    SerialComm(const std::string& port, unsigned long baudrate);
    ~SerialComm();

    // send (existing protocol)
    bool sendFloatArrayCommand(const std::vector<float>& values, uint8_t cmd_id);
    // receive
    std::vector<float> readFloatArrayResponse();

    // arm control protocol (FD FD 06 X_L X_H Y_L Y_H Z_L Z_H CHECKSUM)
    // checksum_offset: 调试验证用，默认 0。非零时校验和 = (累加和 + offset) & 0xFF
    bool sendArmTargetCommand(int16_t x_mm, int16_t y_mm, int16_t z_mm,
                              int checksum_offset = 0);


private:
    serial::Serial serial_port_;
    std::string port_;
    unsigned long baudrate_;
    
    // 自动重连相关
    std::thread reconnect_thread_;
    std::atomic<bool> running_;
    std::mutex serial_mutex_;
    
    bool isOpen();
    void reconnectLoop();
    bool attemptReconnect();
    std::vector<uint8_t> encodeFloatArray(const std::vector<float>& values, uint8_t cmd_id);
    std::vector<uint8_t> encodeArmTarget(int16_t x_mm, int16_t y_mm, int16_t z_mm,
                                        int checksum_offset = 0);
};

#endif
