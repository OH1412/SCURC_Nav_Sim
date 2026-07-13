from __future__ import annotations

import unittest

from legged_mission_planner_fr.field_model import COLUMN_BOX_IDS, sync_boxes_to_zones


class TestColumnSync(unittest.TestCase):
    def test_default_zone_order(self) -> None:
        box_types = [0] * 8
        zone_types = [0, 1, 2, 3]
        sync_boxes_to_zones(box_types, zone_types)
        self.assertEqual(box_types, [0, 1, 2, 3, 0, 1, 2, 3])

    def test_reversed_zone_order(self) -> None:
        box_types = [0] * 8
        zone_types = [3, 2, 1, 0]
        sync_boxes_to_zones(box_types, zone_types)
        self.assertEqual(box_types, [3, 2, 1, 0, 3, 2, 1, 0])

    def test_column_mapping_covers_all_boxes(self) -> None:
        covered = sorted(box_id for ids in COLUMN_BOX_IDS.values() for box_id in ids)
        self.assertEqual(covered, list(range(8)))

    def test_invalid_lengths(self) -> None:
        with self.assertRaises(ValueError):
            sync_boxes_to_zones([0, 1], [0, 1, 2, 3])
        with self.assertRaises(ValueError):
            sync_boxes_to_zones([0] * 8, [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
