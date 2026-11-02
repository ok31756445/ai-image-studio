"""MediaPipe face detection backed by the repository-local BlazeFace model."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .core import ensure_rgb


@lru_cache(maxsize=1)
def _create_detector(model_asset: bytes):
    # MediaPipe imports matplotlib on Windows.  Keep its cache in a writable
    # temporary directory instead of assuming the user's home is writable.
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-image-studio-matplotlib")
    )
    import mediapipe as mp

    options = mp.tasks.vision.FaceDetectorOptions(
        # Supplying the bytes also avoids MediaPipe's native Windows path
        # decoder, which cannot reliably open models below non-ASCII folders.
        base_options=mp.tasks.BaseOptions(model_asset_buffer=model_asset),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        min_detection_confidence=0.5,
        min_suppression_threshold=0.3,
    )
    return mp.tasks.vision.FaceDetector.create_from_options(options)


def detect_faces(image: Image.Image | np.ndarray, model_path: str | Path) -> list[dict]:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-image-studio-matplotlib")
    )
    import mediapipe as mp

    rgb = ensure_rgb(image)
    detector = _create_detector(Path(model_path).read_bytes())
    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    detections: list[dict] = []
    for detection in result.detections:
        box = detection.bounding_box
        score = float(detection.categories[0].score) if detection.categories else 0.0
        detections.append(
            {
                "x": int(box.origin_x),
                "y": int(box.origin_y),
                "width": int(box.width),
                "height": int(box.height),
                "confidence": score,
                "keypoints": [(float(point.x), float(point.y)) for point in detection.keypoints],
            }
        )
    return detections


def annotate_faces(image: Image.Image | np.ndarray, detections: list[dict]) -> Image.Image:
    rgb = ensure_rgb(image)
    output = Image.fromarray(rgb.copy())
    draw = ImageDraw.Draw(output)
    font = ImageFont.load_default()
    line_width = max(2, round(max(output.size) / 500))
    for index, detection in enumerate(detections, 1):
        x = detection["x"]
        y = detection["y"]
        width = detection["width"]
        height = detection["height"]
        confidence = detection["confidence"]
        draw.rectangle((x, y, x + width, y + height), outline="#52c7d9", width=line_width)
        label = f"FACE {index} · {confidence:.1%}"
        label_box = draw.textbbox((x, y), label, font=font)
        label_width = label_box[2] - label_box[0] + 12
        label_height = label_box[3] - label_box[1] + 10
        label_y = max(0, y - label_height)
        draw.rectangle((x, label_y, x + label_width, label_y + label_height), fill="#101820")
        draw.text((x + 6, label_y + 4), label, fill="#dff9fc", font=font)
        for point_x, point_y in detection["keypoints"]:
            px = round(point_x * output.width)
            py = round(point_y * output.height)
            radius = max(2, line_width)
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill="#e8a84a")
    return output
