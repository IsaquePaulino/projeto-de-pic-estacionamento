import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from parking_monitor.configuration import DetectionSettings, ParkingConfig, valid_polygon
from parking_monitor.detection import OccupancyDetector


def advance(detector, image, start, count=4):
    for index in range(count):
        detector.analyze(image, start + index * 0.4)


def test_empty_occupied_and_free_need_consecutive_confirmations(parking, empty_scene, car_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.analyze(empty_scene, 0)
    assert detector.states["V01"].state == "unknown"
    detector.set_reference(empty_scene)
    advance(detector, empty_scene, 1, 3)
    assert detector.states["V01"].state == "unknown"
    detector.analyze(empty_scene, 2.3)
    assert detector.states["V01"].state == "free"
    advance(detector, car_scene, 3, 3)
    assert detector.states["V01"].state == "free"
    detector.analyze(car_scene, 4.3)
    assert detector.states["V01"].state == "occupied"
    advance(detector, empty_scene, 5)
    assert detector.states["V01"].state == "free"
    assert all(state.state == "unknown" for key, state in detector.states.items() if key != "V01")


def test_single_change_does_not_flicker(parking, empty_scene, car_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    advance(detector, empty_scene, 0)
    detector.analyze(car_scene, 2)
    detector.analyze(empty_scene, 2.4)
    assert detector.states["V01"].state == "free"
    assert detector.states["V01"].candidate == "free"


def test_global_brightness_offset_is_compensated(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    advance(detector, np.full_like(empty_scene, 148), 0)
    assert detector.states["V01"].state == "free"
    detector.analyze(np.full_like(empty_scene, 200), 5)
    assert detector.states["V01"].state == "unknown"
    assert "iluminação" in detector.states["V01"].reason


def test_uniform_shadow_is_not_sufficient_for_occupation(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    shadow = empty_scene.copy()
    cv2.rectangle(shadow, (80, 60), (223, 179), (70, 70, 70), -1)
    advance(detector, shadow, 0, 8)
    assert detector.states["V01"].state == "unknown"
    assert detector.states["V01"].changed_ratio > 0.18


def test_small_noise_does_not_occupy_the_space(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    rng = np.random.default_rng(12)
    for index in range(6):
        image = np.clip(empty_scene.astype(float) + rng.normal(0, 3, empty_scene.shape), 0, 255).astype(np.uint8)
        detector.analyze(image, index * 0.4)
    assert detector.states["V01"].state == "free"


def test_color_change_with_similar_gray_intensity_is_detected(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    image = empty_scene.copy()
    cv2.rectangle(image, (105, 85), (195, 165), (0, 180, 96), -1)
    advance(detector, image, 0)
    assert detector.states["V01"].state == "occupied"


def test_uniform_shadow_on_colored_ground_is_not_occupation(parking, empty_scene):
    reference = np.full_like(empty_scene, (80, 160, 110))
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(reference)
    shadow = reference.copy()
    shadow[60:180, 80:224] = (40, 80, 55)
    advance(detector, shadow, 0, 8)
    assert detector.states["V01"].state == "unknown"


def test_persistent_ambiguity_expires_previous_free_state(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings(), stale_after=5)
    detector.set_reference(empty_scene)
    advance(detector, empty_scene, 0)
    shadow = empty_scene.copy()
    cv2.rectangle(shadow, (80, 60), (223, 179), (70, 70, 70), -1)
    detector.analyze(shadow, 2)
    assert detector.states["V01"].state == "free"
    detector.analyze(shadow, 7)
    assert detector.states["V01"].state == "unknown"


@pytest.mark.parametrize("level", [0, 255])
def test_black_or_saturated_frame_is_unknown(parking, empty_scene, level):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    advance(detector, empty_scene, 0)
    detector.analyze(np.full_like(empty_scene, level), 5)
    assert detector.states["V01"].state == "unknown"


def test_resolution_change_invalidates_state(parking, empty_scene):
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(empty_scene)
    advance(detector, empty_scene, 0)
    detector.analyze(np.full((120, 160, 3), 128, np.uint8), 3)
    assert detector.states["V01"].state == "unknown"
    assert "resolução" in detector.states["V01"].reason


def test_camera_translation_is_rejected(parking, empty_scene):
    reference = empty_scene.copy()
    for x in range(15, 320, 35):
        for y in range(15, 240, 35):
            cv2.circle(reference, (x, y), 4, (35, 35, 35), -1)
    detector = OccupancyDetector(parking, DetectionSettings())
    detector.set_reference(reference)
    moved = cv2.warpAffine(reference, np.float32([[1, 0, 8], [0, 1, 5]]), (320, 240), borderValue=(128, 128, 128))
    detector.analyze(moved, 1)
    assert detector.states["V01"].state == "unknown"
    assert "câmera" in detector.states["V01"].reason


@pytest.mark.parametrize("points", [
    [(0, 0), (1, 1), (1, 0), (0, 1)],
    [(0, 0), (0, 0), (0, 0)],
    [(-0.1, 0), (1, 0), (1, 1)],
    [(0, 0), (float("nan"), 0), (1, 1)],
])
def test_bad_regions_are_rejected(points):
    with pytest.raises(ValueError):
        valid_polygon(points)


def test_duplicate_identifiers_and_bad_thresholds_are_rejected(parking):
    data = parking.model_dump()
    data["spots"][1]["id"] = data["spots"][0]["id"]
    with pytest.raises(ValidationError):
        ParkingConfig.model_validate(data)
    with pytest.raises(ValidationError):
        DetectionSettings(free_max_changed_ratio=0.4, occupied_min_changed_ratio=0.2)
    with pytest.raises(ValidationError):
        DetectionSettings(gaussian_blur_kernel=4)
