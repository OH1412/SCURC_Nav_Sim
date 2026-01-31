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

    // send
    bool sendFloatArrayCommand(const std::vector<float>& values, uint8_t cmd_id);
    // receive
    std::vector<float> readFloatArrayResponse();


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
};

#endif
