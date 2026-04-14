from __future__ import annotations

import math
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOUNDS_DIR = ROOT / "sounds"
ASSETS_DIR = ROOT / "assets"
SAMPLE_RATE = 22050


def main() -> None:
    SOUNDS_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)

    create_tone_file(SOUNDS_DIR / "connect.wav", [(880, 0.12), (1175, 0.14)])
    create_tone_file(SOUNDS_DIR / "takeoff.wav", [(660, 0.12), (880, 0.12), (1047, 0.14)])
    create_tone_file(SOUNDS_DIR / "land.wav", [(1047, 0.12), (880, 0.12), (660, 0.14)])
    create_tone_file(SOUNDS_DIR / "low_battery.wav", [(440, 0.10), (0, 0.05), (440, 0.10)])
    create_tone_file(SOUNDS_DIR / "error.wav", [(220, 0.28)])

    logo = create_logo(1024, 1024)
    logo.save(ASSETS_DIR / "logo.png")
    icon = create_icon(256)
    icon.save(ASSETS_DIR / "icon.png")
    icon.save(ASSETS_DIR / "icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])


def create_tone_file(path: Path, pattern: list[tuple[int, float]]) -> None:
    samples = []
    for frequency, duration in pattern:
        frames = int(SAMPLE_RATE * duration)
        for index in range(frames):
            if frequency == 0:
                sample = 0
            else:
                t = index / SAMPLE_RATE
                envelope = min(1.0, index / 200.0, (frames - index) / 200.0)
                sample = int(math.sin(2 * math.pi * frequency * t) * 24000 * max(0.0, envelope))
            samples.append(sample)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in samples))


def create_icon(size: int) -> Image.Image:
    image = create_logo(size, size)
    if size <= 256:
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


def create_logo(width: int, height: int) -> Image.Image:
    image = Image.new("RGBA", (width, height), (133, 196, 233, 255))
    draw = ImageDraw.Draw(image)
    center_x = width // 2
    center_y = height // 2

    line_color = (228, 228, 228, 190)
    draw.rectangle((center_x - width * 0.035, 0, center_x + width * 0.035, height), fill=line_color)
    draw.rectangle((0, center_y - height * 0.035, width, center_y + height * 0.035), fill=line_color)

    wordmark_font = load_font(int(height * 0.16), bold=True)
    wordmark = "WINTELLO"
    text_bbox = draw.textbbox((0, 0), wordmark, font=wordmark_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (width - text_width) // 2
    text_y = int(height * 0.06)
    draw.text((text_x, text_y), wordmark, fill=(17, 123, 217, 255), font=wordmark_font)

    drone_scale = min(width, height) * 0.42
    body_w = drone_scale * 0.44
    body_h = drone_scale * 0.20
    body_rect = (
        center_x - body_w / 2,
        center_y - body_h / 2 + height * 0.10,
        center_x + body_w / 2,
        center_y + body_h / 2 + height * 0.10,
    )
    draw.rounded_rectangle(body_rect, radius=body_h * 0.35, fill=(242, 242, 242, 255), outline=(205, 205, 205, 255), width=max(1, int(height * 0.008)))

    arm_color = (55, 55, 60, 255)
    prop_color = (33, 33, 36, 255)
    arm_width = max(2, int(height * 0.012))
    cx = center_x
    cy = center_y + height * 0.10
    arm_reach = drone_scale * 0.55
    motor_offsets = [
        (-arm_reach, -arm_reach * 0.55),
        (arm_reach, -arm_reach * 0.40),
        (-arm_reach * 0.82, arm_reach * 0.42),
        (arm_reach * 0.92, arm_reach * 0.58),
    ]
    for dx, dy in motor_offsets:
        mx = cx + dx
        my = cy + dy
        draw.line((cx, cy, mx, my), fill=arm_color, width=arm_width)
        draw.ellipse((mx - arm_width * 1.6, my - arm_width * 1.6, mx + arm_width * 1.6, my + arm_width * 1.6), fill=arm_color)
        ring_r = drone_scale * 0.18
        draw.arc((mx - ring_r, my - ring_r, mx + ring_r, my + ring_r), start=205, end=340, fill=prop_color, width=arm_width)
        draw.arc((mx - ring_r, my - ring_r, mx + ring_r, my + ring_r), start=25, end=160, fill=prop_color, width=arm_width)
        blade_len = ring_r * 1.1
        draw.line((mx - blade_len * 0.9, my, mx + blade_len * 0.9, my - blade_len * 0.05), fill=prop_color, width=max(1, arm_width - 1))

    camera_r = max(3, int(height * 0.012))
    draw.ellipse((body_rect[0] + body_w * 0.06, cy - camera_r, body_rect[0] + body_w * 0.06 + camera_r * 2, cy + camera_r), fill=(60, 60, 60, 255))
    draw.ellipse((body_rect[0] + body_w * 0.06 + camera_r * 0.6, cy - camera_r * 0.35, body_rect[0] + body_w * 0.06 + camera_r * 1.4, cy + camera_r * 0.35), fill=(30, 220, 80, 255))
    return image


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "arialbd.ttf",
                "bahnschrift.ttf",
                "segoeuib.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "arial.ttf",
                "bahnschrift.ttf",
                "segoeui.ttf",
            ]
        )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


if __name__ == "__main__":
    main()
