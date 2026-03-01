import logging
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import timm
import torch
from PIL import Image
from torchvision import transforms

logger = logging.getLogger(__name__)

SHOT_SCALES = ["ECS", "CS", "MS", "FS", "LS"]
CHECKPOINT_PATH = os.getenv("SHOT_SCALE_CHECKPOINT", "")


def _get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class ShotScaleClassifier:
    """
    Shot scale classifier — ECS / CS / MS / FS / LS.

    Primary path:  EfficientNet-B3 fine-tuned checkpoint (set SHOT_SCALE_CHECKPOINT env).
    Fallback path: heuristic using face detection + Canny edge density.
    """

    def __init__(self, checkpoint_path: str = ""):
        self.device = _get_device()
        self.model = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        if checkpoint_path and Path(checkpoint_path).exists():
            self._load_model(checkpoint_path)
        else:
            logger.info("No shot scale checkpoint found — using heuristic classifier.")

    def _load_model(self, checkpoint_path: str):
        logger.info(f"Loading shot scale model from {checkpoint_path}")
        self.model = timm.create_model("efficientnet_b3", pretrained=False, num_classes=5)
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        self.model.to(self.device)

    def classify_frame(self, frame: np.ndarray) -> tuple[str, float]:
        """Classify shot scale from a BGR OpenCV frame. Returns (label, confidence)."""
        if self.model is not None:
            return self._classify_with_model(frame)
        return self._classify_heuristic(frame)

    def _classify_with_model(self, frame: np.ndarray) -> tuple[str, float]:
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        tensor = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=-1)
            conf, idx = probs.max(dim=-1)
        return SHOT_SCALES[idx.item()], round(conf.item(), 3)

    def _classify_heuristic(self, frame: np.ndarray) -> tuple[str, float]:
        """
        Face detected → scale by face-to-frame area ratio.
        No face       → scale by Canny edge density.
        """
        h, w = frame.shape[:2]
        frame_area = h * w
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))

        if len(faces) > 0:
            max_face_area = max(fw * fh for (_, _, fw, fh) in faces)
            ratio = max_face_area / frame_area
            if ratio > 0.25:   return "ECS", 0.70
            elif ratio > 0.10: return "CS",  0.70
            elif ratio > 0.04: return "MS",  0.70
            elif ratio > 0.01: return "FS",  0.65
            else:              return "LS",  0.65
        else:
            edges = cv2.Canny(gray, 50, 150)
            edge_density = edges.sum() / (frame_area * 255)
            if edge_density > 0.15:   return "ECS", 0.50
            elif edge_density > 0.08: return "CS",  0.50
            elif edge_density > 0.04: return "MS",  0.50
            elif edge_density > 0.02: return "FS",  0.50
            else:                     return "LS",  0.50


class ShotAnalyzer:
    """
    Full video shot analysis pipeline:
    1. PySceneDetect — shot boundary detection (ContentDetector)
    2. OpenCV        — brightness, saturation, camera movement (Farneback optical flow)
    3. ShotScaleClassifier — ECS / CS / MS / FS / LS per shot
    """

    def __init__(self):
        self.classifier = ShotScaleClassifier(CHECKPOINT_PATH)
        logger.info("ShotAnalyzer ready.")

    def analyze_video(
        self, video_path: str, thumbnail_dir: Optional[str] = None
    ) -> list[dict]:
        """
        Detect and analyze all shots in a video file.
        Returns list of shot dicts matching the shots DB schema.
        """
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector

        logger.info(f"Analyzing video: {video_path}")
        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=27.0))
        scene_manager.detect_scenes(video, show_progress=False)
        scenes = scene_manager.get_scene_list()

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

        if not scenes:
            logger.warning("No scene cuts detected — treating entire video as one shot.")
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps

            class _TC:
                def __init__(self, s): self._s = s
                def get_seconds(self): return self._s

            scenes = [(_TC(0.0), _TC(duration))]

        shots = []
        for i, (start_tc, end_tc) in enumerate(scenes):
            start_sec = start_tc.get_seconds()
            end_sec   = end_tc.get_seconds()
            duration  = end_sec - start_sec

            mid_sec = start_sec + duration / 2
            cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000)
            ret, frame = cap.read()
            if not ret:
                continue

            scale, confidence              = self.classifier.classify_frame(frame)
            brightness, saturation         = self._measure_brightness_saturation(frame)
            movement                       = self._detect_camera_movement(cap, start_sec, end_sec)

            thumbnail_url = None
            if thumbnail_dir:
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumb_path = os.path.join(thumbnail_dir, f"shot_{i + 1:04d}.jpg")
                cv2.imwrite(thumb_path, frame)
                thumbnail_url = thumb_path

            shots.append({
                "shot_number":      i + 1,
                "start_time":       round(start_sec, 3),
                "end_time":         round(end_sec, 3),
                "duration":         round(duration, 3),
                "shot_scale":       scale,
                "scale_confidence": confidence,
                "camera_movement":  movement,
                "brightness":       brightness,
                "saturation":       saturation,
                "thumbnail_url":    thumbnail_url,
            })

        cap.release()
        logger.info(f"Detected {len(shots)} shots.")
        return shots

    def _measure_brightness_saturation(self, frame: np.ndarray) -> tuple[float, float]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
        brightness = round(float(hsv[:, :, 2].mean()) / 255.0, 4)
        saturation = round(float(hsv[:, :, 1].mean()) / 255.0, 4)
        return brightness, saturation

    def _detect_camera_movement(
        self, cap: cv2.VideoCapture, start_sec: float, end_sec: float
    ) -> str:
        """
        Estimate movement type from Farneback optical flow between first and
        a frame 0.5 s before shot end.
        Returns: static | pan | tilt | zoom | handheld
        """
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        ret1, frame1 = cap.read()

        sample_end = max(start_sec + 0.1, end_sec - 0.5)
        cap.set(cv2.CAP_PROP_POS_MSEC, sample_end * 1000)
        ret2, frame2 = cap.read()

        if not ret1 or not ret2:
            return "static"

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        flow  = cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        mean_mag = float(mag.mean())

        if mean_mag < 0.5:  return "static"
        if mean_mag > 3.0:  return "handheld"

        mean_dx = abs(float(flow[..., 0].mean()))
        mean_dy = abs(float(flow[..., 1].mean()))

        if mean_dx > mean_dy * 1.5:  return "pan"
        if mean_dy > mean_dx * 1.5:  return "tilt"
        return "zoom"


# Singleton
_shot_analyzer: Optional[ShotAnalyzer] = None


def get_shot_analyzer() -> ShotAnalyzer:
    global _shot_analyzer
    if _shot_analyzer is None:
        _shot_analyzer = ShotAnalyzer()
    return _shot_analyzer
