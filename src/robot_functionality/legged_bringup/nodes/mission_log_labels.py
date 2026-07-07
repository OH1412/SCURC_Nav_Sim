"""Chinese labels for mission session log output."""

from __future__ import annotations

LEVEL_LABELS = {
    'INFO': '信息',
    'ERROR': '错误',
}

SOURCE_LABELS = {
    'mission_session_logger': '任务日志器',
    'stand_up_sender': '站立发送',
    'wait_for_ros_condition': '就绪门控',
    'aft_to_pose_offset_node': '重定位转发',
    'arm_pose_broadcaster': '机械臂位姿广播',
    'mission_bt_node': '任务行为树',
    'Nav2PoseNode': '导航节点',
    'ArmActionNode': '机械臂动作',
    'serial_cmd_sender': '串口指令发送',
    'SerialComm': '串口通信',
    'cmd_vel_udp_bridge': 'UDP速度桥接',
}

EVENT_LABELS = {
    'LAUNCH_SESSION_START': '任务会话开始',
    'LAUNCH_SESSION_END': '任务会话结束',
    'READINESS_GATE_PASSED': '就绪门控通过',
    'READINESS_GATE_TIMEOUT': '就绪门控超时',
    'RELOC_READY': '重定位转发就绪',
    'STANDUP_WAIT_RELOC_START': '开始等待重定位',
    'STANDUP_SKIP_RELOC': '跳过重定位等待',
    'STANDUP_RELOC_RECEIVED': '收到重定位信号',
    'STANDUP_RELOC_TIMEOUT': '重定位等待超时',
    'STANDUP_UDP_SENT': '发送站立UDP指令',
    'STANDUP_UDP_FAILED': '站立UDP发送失败',
    'STANDUP_WAIT_COMPLETE': '站立等待完成',
    'STANDUP_DONE_PUBLISHED': '发布站立完成信号',
    'SERIAL_READY': '串口驱动就绪',
    'SERIAL_OPEN_FAILED': '串口打开失败',
    'SERIAL_RECONNECTED': '串口重连成功',
    'ARM_SEND_ERROR': '机械臂串口发送错误',
    'ARM_ACK_READ_ERROR': '机械臂ACK读取错误',
    'ARM_COMMAND_RECEIVED': '收到机械臂指令',
    'ARM_COMMAND_SEND_FAILED': '机械臂指令发送失败',
    'ARM_STATUS_PUBLISHED': '发布机械臂ACK状态',
    'UDP_BRIDGE_STARTED': 'UDP速度桥接启动',
    'BT_XML_CONFIGURED': '行为树XML已配置',
    'BT_LOADED': '行为树加载完成',
    'BT_LOAD_FAILED': '行为树加载失败',
    'BT_XML_LOAD_FAILED': '行为树XML加载失败',
    'WAYPOINTS_LOADED': '航点YAML加载完成',
    'WAYPOINTS_LOAD_FAILED': '航点YAML加载失败',
    'NAV2_LIFECYCLE_ACTIVE': 'Nav2生命周期已激活',
    'NAV2_LIFECYCLE_TIMEOUT': 'Nav2生命周期等待超时',
    'NAV2_ACTION_READY': '导航动作服务就绪',
    'NAV2_ACTION_TIMEOUT': '导航动作服务超时',
    'BT_TICK_START': '行为树开始执行',
    'BT_FINISHED_SUCCESS': '行为树执行成功',
    'BT_FINISHED_FAILURE': '行为树执行失败',
    'NAV_STEP_START': '开始导航步骤',
    'NAV_GOAL_SENT': '发送导航目标',
    'NAV_GOAL_SEND_FAILED': '导航目标发送失败',
    'NAV_GOAL_REJECTED': '导航目标被拒绝',
    'NAV_PROGRESS': '导航进行中',
    'NAV_REACHED_PUBLISHED': '发布导航到达',
    'NAV_SUCCEEDED': '导航成功',
    'NAV_ABORTED': '导航中止',
    'NAV_CANCELED': '导航取消',
    'NAV_WAYPOINT_TIMEOUT': '等待导航航点超时',
    'NAV_REACHED_RECEIVED': '收到导航到达通知',
    'ARM_POSE_REQUEST_RECEIVED': '收到机械臂位姿请求',
    'ARM_WAYPOINT_INVALID_POINT': '机械臂点位编号无效',
    'ARM_WAYPOINT_MISSING_ENTRY': '机械臂点位配置缺失',
    'ARM_WAYPOINT_ROLE_MISMATCH': '机械臂点位角色不匹配',
    'ARM_WAYPOINT_NO_TARGET': '机械臂点位无目标坐标',
    'ARM_WAYPOINT_NO_MAP_TARGET': '机械臂点位缺少地图目标',
    'ARM_WAYPOINT_PUBLISHED': '发布机械臂航点',
    'ARM_STEP_START': '开始机械臂步骤',
    'ARM_POSE_REQUEST_PUBLISHED': '发布机械臂位姿请求',
    'ARM_COMMAND_SENT': '发送机械臂控制指令',
    'ARM_COMMAND_NO_SUBSCRIBER': '机械臂指令无订阅者',
    'ARM_WAYPOINT_TIMEOUT': '等待机械臂航点超时',
    'ARM_ACK_SUCCESS': '机械臂动作确认成功',
    'ARM_ACK_FAILURE': '机械臂动作确认失败',
    'ARM_ACK_TIMEOUT': '机械臂动作确认超时',
}


def level_label(level: str) -> str:
    return LEVEL_LABELS.get(level, level)


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def event_label(event_id: str) -> str:
    return EVENT_LABELS.get(event_id, event_id)
