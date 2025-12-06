### height_control_action--高度控制插件
#### 「到目标高度停」上升到指定高度后，自动停止升降运动，保持当前高度悬停 / 静止
在robot_functionality/r2_bringup/behavior_tree/test_control_height_bt.xml中设置target_height\
使用时需要在/robot_functionality/r2_bringup/params/nav2_params.yaml文件bt_navigator 部分加入 
```bash
- behavior_ext_plugins 
```
