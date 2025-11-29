
bool[] is_safe

# Estimate of the traversability of the path.
# Ranges from 0 to 1 where 0 means not traversable and 1 highly traversable.
float64[] traversability

# Polygons that are untraversable.
geometry_msgs/PolygonStamped[] untraversable_polygons
