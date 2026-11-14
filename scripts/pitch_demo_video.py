from __future__ import annotations

import argparse
import math
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


@dataclass(frozen=True)
class Segment:
    title: str
    caption: str
    start: float
    end: float
    source_start: float
    source_end: float
    zoom: float = 1.0
    focus: tuple[float, float] = (0.5, 0.5)
    click: tuple[float, float] | None = None
    card: bool = False


SEGMENTS = [
    Segment(
        "What It Is",
        "AgriShield helps farmers plan fire-safe farms before wildfire season.",
        0.0,
        5.0,
        0.0,
        0.0,
        card=True,
    ),
    Segment(
        "Draw Farm Boundary",
        "Select the parcel area that needs protection.",
        5.0,
        10.0,
        5.0,
        10.0,
        zoom=1.09,
        focus=(0.55, 0.50),
        click=(0.55, 0.50),
    ),
    Segment(
        "Add Assets",
        "Mark crops, barns, livestock, roads, and water points.",
        10.0,
        15.0,
        10.0,
        15.0,
        zoom=1.13,
        focus=(0.55, 0.56),
        click=(0.55, 0.56),
    ),
    Segment(
        "Show Risk Overlay",
        "Rank fire paths using fuels, weather, terrain, and asset exposure.",
        15.0,
        22.0,
        15.0,
        22.0,
        zoom=1.05,
        focus=(0.57, 0.53),
        click=(0.82, 0.38),
    ),
    Segment(
        "Generate Buffers",
        "Recommend firebreaks, water points, and low-fuel buffers.",
        22.0,
        27.0,
        22.0,
        27.0,
        zoom=1.11,
        focus=(0.57, 0.58),
        click=(0.55, 0.61),
    ),
    Segment(
        "Low Disruption",
        "Keep farm operations moving with the smallest useful intervention.",
        27.0,
        31.0,
        27.0,
        31.0,
        zoom=1.12,
        focus=(0.68, 0.58),
        click=(0.83, 0.45),
    ),
    Segment(
        "Max Protection",
        "Increase buffers when risk reduction matters more than disruption.",
        31.0,
        35.0,
        31.0,
        35.0,
        zoom=1.12,
        focus=(0.68, 0.58),
        click=(0.83, 0.45),
    ),
    Segment(
        "Before / After Payoff",
        "Compare current risk, risk after actions, reduction, and land at risk.",
        35.0,
        41.0,
        35.0,
        41.0,
        zoom=1.14,
        focus=(0.78, 0.18),
        click=(0.78, 0.18),
    ),
    Segment(
        "Plain-Language Plan",
        "Turn simulation output into field-ready recommendations.",
        41.0,
        46.0,
        41.0,
        46.0,
        zoom=1.07,
        focus=(0.76, 0.46),
        click=(0.82, 0.40),
    ),
    Segment(
        "City Planning Use Case",
        "The same workflow can prioritize WUI buffers, access, and water planning.",
        46.0,
        50.0,
        46.0,
        50.0,
        zoom=1.05,
        focus=(0.76, 0.48),
        click=(0.82, 0.36),
    ),
]


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def active_segment(t: float) -> Segment:
    for segment in SEGMENTS:
        if segment.start <= t < segment.end:
            return segment
    return SEGMENTS[-1]


def timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def source_image(frames: list[Path], segment: Segment, t: float, fps: float) -> Image.Image:
    if segment.source_start == segment.source_end:
        source_t = segment.source_start
    else:
        local = (t - segment.start) / (segment.end - segment.start)
        eased = 0.5 - math.cos(local * math.pi) / 2
        source_t = segment.source_start + (segment.source_end - segment.source_start) * eased
    idx = max(0, min(len(frames) - 1, round(source_t * fps)))
    return Image.open(frames[idx]).convert("RGB")


def zoom(image: Image.Image, amount: float, focus: tuple[float, float]) -> Image.Image:
    if amount <= 1:
        return image
    w, h = image.size
    cw = w / amount
    ch = h / amount
    cx = w * focus[0]
    cy = h * focus[1]
    x0 = max(0, min(w - cw, cx - cw / 2))
    y0 = max(0, min(h - ch, cy - ch / 2))
    return image.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.Resampling.LANCZOS)


def outlined(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt: ImageFont.ImageFont) -> None:
    x, y = xy
    for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((x + dx, y + dy), text, font=fnt, fill=(4, 12, 8, 225))
    draw.text((x, y), text, font=fnt, fill=(255, 255, 255, 255))


def section_name(t: float) -> str:
    if t < 5:
        return "0-5 sec: What it is"
    if t < 35:
        return "5-35 sec: Product demo"
    return "35-50 sec: The payoff"


def render_card(base: Image.Image, segment: Segment) -> Image.Image:
    w, h = base.size
    img = base.filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (12, 39, 28, 190))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    draw.text((96, 250), "AGRISHIELD", font=font(26, True), fill=(143, 255, 208, 255))
    draw.text((96, 306), segment.title, font=font(72, True), fill=(255, 255, 255, 255))
    y = 410
    for line in textwrap.wrap(segment.caption, width=58):
        draw.text((100, y), line, font=font(34, True), fill=(235, 247, 239, 255))
        y += 46
    return img.convert("RGB")


def render_overlay(image: Image.Image, segment: Segment, t: float) -> Image.Image:
    img = image.convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    strip_h = 76
    draw.rectangle((0, 0, w, strip_h), fill=(255, 255, 255, 235))
    draw.rectangle((0, strip_h - 3, w, strip_h), fill=(35, 120, 86, 180))
    draw.text((30, 18), section_name(t), font=font(24, True), fill=(19, 31, 24, 255))
    draw.text((390, 18), segment.title, font=font(26, True), fill=(35, 120, 86, 255))
    bar_x0, bar_x1 = 980, w - 42
    bar_y = 38
    draw.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 9), radius=5, fill=(210, 224, 214, 255))
    draw.rounded_rectangle((bar_x0, bar_y, bar_x0 + (bar_x1 - bar_x0) * (t / 50), bar_y + 9), radius=5, fill=(35, 120, 86, 255))
    for mark, label in [(5, "Demo"), (35, "Payoff")]:
        x = bar_x0 + (bar_x1 - bar_x0) * (mark / 50)
        draw.ellipse((x - 8, bar_y - 4, x + 8, bar_y + 12), fill=(35, 120, 86, 255))

    cap_font = font(34, True)
    y = h - 128
    for line in textwrap.wrap(segment.caption, width=54):
        tw = draw.textlength(line, font=cap_font)
        outlined(draw, ((w - tw) / 2, y), line, cap_font)
        y += 40

    if segment.click:
        local = (t - segment.start) / max(0.1, segment.end - segment.start)
        pulse = (math.sin(local * math.pi * 8) + 1) / 2
        x = w * segment.click[0]
        y = h * segment.click[1]
        r = 16 + pulse * 18
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 230, 109, 235), width=5)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 230, 109, 255))

    return img.convert("RGB")


def write_srt(path: Path) -> None:
    blocks = []
    for idx, segment in enumerate(SEGMENTS, start=1):
        blocks.append(f"{idx}\n{timestamp(segment.start)} --> {timestamp(segment.end)}\n{segment.caption}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-fps", type=float, default=12)
    parser.add_argument("--output-fps", type=float, default=12)
    parser.add_argument("--srt", type=Path)
    args = parser.parse_args()
    frames = sorted(args.frames_dir.glob("*.jpg"))
    if not frames:
        raise SystemExit("No frames found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    total_frames = round(50 * args.output_fps)
    for out_idx in range(total_frames):
        t = out_idx / args.output_fps
        segment = active_segment(t)
        base = source_image(frames, segment, t, args.source_fps)
        if segment.card:
            image = render_card(base, segment)
        else:
            image = render_overlay(zoom(base, segment.zoom, segment.focus), segment, t)
        image.save(args.output_dir / f"{out_idx + 1:05}.jpg", quality=92)
    if args.srt:
        args.srt.parent.mkdir(parents=True, exist_ok=True)
        write_srt(args.srt)


if __name__ == "__main__":
    main()
