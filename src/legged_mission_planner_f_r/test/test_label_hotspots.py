from legged_mission_planner_fr.label_hotspots import LabelHotspotConfig, NormRect, build_label_hotspots_yaml


def test_norm_rect_center_and_hit():
    rect = NormRect.from_drag(0.2, 0.3, 0.4, 0.5)
    assert abs(rect.center[0] - 0.3) < 1e-9 and rect.center[1] == 0.4
    assert rect.contains(0.3, 0.4)
    assert not rect.contains(0.1, 0.1)
    assert rect.pixel_size(267, 462) == (53, 92)
    assert rect.fit_square_sprite_size(267, 462) == max(8, int(round(53 * 0.9)))
    assert rect.pixel_center(267, 462) == (int(round(0.3 * 267)), int(round(0.4 * 462)))


def test_label_hotspot_hit_box_zone():
    config = LabelHotspotConfig(
        boxes={0: NormRect(0.1, 0.1, 0.2, 0.2)},
        zones={1: NormRect(0.5, 0.5, 0.6, 0.6)},
    )
    assert config.hit_box(0.15, 0.15) == 0
    assert config.hit_zone(0.55, 0.55) == 1
    assert config.hit_box(0.9, 0.9) is None


def test_build_label_hotspots_yaml():
    config = LabelHotspotConfig(
        boxes={0: NormRect(0.1, 0.2, 0.3, 0.4)},
        zones={0: NormRect(0.5, 0.6, 0.7, 0.8)},
    )
    data = build_label_hotspots_yaml(config)
    assert data['boxes'][0]['norm_x0'] == 0.1
    assert data['zones'][0]['norm_y1'] == 0.8
