#include "my_gazebo_plugins/hello_plugin.hpp"
#include <gazebo/common/Events.hh>

namespace gazebo
{
    void HelloPlugin::Load(physics::ModelPtr _model, sdf::ElementPtr _sdf)
    {
        // 获取机器人模型
        this->model_ = _model;

        // 每次世界更新时调用 OnUpdate()
        this->updateConnection_ = event::Events::ConnectWorldUpdateBegin(
            std::bind(&HelloPlugin::OnUpdate, this));
    }

    void HelloPlugin::OnUpdate()
    {
        // 每次世界更新时输出 Hello, World!
        std::cout << "Hello, World!" << std::endl;
    }

    // 插件注册
    GZ_REGISTER_MODEL_PLUGIN(HelloPlugin)
}
