from app.reframe.face_tracker import (
    FaceBox,
    KalmanFilter2D,
    compute_crop_box,
)


def test_kalman_smooth():
    kf = KalmanFilter2D(dt=1.0)
    noisy = [(100 + i * 10, 200 + i * 5) for i in range(10)]
    smoothed = [kf.update(x, y) for x, y in noisy]

    for i in range(1, len(smoothed)):
        dx = abs(smoothed[i][0] - smoothed[i - 1][0])
        dy = abs(smoothed[i][1] - smoothed[i - 1][1])
        assert dx < 20
        assert dy < 20


def test_crop_box_within_bounds():
    face = FaceBox(x_center=50, y_center=50, width=100, height=100)
    crop = compute_crop_box(face, frame_w=1920, frame_h=1080)
    assert crop.x >= 0
    assert crop.y >= 0
    assert crop.x + crop.width <= 1920
    assert crop.y + crop.height <= 1080


def test_crop_box_at_edge():
    face = FaceBox(x_center=10, y_center=10, width=50, height=50)
    crop = compute_crop_box(face, frame_w=1920, frame_h=1080)
    assert crop.x >= 0
    assert crop.y >= 0


def test_no_face_fallback():
    crop = compute_crop_box(None, frame_w=1920, frame_h=1080)
    assert crop.x >= 0
    assert crop.y >= 0
    assert crop.width > 0
    assert crop.height > 0


def test_kalman_initialization():
    kf = KalmanFilter2D(dt=0.5)
    x, y = kf.update(500.0, 300.0)
    assert x == 500.0
    assert y == 300.0
