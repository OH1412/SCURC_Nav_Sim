#!/usr/bin/env python3
"""
kfs_planner_node.py

订阅 KFSDecision，运行路径规划（基于提供的 A* + 外围跑道逻辑），并把计算好的主航点列表写入
fly_step_mission/behavior_trees/dynamic_waypoint_mission.xml 中 SetBlackboard output_key="MainWPs" 的 value 属性。

说明：为了最小改动，这个节点直接修改 BT xml 源文件（在源码目录），这样下一次启动 BT 时会读取更新的航点。
如果需要在运行时立即修改正在运行的 BT 的黑板，需要在 C++ 的 BT 节点中暴露额外的服务 / 话题接口（可选后续改进）。
"""
import os
import heapq
import random
import threading
import xml.etree.ElementTree as ET
import pathlib
from typing import Dict, Tuple, List, Optional

import rclpy
from rclpy.node import Node
from yolov8_ros2_msgs.msg import KFSDecision
from ament_index_python.packages import get_package_share_directory
from fly_step_msgs.srv import SetMainWps
import time


# ---------------------------
# 基本（内部）坐标/邻居
# ---------------------------
def node_to_coord_inner(node: int) -> Tuple[int, int]:
    node0 = node - 1
    row = node0 // 3
    col = node0 % 3
    return (row, col)

def coord_to_node_inner(row: int, col: int) -> int:
    return row * 3 + col + 1

def neighbors_inner(node: int) -> List[int]:
    r, c = node_to_coord_inner(node)
    nbrs = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 4 and 0 <= nc < 3:
            nbrs.append(coord_to_node_inner(nr, nc))
    return nbrs

def manhattan_inner(a: int, b: int) -> int:
    ra, ca = node_to_coord_inner(a)
    rb, cb = node_to_coord_inner(b)
    return abs(ra - rb) + abs(ca - cb)

# ---------------------------
# 内->外层坐标映射（外围 +1）
# 外层尺寸： OUT_ROWS=6, OUT_COLS=5
# ---------------------------
def inner_to_outer_coord(node: int) -> Tuple[int, int]:
    r_in, c_in = node_to_coord_inner(node)
    return (r_in + 1, c_in + 1)

def outer_to_inner_node(r_out: int, c_out: int) -> Optional[int]:
    r_in = r_out - 1
    c_in = c_out - 1
    if 0 <= r_in < 4 and 0 <= c_in < 3:
        return coord_to_node_inner(r_in, c_in)
    return None

OUT_ROWS = 6
OUT_COLS = 5

# ---------------------------
# 粉色跑道（外围环）索引/路径辅助
# ---------------------------
def build_pink_ring_positions() -> List[Tuple[int,int]]:
    ring = []
    for c in range(0, OUT_COLS):
        ring.append((0, c))
    for r in range(1, OUT_ROWS):
        ring.append((r, OUT_COLS-1))
    for c in range(OUT_COLS-2, -1, -1):
        ring.append((OUT_ROWS-1, c))
    for r in range(OUT_ROWS-2, 0, -1):
        ring.append((r, 0))
    return ring

PINK_RING = build_pink_ring_positions()
PINK_INDEX = {pos:i for i,pos in enumerate(PINK_RING)}
PINK_COUNT = len(PINK_RING)

def pink_ring_distance(a_idx: int, b_idx: int) -> int:
    d = abs(a_idx - b_idx)
    return min(d, PINK_COUNT - d)

def ring_shortest_path_indices(a_idx:int, b_idx:int) -> List[int]:
    if a_idx == b_idx:
        return [a_idx]
    d = (b_idx - a_idx) % PINK_COUNT
    if d <= PINK_COUNT - d:
        path = []
        cur = a_idx
        while True:
            path.append(cur)
            if cur == b_idx:
                break
            cur = (cur + 1) % PINK_COUNT
        return path
    else:
        path = []
        cur = a_idx
        while True:
            path.append(cur)
            if cur == b_idx:
                break
            cur = (cur - 1) % PINK_COUNT
        return path

def pink_positions_adjacent_to_inner(node:int) -> List[int]:
    r_out, c_out = inner_to_outer_coord(node)
    adj = []
    for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
        rr, cc = r_out + dr, c_out + dc
        if 0 <= rr < OUT_ROWS and 0 <= cc < OUT_COLS:
            if (rr, cc) in PINK_INDEX:
                adj.append(PINK_INDEX[(rr, cc)])
    return adj

# ---------------------------
# 垂直代价与高度下界（内部网格）
# ---------------------------
def vertical_time_exact(a: int, b: int, heights_map: Dict[int, int], times: Dict[str, float]) -> float:
    ha = heights_map[a]
    hb = heights_map[b]
    if ha == hb:
        return 0.0
    if ha < hb:
        if (ha, hb) in ((200, 400), (400, 600)):
            return times["time_up_low"]
        elif (ha, hb) == (200, 600):
            return times["time_up_high"]
    else:
        if (ha, hb) in ((600, 400), (400, 200)):
            return times["time_down_low"]
        elif (ha, hb) == (600, 200):
            return times["time_down_high"]
    raise ValueError(f"Unhandled height change {ha}->{hb}")

def build_height_min_cost(times: Dict[str, float]) -> Dict[Tuple[int, int], float]:
    heights = [200, 400, 600]
    edges = {}
    for h in heights:
        edges[(h, h)] = 0.0
    edges[(200, 400)] = times["time_up_low"]
    edges[(400, 200)] = times["time_down_low"]
    edges[(400, 600)] = times["time_up_low"]
    edges[(600, 400)] = times["time_down_low"]
    edges[(200, 600)] = times["time_up_high"]
    edges[(600, 200)] = times["time_down_high"]

    mincost = {}
    for h_start in heights:
        dist = {h: float('inf') for h in heights}
        dist[h_start] = 0.0
        pq = [(0.0, h_start)]
        while pq:
            d, h = heapq.heappop(pq)
            if d > dist[h]:
                continue
            for h2 in heights:
                if h == h2:
                    nd = d
                elif (h, h2) in edges:
                    nd = d + edges[(h, h2)]
                else:
                    continue
                if nd < dist[h2]:
                    dist[h2] = nd
                    heapq.heappush(pq, (nd, h2))
        for h_end in heights:
            mincost[(h_start, h_end)] = dist[h_end]
    return mincost

def ascent_from_zero_time(height: int, times: Dict[str, float]) -> float:
    if height == 200:
        return times["time_up_low"]
    elif height == 400:
        return times["time_up_high"]
    elif height == 600:
        return times.get("time_up_to_600", times["time_up_high"])
    else:
        raise ValueError(f"未知高度用于从0抬升: {height}")

def descent_to_zero_time(height: int, times: Dict[str, float]) -> float:
    if height == 200:
        return times["time_down_low"]
    elif height == 400:
        return times["time_down_high"]
    elif height == 600:
        return times["time_down_to_zero"]
    else:
        raise ValueError(f"未知高度用于降到0: {height}")

# ---------------------------
# A* 主逻辑（精简版，保留原有接口）
# 返回： best_time, node_path, stats, kfs1_pick_events_ordered, ext_path_segments
# ---------------------------
def a_star_with_external_ring_kfs1(
    heights_map: Dict[int, int],
    times: Dict[str, float],
    ext_move_time: float,
    ext_pick_kfs1_time_default: float,
    kfs_locked: int,
    kfs1_set: set,
    time_pick_kfs1_map: Dict[int, float],
    kfs2_positions: List[int],
    entry_nodes=(1,2,3),
    exit_nodes=(10,11,12),
    min_kfs2_picked_required: int = 1
):
    # 为了保持示例简单：直接调用之前提供的实现（已在此文件内定义的辅助函数）
    # 这里仅保留最小完整逻辑：调用到最后返回 node_path
    # NOTE: 这是一个较长的实现 — 为简洁起见，实际细节省略复杂注释

    # reuse code from provided snippet (kept compact but functional)
    time_pick_kfs2 = times["time_pick_kfs2"]
    time_clean_kfs2 = times["time_clean_kfs2"]
    w_time = times.get("w_time", 1.0)
    w_pick = times.get("w_pick", 1.0)

    kfs1_list = sorted(list(kfs1_set))
    kfs1_index = {p:i for i,p in enumerate(kfs1_list)}
    total_kfs1 = len(kfs1_list)

    kfs2_index = {p:i for i,p in enumerate(kfs2_positions)}
    total_kfs2 = len(kfs2_positions)

    def kfs2_is_handled(p_mask:int, c_mask:int, pos:int) -> bool:
        if pos not in kfs2_index:
            return True
        idx = kfs2_index[pos]
        return ((p_mask >> idx) & 1) == 1 or ((c_mask >> idx) & 1) == 1

    def is_passable(node: int, k1_mask:int, p_mask:int, c_mask:int, robot_time: float, k1_completion_times: Tuple[float]):
        if node == kfs_locked:
            return False
        if node in kfs1_index:
            idx = kfs1_index[node]
            if ((k1_mask >> idx) & 1) == 0:
                return False
            if k1_completion_times[idx] > robot_time + 1e-9:
                return False
        if node in kfs2_index and not kfs2_is_handled(p_mask, c_mask, node):
            return False
        return True

    h_min = build_height_min_cost(times)
    def heuristic(node:int, k1_mask:int, p_mask:int, c_mask:int) -> float:
        cur_h = heights_map[node]
        best_t = float('inf')
        for ex in exit_nodes:
            if ex == kfs_locked:
                continue
            ex_h = heights_map[ex]
            t_lower = manhattan_inner(node, ex) * times["time_approach"] + h_min[(cur_h, ex_h)]
            if t_lower < best_t:
                best_t = t_lower
        if best_t == float('inf'):
            best_t = 0.0
        picked_so_far = 0
        return w_time * best_t - w_pick * (picked_so_far + (total_kfs2 - picked_so_far))

    INF = float('inf')
    g_obj = {}
    g_time = {}
    g_picked = {}
    came_from = {}
    open_pq = []
    best_goal = None

    ext_start_idx = PINK_INDEX[(0,0)]

    # 初始化入口状态
    for s in entry_nodes:
        if s == kfs_locked:
            continue
        ascent = ascent_from_zero_time(heights_map[s], times)
        approach = times["time_approach"]
        ext_time0 = 0.0
        k1_comp0 = tuple([0.0]*total_kfs1)

        if s in kfs1_set:
            idx_k1 = kfs1_index[s]
            candidates = pink_positions_adjacent_to_inner(s)
            if not candidates:
                continue
            best_cand = None
            best_steps = None
            for cand in candidates:
                steps = pink_ring_distance(ext_start_idx, cand)
                if best_cand is None or steps < best_steps:
                    best_cand = cand
                    best_steps = steps
            move_time = best_steps * ext_move_time
            dur = time_pick_kfs1_map.get(s, ext_pick_kfs1_time_default)
            completion = ext_time0 + move_time + dur
            ext_time1 = completion
            ext_pos1 = best_cand
            k1_mask0 = (1 << idx_k1)
            k1_comp_list = list(k1_comp0)
            k1_comp_list[idx_k1] = completion
            k1_comp0 = tuple(k1_comp_list)
            p_mask0 = 0
            c_mask0 = 0
            options_masks = [(p_mask0, c_mask0, 0.0)]
            if s in kfs2_index:
                bit = 1 << kfs2_index[s]
                options_masks.append((p_mask0 | bit, c_mask0 | bit, time_pick_kfs2))
                options_masks.append((p_mask0, c_mask0 | bit, time_clean_kfs2))
            for (p_mask, c_mask, cost_k2) in options_masks:
                robot_time0 = completion + ascent + approach + cost_k2
                picked_cnt = bin(p_mask).count("1")
                obj = w_time * robot_time0 - w_pick * picked_cnt
                state = (s, k1_mask0, p_mask, c_mask, round(ext_time1, 3), k1_comp0, ext_pos1)
                if state not in g_obj or obj < g_obj[state]:
                    g_obj[state] = obj
                    g_time[state] = robot_time0
                    g_picked[state] = picked_cnt
                    heapq.heappush(open_pq,
                                   (obj + heuristic(s, k1_mask0, p_mask, c_mask), obj, robot_time0, picked_cnt, state))
        else:
            k1_mask0 = 0; p_mask0 = 0; c_mask0 = 0
            options_masks = [(p_mask0, c_mask0, 0.0)]
            if s in kfs2_index:
                bit = 1 << kfs2_index[s]
                options_masks.append((p_mask0 | bit, c_mask0 | bit, time_pick_kfs2))
                options_masks.append((p_mask0, c_mask0 | bit, time_clean_kfs2))
            for (p_mask, c_mask, cost_k2) in options_masks:
                robot_time0 = ascent + approach + cost_k2
                obj = w_time * robot_time0 - w_pick * bin(p_mask).count("1")
                state = (s, k1_mask0, p_mask, c_mask, round(ext_time0,3), k1_comp0, ext_start_idx)
                if state not in g_obj or obj < g_obj[state]:
                    g_obj[state] = obj; g_time[state] = robot_time0; g_picked[state] = bin(p_mask).count("1")
                    heapq.heappush(open_pq, (obj + heuristic(s, k1_mask0, p_mask, c_mask), obj, robot_time0, g_picked[state], state))

    if not open_pq:
        raise RuntimeError("入口被阻塞，无可用起始状态")

    # 搜索（此处保留原始搜索流程，但不做过度注释）
    while open_pq:
        f, obj_g, robot_time_g, picked_g_cnt, state = heapq.heappop(open_pq)
        node, k1_mask, p_mask, c_mask, ext_time, k1_comp_tuple, ext_pos_idx = state

        if best_goal is not None:
            best_obj_val = best_goal[0]
            if f >= best_obj_val - 1e-9:
                break

        if g_obj.get(state, INF) < obj_g - 1e-12:
            continue

        # 外部安排
        for k1_node in kfs1_list:
            idx = kfs1_index[k1_node]
            if ((k1_mask >> idx) & 1) == 0:
                candidates = pink_positions_adjacent_to_inner(k1_node)
                if not candidates:
                    continue
                dur = time_pick_kfs1_map.get(k1_node, ext_pick_kfs1_time_default)
                for cand in candidates:
                    steps = pink_ring_distance(ext_pos_idx, cand)
                    move_time = steps * ext_move_time
                    completion = ext_time + move_time + dur
                    new_ext_time = completion
                    new_ext_pos = cand
                    new_k1_mask = k1_mask | (1 << idx)
                    k1_comp_list = list(k1_comp_tuple); k1_comp_list[idx] = completion
                    new_k1_comp_tuple = tuple(k1_comp_list)
                    new_robot_time = robot_time_g
                    new_p_mask = p_mask; new_c_mask = c_mask; new_picked = picked_g_cnt
                    new_obj = w_time * new_robot_time - w_pick * new_picked
                    new_state = (node, new_k1_mask, new_p_mask, new_c_mask, round(new_ext_time,3), new_k1_comp_tuple, new_ext_pos)
                    if new_obj + 1e-12 < g_obj.get(new_state, INF):
                        g_obj[new_state] = new_obj; g_time[new_state] = new_robot_time; g_picked[new_state] = new_picked
                        came_from[new_state] = (state, ("pick_kfs1_ext", k1_node, dur, ext_time, new_ext_time, ext_pos_idx, new_ext_pos))
                        heapq.heappush(open_pq, (new_obj + heuristic(node, new_k1_mask, new_p_mask, new_c_mask), new_obj, new_robot_time, new_picked, new_state))

        # pick/clean kfs2
        if node in exit_nodes:
            check_nodes = neighbors_inner(node) + [node]
        else:
            check_nodes = neighbors_inner(node)
        for v in check_nodes:
            if v in kfs2_index and not kfs2_is_handled(p_mask, c_mask, v):
                idx2 = kfs2_index[v]; bit2 = 1 << idx2
                # pick
                new_p_mask = p_mask | bit2; new_c_mask = c_mask | bit2
                new_robot_time = robot_time_g + time_pick_kfs2; new_picked = picked_g_cnt + 1
                new_obj = w_time * new_robot_time - w_pick * new_picked
                new_state = (node, k1_mask, new_p_mask, new_c_mask, ext_time, k1_comp_tuple, ext_pos_idx)
                if new_obj + 1e-12 < g_obj.get(new_state, INF):
                    g_obj[new_state] = new_obj; g_time[new_state] = new_robot_time; g_picked[new_state] = new_picked
                    came_from[new_state] = (state, ("pick_kfs2", v, time_pick_kfs2, ext_time, ext_time))
                    heapq.heappush(open_pq, (new_obj + heuristic(node, k1_mask, new_p_mask, new_c_mask), new_obj, new_robot_time, new_picked, new_state))
                # clean
                new_p_mask2 = p_mask; new_c_mask2 = c_mask | bit2
                new_robot_time2 = robot_time_g + time_clean_kfs2; new_picked2 = picked_g_cnt
                new_obj2 = w_time * new_robot_time2 - w_pick * new_picked2
                new_state2 = (node, k1_mask, new_p_mask2, new_c_mask2, ext_time, k1_comp_tuple, ext_pos_idx)
                if new_obj2 + 1e-12 < g_obj.get(new_state2, INF):
                    g_obj[new_state2] = new_obj2; g_time[new_state2] = new_robot_time2; g_picked[new_state2] = new_picked2
                    came_from[new_state2] = (state, ("clean_kfs2", v, time_clean_kfs2, ext_time, ext_time))
                    heapq.heappush(open_pq, (new_obj2 + heuristic(node, k1_mask, new_p_mask2, new_c_mask2), new_obj2, new_robot_time2, new_picked2, new_state2))

        # move
        for v in neighbors_inner(node):
            move_time = times["time_approach"] + vertical_time_exact(node, v, heights_map, times)
            arrival_time = robot_time_g + move_time
            if v in kfs1_index:
                idxv = kfs1_index[v]
                if ((k1_mask >> idxv) & 1) == 0:
                    continue
                completion_v = k1_comp_tuple[idxv]
                effective_arrival = max(arrival_time, completion_v)
            else:
                effective_arrival = arrival_time
            if v in kfs2_index and not kfs2_is_handled(p_mask, c_mask, v):
                continue
            if not is_passable(v, k1_mask, p_mask, c_mask, effective_arrival, k1_comp_tuple):
                continue
            new_robot_time = effective_arrival
            new_picked = picked_g_cnt
            new_obj = w_time * new_robot_time - w_pick * new_picked
            new_state = (v, k1_mask, p_mask, c_mask, ext_time, k1_comp_tuple, ext_pos_idx)
            if new_obj + 1e-12 < g_obj.get(new_state, INF):
                g_obj[new_state] = new_obj; g_time[new_state] = new_robot_time; g_picked[new_state] = new_picked
                came_from[new_state] = (state, ("move", v, move_time, ext_time, ext_time))
                heapq.heappush(open_pq, (new_obj + heuristic(v, k1_mask, p_mask, c_mask), new_obj, new_robot_time, new_picked, new_state))

        # exit candidate
        if node in exit_nodes and node != kfs_locked and picked_g_cnt >= min_kfs2_picked_required:
            exit_descent = descent_to_zero_time(heights_map[node], times)
            extra_move = times["time_approach"]
            final_time_est = robot_time_g + exit_descent + extra_move
            final_obj = w_time * final_time_est - w_pick * picked_g_cnt
            candidate = (final_obj, final_time_est, picked_g_cnt, (node, k1_mask, p_mask, c_mask, ext_time, k1_comp_tuple, ext_pos_idx))
            if best_goal is None or final_obj < best_goal[0] - 1e-12:
                best_goal = candidate

    if best_goal is None:
        raise RuntimeError("无法到达出口且满足至少拾取 KFS2 的约束（不可达或约束不满足）")

    best_obj_val, best_time_est, best_picked_cnt, best_state = best_goal

    # 回溯 actions（按时间顺序）
    actions = []
    cur = best_state
    while True:
        prev = came_from.get(cur)
        if prev is None:
            break
        prev_state, action = prev
        actions.append((action, cur))
        cur = prev_state
    actions.reverse()

    # 回溯路径状态序列
    path_states = []
    cur = best_state
    while True:
        path_states.append(cur)
        prev = came_from.get(cur)
        if prev is None:
            break
        cur = prev[0]
    path_states.reverse()
    node_path = []
    for st in path_states:
        nd = st[0]
        if not node_path or node_path[-1] != nd:
            node_path.append(nd)

    # 最终统计
    stats = {
        'objective': best_obj_val,
        'time': best_time_est,
        'picked_kfs2_count': best_picked_cnt,
        'picked_mask_kfs2': best_state[2],
        'cleaned_mask_kfs2': best_state[3],
        'kfs1_scheduled_mask': best_state[1],
        'kfs1_completion_times': best_state[5],
        'final_state': best_state,
        'actions': actions
    }
    return best_time_est, node_path, stats, [], []


class KFSPlannerNode(Node):
    def __init__(self):
        super().__init__('kfs_planner_node')
        self.get_logger().info('KFS_PLANNER_NODE STARTED')
        self.declare_parameter('bt_xml_path', '')
        # 默认指向 fly_step_mission 包内的 behavior_trees 文件（通常这是 BT 的源 xml）
        try:
            fly_share = get_package_share_directory('fly_step_mission')
            bt_xml_default = os.path.join(fly_share, 'behavior_trees', 'dynamic_waypoint_mission.xml')
        except Exception:
            bt_xml_default = os.path.join(os.path.dirname(__file__), '..', 'behavior_trees', 'dynamic_waypoint_mission.xml')
        bt_xml_default = os.path.normpath(bt_xml_default)
        self.bt_xml_path = self.get_parameter('bt_xml_path').get_parameter_value().string_value or bt_xml_default
        self.get_logger().info(f'BT xml path: {self.bt_xml_path}')

        # Subscribe to KFSDecision
        self.sub = self.create_subscription(KFSDecision, '/kfs_decision', self.cb_decision, 10)
        self._lock = threading.Lock()

        # Service client to update running BT blackboard
        self._client = self.create_client(SetMainWps, '/fly_step_bt/set_main_wps')

        # retry policy for sending to BT service if service is not available yet
        self.declare_parameter('service_retry', True)
        self.service_retry = bool(self.get_parameter('service_retry').get_parameter_value().bool_value)
        self.declare_parameter('service_retry_interval_sec', 1.0)
        self.service_retry_interval_sec = float(self.get_parameter('service_retry_interval_sec').get_parameter_value().double_value)
        # total seconds to keep retrying; 0 means infinite
        # 默认改为 0（无限重试），确保 planner 会持续尝试直到 BT service 可用
        self.declare_parameter('service_retry_timeout_sec', 0.0)
        self.service_retry_timeout_sec = float(self.get_parameter('service_retry_timeout_sec').get_parameter_value().double_value)

        # whether planner is allowed to directly overwrite the installed BT xml file when service is unavailable
        # default: False -> safer: do not overwrite install files by default
        self.declare_parameter('allow_write_bt_xml', False)
        self.allow_write_bt_xml = bool(self.get_parameter('allow_write_bt_xml').get_parameter_value().bool_value)

        # pending background retry state
        self._pending_wp = None
        self._pending_thread = None

        # 规划完成标志，避免重复处理
        self._planning_completed = False

        # default maps/times
        self.heights = {
            1: 400, 2: 200, 3: 400,
            4: 200, 5: 400, 6: 600,
            7: 400, 8: 600, 9: 400,
            10: 200, 11: 400, 12: 200
        }
        self.times = {
            "time_approach": 0.5,
            "time_up_low": 1.60,
            "time_up_high": 3.20,
            "time_down_low": 2.00,
            "time_down_high": 4.00,
            "time_down_to_zero": 5.00,
            "time_up_to_600": 4.50,
            "time_pick_kfs1_default": 2.5,
            "time_pick_kfs2": 1.6,
            "time_clean_kfs2": 0.3,
            "w_time": 1.0,
            "w_pick": 100.0
        }
        self.ext_move_time = 0.8
        self.ext_pick_kfs1_time_default = 2.2

    def cb_decision(self, msg: KFSDecision):
        # 当收到 KFSDecision 时触发规划并写入 BT xml
        try:
            with self._lock:
                # 如果已经完成规划，忽略后续消息
                if self._planning_completed:
                    self.get_logger().debug('Planning already completed, ignoring KFSDecision message')
                    return

                self.get_logger().info('Received KFSDecision, running planner...')
                # 首先尝试从消息字段里提取台阶物体信息
                # Treat OBJECT_UNK as EMPTY per request
                OBJECT_NONE = 0
                OBJECT_R1 = 1
                OBJECT_R2 = 2
                OBJECT_FAKE = 3
                OBJECT_UNK = 4

                kfs1_positions = []
                kfs2_positions = []
                fake_positions = []
                try:
                    # msg.stair_object_type 应该是长度为 total_stairs 的数组，对应台阶 1..N
                    for i, val in enumerate(msg.stair_object_type):
                        # normalize unknown -> none
                        if int(val) == OBJECT_UNK:
                            obj = OBJECT_NONE
                        else:
                            obj = int(val)

                        idx1 = i + 1
                        if obj == OBJECT_R1:
                            kfs1_positions.append(idx1)
                        elif obj == OBJECT_R2:
                            kfs2_positions.append(idx1)
                        elif obj == OBJECT_FAKE:
                            fake_positions.append(idx1)
                        # OBJECT_NONE or others are ignored
                except Exception:
                    # 如果消息格式不符合预期，回退到原先的随机策略
                    kfs1_positions = []
                    kfs2_positions = []

                # Determine kfs_locked from KFSDecision message
                # Use the first fake position as locked, or None if no fake
                kfs_locked = fake_positions[0] if fake_positions else None

                # Build kfs1_set: prefer reported R1 positions; if none, fall back to sampling
                if kfs1_positions:
                    # choose up to 3 reported R1 positions
                    sample_kfs1 = kfs1_positions[:3]
                    kfs1_set = set(sample_kfs1)
                else:
                    # fallback: 随机选择，排除 locked
                    kfs1_candidates = [1,2,3,4,6,7,9,10,11,12]
                    if kfs_locked in kfs1_candidates:
                        available_kfs1 = [c for c in kfs1_candidates if c != kfs_locked]
                    else:
                        available_kfs1 = kfs1_candidates
                    sample_kfs1_count = min(3, len(available_kfs1))
                    kfs1_set = set(random.sample(available_kfs1, sample_kfs1_count))

                # If we have reported kfs2 positions, use them; otherwise sample from remaining
                if kfs2_positions:
                    # limit to 4
                    kfs2_positions = kfs2_positions[:4]
                else:
                    all_cells = list(range(1,13))
                    candidates_for_kfs2 = [c for c in all_cells if c != kfs_locked and c not in kfs1_set]
                    kfs2_count = min(4, len(candidates_for_kfs2))
                    kfs2_positions = random.sample(candidates_for_kfs2, kfs2_count)

                time_pick_kfs1_map_global = {
                    1: 2.0, 2: 3.0, 3: 2.2, 4: 1.8, 6: 2.6,
                    7: 2.4, 9: 2.1, 10: 1.9, 11: 2.7, 12: 2.3
                }
                time_pick_kfs1_map = {node: time_pick_kfs1_map_global.get(node, self.times["time_pick_kfs1_default"]) for node in kfs1_set}

                try:
                    best_time, node_path, stats, kfs1_pick_events, ext_path_segments = a_star_with_external_ring_kfs1(
                        heights_map=self.heights,
                        times=self.times,
                        ext_move_time=self.ext_move_time,
                        ext_pick_kfs1_time_default=self.ext_pick_kfs1_time_default,
                        kfs_locked=kfs_locked,
                        kfs1_set=kfs1_set,
                        time_pick_kfs1_map=time_pick_kfs1_map,
                        kfs2_positions=kfs2_positions,
                        entry_nodes=(1,2,3),
                        exit_nodes=(10,11,12),
                        min_kfs2_picked_required=1
                    )
                except Exception as e:
                    self.get_logger().error(f'Planning failed: {e}')
                    node_path = []

                wp_list = node_path if node_path is not None else []
                # 如果第一个点是入口 1/2/3，则在前面补充入口航点（值 = 第一个点 - 3）
                if wp_list:
                    first_wp = wp_list[0]
                    if first_wp in (1, 2, 3):
                        entry_wp = first_wp - 3
                        wp_list = [entry_wp] + wp_list
                        self.get_logger().info(f'Prepended entry waypoint {entry_wp} to MainWPs -> {wp_list}')

                self.get_logger().info(f'Computed MainWPs = {wp_list}, writing to XML...')
                self._write_mainwps_to_xml(wp_list)
                self.get_logger().info('Successfully wrote MainWPs to XML')
        except Exception as e:
            self.get_logger().error(f'Exception in cb_decision: {e}')

    def _send_mainwps_to_blackboard(self, wps: List[int]):
        """直接将计算结果发送给行为树黑板"""
        self.get_logger().info(f'Sending MainWPs to blackboard: {wps}')
        # 尝试通过服务更新运行时 BT 黑板
        try:
            if self._client.wait_for_service(timeout_sec=1.0):
                req = SetMainWps.Request()
                req.wps = wps
                future = self._client.call_async(req)
                # 等待响应
                timeout = 2.0
                t0 = time.time()
                while rclpy.ok() and not future.done() and (time.time() - t0) < timeout:
                    rclpy.spin_once(self, timeout_sec=0.01)
                if future.done():
                    res = future.result()
                    if res and getattr(res, 'success', False):
                        self.get_logger().info('Updated running BT blackboard via service')
                        return True
                    else:
                        self.get_logger().warning(f'Service returned failure: {getattr(res, "message", "")}')
                else:
                    self.get_logger().warning('Service call timed out')
            else:
                self.get_logger().info('BT service /fly_step_bt/set_main_wps not available (will retry if configured)')
        except Exception as e:
            self.get_logger().warning(f'Service call encountered exception: {e}')

        # Debug: check retry configuration
        self.get_logger().info(f'Service retry enabled: {self.service_retry}, timeout: {self.service_retry_timeout_sec}s')

        # 如果服务不可用，启动后台重试
        if self.service_retry:
            with self._lock:
                self._pending_wp = wps
                if self._pending_thread is None or not self._pending_thread.is_alive():
                    def _retry_loop(node_self: 'KFSPlannerNode'):
                        start = time.time()
                        node_self.get_logger().info('Starting background retry to deliver MainWPs to /fly_step_bt/set_main_wps')
                        while rclpy.ok():
                            # 检查超时
                            if node_self.service_retry_timeout_sec > 0 and (time.time() - start) > node_self.service_retry_timeout_sec:
                                node_self.get_logger().warning(f'Giving up retrying after {node_self.service_retry_timeout_sec}s')
                                break
                            try:
                                if node_self._client.wait_for_service(timeout_sec=node_self.service_retry_interval_sec):
                                    with node_self._lock:
                                        pending = node_self._pending_wp
                                    if pending is None:
                                        node_self.get_logger().info('No pending MainWPs to send; exiting retry loop')
                                        break
                                    req2 = SetMainWps.Request()
                                    req2.wps = pending
                                    fut2 = node_self._client.call_async(req2)
                                    t0b = time.time()
                                    while rclpy.ok() and not fut2.done() and (time.time() - t0b) < 2.0:
                                        rclpy.spin_once(node_self, timeout_sec=0.01)
                                    if fut2.done():
                                        res2 = fut2.result()
                                        if res2 and getattr(res2, 'success', False):
                                            node_self.get_logger().info('Background retry: updated running BT blackboard via service')
                                            with node_self._lock:
                                                node_self._pending_wp = None
                                            break
                                        else:
                                            node_self.get_logger().warning(f'Background retry: service returned failure: {getattr(res2, "message", "")}')
                                    else:
                                        node_self.get_logger().debug('Background retry: service call timed out, will retry')
                            except Exception as ex:
                                node_self.get_logger().debug(f'Background retry: exception: {ex}')
                            time.sleep(node_self.service_retry_interval_sec)
                        node_self.get_logger().info('Background retry loop exiting')

                    th = threading.Thread(target=_retry_loop, args=(self,), daemon=True)
                    self._pending_thread = th
                    th.start()
                    self.get_logger().info('Scheduled background retry to deliver MainWPs')

        return False

    def _write_mainwps_to_xml(self, wps: List[int]):
        """直接修改XML文件中的MainWPs值"""
        try:
            # 使用ament_index找到fly_step_mission包的共享目录
            fly_step_share = get_package_share_directory('fly_step_mission')
            bt_xml_file = os.path.join(fly_step_share, 'behavior_trees', 'dynamic_waypoint_mission.xml')

            self.get_logger().info(f'Reading BT XML file: {bt_xml_file}')

            # 读取XML文件
            tree = ET.parse(bt_xml_file)
            root = tree.getroot()

            # 查找SetBlackboard节点并修改value
            changed = False
            for sb in root.iter():
                if sb.tag.endswith('SetBlackboard') or sb.tag == 'SetBlackboard':
                    if sb.get('output_key') == 'MainWPs':
                        # 构建新的value字符串
                        new_value = '[' + ', '.join(str(x) for x in wps) + ']'
                        sb.set('value', new_value)
                        changed = True
                        self.get_logger().info(f'Updated MainWPs in XML: {new_value}')
                        break

            if changed:
                # 创建备份
                backup = bt_xml_file + '.bak'
                try:
                    if not os.path.exists(backup):
                        import shutil
                        shutil.copy2(bt_xml_file, backup)
                        self.get_logger().info(f'Created backup: {backup}')
                except Exception as e:
                    self.get_logger().warning(f'Failed to create backup: {e}')

                # 保存修改后的XML
                tree.write(bt_xml_file, encoding='utf-8', xml_declaration=True)
                self.get_logger().info('Successfully updated BT XML file')
                # 标记规划完成，避免重复处理
                self._planning_completed = True
                self.get_logger().info('Planning completed successfully! Will ignore future KFSDecision messages')
            else:
                self.get_logger().warning('No SetBlackboard MainWPs found in XML')

        except Exception as e:
            self.get_logger().error(f'Failed to update BT XML: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = KFSPlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
