# 单步任务
string nav_id          # 导航航点编号（外部 nav_waypoint id）
uint8 arm_point_id     # 0~7=抓取点, 8~15=放置点; 255=未指定
uint8 arm_action       # 0=无, 1=Pick, 2=Place

uint8 ARM_NONE=0
uint8 ARM_PICK=1
uint8 ARM_PLACE=2
