"""
MediaPipe face detection + Kalman filter for smooth 9:16 crop reframing.

Samples every 5th frame, applies a constant-velocity Kalman filter,
then computes a crop box centered on the face (±1.5x face size).
Falls back to center-crop when no face detected for >2 seconds.
"""

from dataclasses import dataclass

import cv2
import numpy as np

_mp_face_detection = None


def _get_face_detection():
    global _mp_face_detection
    if _mp_face_detection is None:
        try:
            import mediapipe as mp

            _mp_face_detection = mp.solutions.face_detection
        except (ImportError, AttributeError):
            _mp_face_detection = None
    return _mp_face_detection


@dataclass
class FaceBox:
    x_center: float
    y_center: float
    width: float
    height: float


@dataclass
class CropBox:
    x: int
    y: int
    width: int
    height: int


class KalmanFilter2D:
    """Simple constant-velocity Kalman filter for 2D position."""

    def __init__(self, dt: float = 1.0):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0],
                                              [0, 1, 0, 0]], dtype=np.float32)
        self.kf.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01
        self.initialized = False

    def update(self, x: float, y: float) -> tuple[float, float]:
        if not self.initialized:
            self.kf.statePre = np.array([x, y, 0, 0], dtype=np.float32)
            self.kf.statePost = np.array([x, y, 0, 0], dtype=np.float32)
            self.initialized = True
            return x, y

        self.kf.predict()
        measurement = np.array([[x], [y]], dtype=np.float32)
        corrected = self.kf.correct(measurement)
        return float(corrected[0][0]), float(corrected[1][0])


def detect_faces(frame: np.ndarray) -> list[FaceBox]:
    """Run MediaPipe face detection on a single frame."""
    fd = _get_face_detection()
    if fd is None:
        return []

    with fd.FaceDetection(model_selection=0, min_detection_confidence=0.5) as detector:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = detector.process(rgb)

    if not results.detections:
        return []

    h, w = frame.shape[:2]
    boxes = []
    for detection in results.detections:
        bbox = detection.location_data.relative_bounding_box
        boxes.append(FaceBox(
            x_center=(bbox.xmin + bbox.width / 2) * w,
            y_center=(bbox.ymin + bbox.height / 2) * h,
            width=bbox.width * w,
            height=bbox.height * h,
        ))
    return boxes


def compute_crop_box(
    face: FaceBox | None,
    frame_w: int,
    frame_h: int,
    output_w: int = 1080,
    output_h: int = 1920,
    fallback_center: bool = True,
) -> CropBox:
    """Compute a 9:16 crop box centered on the face.

    If face is None, returns center-crop as fallback.
    """
    if face is None:
        if fallback_center:
            crop_w = min(frame_w, int(frame_h * 9 / 16))
            crop_h = int(crop_w * 16 / 9)
            if crop_h > frame_h:
                crop_h = frame_h
                crop_w = int(crop_h * 9 / 16)
            return CropBox(
                x=(frame_w - crop_w) // 2,
                y=(frame_h - crop_h) // 2,
                width=crop_w,
                height=crop_h,
            )
        return CropBox(x=0, y=0, width=frame_w, height=frame_h)

    face_size = max(face.width, face.height)
    crop_size = int(face_size * 1.5)
    target_w = output_w
    target_h = output_h

    scale = max(target_w / crop_size, target_h / crop_size)
    crop_w = int(target_w / scale)
    crop_h = int(target_h / scale)

    x = int(face.x_center - crop_w / 2)
    y = int(face.y_center - crop_h / 2)

    x = max(0, min(x, frame_w - crop_w))
    y = max(0, min(y, frame_h - crop_h))

    return CropBox(x=x, y=y, width=crop_w, height=crop_h)


def smooth_crop_trajectory(
    video_path: str,
    sample_every: int = 5,
    output_w: int = 1080,
    output_h: int = 1920,
) -> list[CropBox]:
    """Process video, return list of CropBoxes (one per sampled frame).

    Applies MediaPipe detection every `sample_every` frames,
    Kalman-smooths the face center trajectory, and computes crop boxes.
    Frames without detection get a fallback center-crop.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    kf = KalmanFilter2D(dt=sample_every / fps)
    crop_boxes: list[CropBox] = []
    no_face_counter = 0
    smoothed_face: FaceBox | None = None

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every == 0:
            faces = detect_faces(frame)
            if faces:
                face = faces[0]
                sx, sy = kf.update(face.x_center, face.y_center)
                smoothed_face = FaceBox(
                    x_center=sx, y_center=sy,
                    width=face.width, height=face.height,
                )
                no_face_counter = 0
            else:
                no_face_counter += 1
                if no_face_counter * sample_every / fps > 2.0:
                    smoothed_face = None

        crop = compute_crop_box(
            smoothed_face, frame_w, frame_h, output_w, output_h
        )
        crop_boxes.append(crop)
        frame_idx += 1

    cap.release()
    return crop_boxes
