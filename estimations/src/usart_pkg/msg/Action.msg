# Action.msg

# 动作定义
uint8 ACTION_STAND          = 1
uint8 ACTION_FORWARD        = 2
uint8 ACTION_BACKWARD       = 9
uint8 ACTION_TURN_LEFT      = 4
uint8 ACTION_TURN_RIGHT     = 5

# 速度等级定义
uint8 SPEED_LOW    = 0
uint8 SPEED_MEDIUM = 1
uint8 SPEED_HIGH   = 2

# 消息字段
uint8 action_id
uint8 speed_level
