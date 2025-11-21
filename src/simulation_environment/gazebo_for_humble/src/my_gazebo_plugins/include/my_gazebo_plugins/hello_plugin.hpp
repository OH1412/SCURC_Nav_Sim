#pragma once

#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <gazebo/common/common.hh>
#include <iostream>

namespace gazebo
{
    class HelloPlugin : public ModelPlugin
    {
    public:
        HelloPlugin() = default;
        ~HelloPlugin() = default;

        // 加载插件时调用
        void Load(physics::ModelPtr _model, sdf::ElementPtr _sdf) override;

        // 每次世界更新时调用
        void OnUpdate();

    private:
        physics::ModelPtr model_;               // 机器人模型
        event::ConnectionPtr updateConnection_; // 连接到世界更新事件
    };
}
