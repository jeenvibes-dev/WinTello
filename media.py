from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import config


class MediaManager:
    """Saves photos and videos from the latest RGB camera frame."""

    def __init__(self, media_dir: str = config.MEDIA_DIR, fps: int = config.MEDIA_VIDEO_FPS) -> None:
        self.media_dir = Path(media_dir)
        self.photos_dir = self.media_dir / "photos"
        self.videos_dir = self.media_dir / "videos"
        self.fps = fps
        self._writer = None
        self._recording_path: Optional[Path] = None

    @property
    def is_recording(self) -> bool:
        return self._writer is not None

    @property
    def recording_path(self) -> Optional[Path]:
        return self._recording_path

    def capture_photo(self, frame) -> Optional[Path]:
        if frame is None:
            return None
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        path = self.photos_dir / f"tello_photo_{self._timestamp()}.jpg"
        self._write_image(path, frame)
        return path

    def start_recording(self, frame) -> Optional[Path]:
        if frame is None:
            return None
        if self.is_recording:
            return self._recording_path
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        path = self.videos_dir / f"tello_video_{self._timestamp()}.avi"
        self._writer = self._create_writer(path, frame)
        self._recording_path = path
        self.write_video_frame(frame)
        return path

    def write_video_frame(self, frame) -> None:
        if frame is None or self._writer is None:
            return
        self._writer.write(self._rgb_to_bgr(frame))

    def stop_recording(self) -> Optional[Path]:
        path = self._recording_path
        if self._writer is not None:
            self._writer.release()
        self._writer = None
        self._recording_path = None
        return path

    def open_playback(self) -> None:
        self.media_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self.media_dir)

    def _create_writer(self, path: Path, frame):
        import cv2

        height, width = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(path), fourcc, self.fps, (width, height))
        if not writer.isOpened():
            writer.release()
            raise RuntimeError(f"Unable to create video file: {path}")
        return writer

    def _write_image(self, path: Path, frame) -> None:
        import cv2

        if not cv2.imwrite(str(path), self._rgb_to_bgr(frame)):
            raise RuntimeError(f"Unable to save photo: {path}")

    @staticmethod
    def _rgb_to_bgr(frame):
        return frame[:, :, [2, 1, 0]]

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
