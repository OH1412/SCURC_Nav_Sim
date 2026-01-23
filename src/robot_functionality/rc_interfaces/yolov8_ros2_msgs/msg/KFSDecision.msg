# 台阶内容快照 - 描述所有12个台阶上有什么物体

# 常量定义
int32 OBJECT_NONE = 0           # 台阶为空
int32 OBJECT_R1 = 1             # 台阶上有r1
int32 OBJECT_R2 = 2             # 台阶上有r2
int32 OBJECT_FAKE = 3           # 台阶上有假KFS
int32 OBJECT_UNK = 4            # 台阶上未知物体

int32 total_stairs              # 总台阶数（固定=12）

# 每个台阶的内容（数组长度=12，索引i对应台阶i+1）
int32[] stair_object_type       # 台阶上的物体类型（使用上面的常量）
float64[] stair_confidences     # 该物体的置信度（若为OBJECT_NONE则为0.0）
string[] stair_names            # 台阶名称（方便调试）

# 统计信息
int32 total_r1_count            # 全场景r1总数
int32 total_r2_count            # 全场景r2总数  
int32 total_fake_count          # 全场景假KFS总数（0或1）
int32 total_empty_count         # 空台阶数量

builtin_interfaces/Time timestamp
string frame_id