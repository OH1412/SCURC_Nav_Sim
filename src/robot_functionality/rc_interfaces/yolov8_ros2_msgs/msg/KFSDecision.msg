# 是否存在可抓取的真 KFS
bool real_kfs_available

# 【所有可抓取真 KFS 的列表】- 按距离排序
uint32 real_kfs_count
string[] real_kfs_class_names
float64[] real_kfs_distances
float64[] real_kfs_confidences
string[] real_kfs_colors
float64[] real_kfs_bbox_xmin
float64[] real_kfs_bbox_ymin
float64[] real_kfs_bbox_xmax
float64[] real_kfs_bbox_ymax
uint32 primary_target_index

# 【假 KFS 危险区】
uint32 fake_kfs_count
float64[] fake_kfs_distances
float64[] fake_kfs_confidences
string[] fake_kfs_colors
float64 closest_fake_kfs_distance

# 【安全状态】
string safety_status
string priority_level
builtin_interfaces/Time timestamp
string frame_id
float64 decision_confidence