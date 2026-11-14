from __future__ import annotations

import argparse
import math
import textwrap
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


@dataclass(frozen=True)
class Segment:
    kind: str
    title: str
    caption: str
    start: float
    end: float
    source_start: float
    source_end: float
    zoom: float = 1.0
    focus: tuple[float, float] = (0.5, 0.5)
    click: tuple[float, float] | None = None


SEGMENTS = [
    Segment(
        "title",
        "AgriShield",
        "Wildfire planning for farms: select a parcel, model risk, and turn it into action.",
        0.0,
        3.4,
        0.0,
        0.0,
    ),
    Segment(
        "chapter",
        "1. Select the Farm Parcel",
        "Start with the location and trace the protected boundary.",
        3.4,
        4.5,
        0.0,
        0.0,
    ),
    Segment(
        "scene",
        "Select Parcel",
        "Trace the parcel boundary on satellite imagery.",
        4.5,
        10.2,
        0.0,
        5.2,
        zoom=1.09,
        focus=(0.55, 0.48),
        click=(0.52, 0.48),
    ),
    Segment(
        "chapter",
        "2. Add Farm Attributes",
        "Crop, harvest timing, livestock, irrigation, and crew size drive the advisory.",
        10.2,
        11.3,
        5.2,
        5.2,
    ),
    Segment(
        "scene",
        "Set Attributes",
        "Choose crop, harvest window, livestock, irrigation, and crew size.",
        11.3,
        16.0,
        5.2,
        8.2,
        zoom=1.18,
        focus=(0.18, 0.56),
        click=(0.14, 0.62),
    ),
    Segment(
        "chapter",
        "3. Mark What Matters",
        "Assets tell the optimizer what to protect first.",
        16.0,
        17.1,
        8.2,
        8.2,
    ),
    Segment(
        "scene",
        "Add Assets",
        "Mark barns, high-value crops, livestock, access roads, and water.",
        17.1,
        24.0,
        8.2,
        13.4,
        zoom=1.13,
        focus=(0.55, 0.55),
        click=(0.55, 0.55),
    ),
    Segment(
        "chapter",
        "4. Run Risk Simulation",
        "The preview ranks incoming fire paths by local exposure.",
        24.0,
        25.1,
        13.4,
        13.4,
    ),
    Segment(
        "scene",
        "Review Risk",
        "Risk corridors are ranked by wind, fuels, weather, and asset exposure.",
        25.1,
        36.0,
        13.4,
        22.5,
        zoom=1.06,
        focus=(0.54, 0.52),
        click=(0.82, 0.38),
    ),
    Segment(
        "chapter",
        "5. Compare Protection",
        "Action lines and water points are placed on exposed parcel edges.",
        36.0,
        37.1,
        22.5,
        22.5,
    ),
    Segment(
        "scene",
        "Action Plan",
        "Protected mode shows how firebreaks slow the highest-risk corridors.",
        37.1,
        49.0,
        22.5,
        33.5,
        zoom=1.11,
        focus=(0.56, 0.58),
        click=(0.55, 0.61),
    ),
    Segment(
        "chapter",
        "6. Generate the Report",
        "Turn simulation output into a plain-English field plan.",
        49.0,
        50.1,
        33.5,
        33.5,
    ),
    Segment(
        "scene",
        "Generated Report",
        "Share the field plan with a farm manager, advisor, or crew.",
        50.1,
        60.5,
        33.5,
        44.5,
        zoom=1.06,
        focus=(0.76, 0.45),
        click=(0.85, 0.40),
    ),
    Segment(
        "chapter",
        "7. Inspect Details",
        "Keep the backend payload and ranked alternatives available.",
        60.5,
        61.6,
        44.5,
        44.5,
    ),
    Segment(
        "scene",
        "Technical Details",
        "Review ranked layouts and backend-ready payload data.",
        61.6,
        70.6,
        44.5,
        53.5,
        zoom=1.05,
        focus=(0.76, 0.58),
        click=(0.82, 0.64),
    ),
    Segment(
        "chapter",
        "8. Operational Alerts",
        "Translate the plan into timing guidance for farm operations.",
        70.6,
        71.7,
        53.5,
        53.5,
    ),
    Segment(
        "scene",
        "Alerts",
        "Summarize smoke, livestock, irrigation, and outdoor labor guidance.",
        71.7,
        80.0,
        53.5,
        61.5,
        zoom=1.05,
        focus=(0.76, 0.48),
        click=(0.83, 0.35),
    ),
    Segment(
        "outro",
        "Complete Workflow",
        "Parcel selection, attributes, simulation, action planning, reports, and alerts in one farm workflow.",
        80.0,
        84.0,
        61.5,
        66.0,
    ),
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def segment_at(time_s: float) -> Segment:
    for segment in SEGMENTS:
        if segment.start <= time_s < segment.end:
            return segment
    return SEGMENTS[-1]


def source_frame(frames: list[Path], segment: Segment, time_s: float, fps: float) -> Image.Image:
    if segment.source_end <= segment.source_start:
        source_time = segment.source_start
    else:
        local = (time_s - segment.start) / (segment.end - segment.start)
        eased = 0.5 - math.cos(local * math.pi) / 2
        source_time = segment.source_start + (segment.source_end - segment.source_start) * eased
    index = max(0, min(len(frames) - 1, round(source_time * fps)))
    return Image.open(frames[index]).convert("RGB")


def crop_zoom(image: Image.Image, zoom: float, focus: tuple[float, float]) -> Image.Image:
    if zoom <= 1.001:
        return image
    width, height = image.size
    crop_w = width / zoom
    crop_h = height / zoom
    cx = width * focus[0]
    cy = height * focus[1]
    x0 = max(0, min(width - crop_w, cx - crop_w / 2))
    y0 = max(0, min(height - crop_h, cy - crop_h / 2))
    return image.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize((width, height), Image.Resampling.LANCZOS)


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] = (5, 12, 9, 210),
    width: int = 3,
) -> None:
    x, y = xy
    for dx, dy in [(-width, 0), (width, 0), (0, -width), (0, width), (-width, -width), (width, -width), (-width, width), (width, width)]:
        draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def draw_progress(draw: ImageDraw.ImageDraw, image: Image.Image, time_s: float, segment: Segment) -> None:
    width, _ = image.size
    strip_h = 72
    draw.rectangle((0, 0, width, strip_h), fill=(255, 255, 255, 232))
    draw.rectangle((0, strip_h - 3, width, strip_h), fill=(35, 120, 86, 170))
    title_font = load_font(26, bold=True)
    small_font = load_font(18, bold=True)
    draw.text((30, 22), segment.title, font=title_font, fill=(19, 31, 24, 255))

    total = SEGMENTS[-1].end
    bar_x0 = width * 0.32
    bar_x1 = width - 42
    bar_y = 38
    draw.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 9), radius=5, fill=(210, 224, 214, 255))
    draw.rounded_rectangle(
        (bar_x0, bar_y, bar_x0 + (bar_x1 - bar_x0) * (time_s / total), bar_y + 9),
        radius=5,
        fill=(35, 120, 86, 255),
    )
    chapter_segments = [s for s in SEGMENTS if s.kind in {"scene", "outro"}]
    for idx, item in enumerate(chapter_segments, start=1):
        x = bar_x0 + (bar_x1 - bar_x0) * (item.start / total)
        active = item.start <= time_s < item.end
        radius = 14 if active else 8
        fill = (35, 120, 86, 255) if time_s >= item.start else (148, 168, 156, 255)
        draw.ellipse((x - radius, bar_y - radius + 5, x + radius, bar_y + radius + 5), fill=fill)
        if active:
            draw.text((x - 5, bar_y - 8), str(idx), font=small_font, fill=(255, 255, 255, 255))


def draw_scene_overlay(image: Image.Image, segment: Segment, time_s: float) -> Image.Image:
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    draw_progress(draw, image, time_s, segment)

    body_font = load_font(34, bold=True)
    lines = textwrap.wrap(segment.caption, width=48)
    y = height - 136
    for line in lines:
        tw = draw.textlength(line, font=body_font)
        draw_text_with_outline(draw, ((width - tw) / 2, y), line, body_font, (255, 255, 255, 255))
        y += 40

    if segment.click:
        local = (time_s - segment.start) / max(0.1, segment.end - segment.start)
        pulse = (math.sin(local * math.pi * 8) + 1) / 2
        x = width * segment.click[0]
        y = height * segment.click[1]
        r = 16 + pulse * 18
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 230, 109, 230), width=5)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 230, 109, 255))

    return Image.alpha_composite(image, overlay).convert("RGB")


def card_frame(base: Image.Image, segment: Segment, kind: str) -> Image.Image:
    width, height = base.size
    bg = base.convert("RGB").filter(ImageFilter.GaussianBlur(8))
    overlay = Image.new("RGBA", bg.size, (13, 39, 28, 168 if kind == "title" else 188))
    image = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    if kind == "title":
        title_font = load_font(78, bold=True)
        body_font = load_font(34, bold=True)
        eyebrow_font = load_font(24, bold=True)
        draw.text((96, 230), "AGRISHIELD DEMO", font=eyebrow_font, fill=(143, 255, 208, 255))
        draw.text((96, 275), segment.title, font=title_font, fill=(255, 255, 255, 255))
        wrapped = textwrap.wrap(segment.caption, width=58)
        y = 380
        for line in wrapped:
            draw.text((100, y), line, font=body_font, fill=(235, 247, 239, 255))
            y += 44
        draw.rounded_rectangle((96, 520, 430, 590), radius=14, fill=(35, 120, 86, 255))
        draw.text((126, 540), "Guided walkthrough", font=load_font(26, bold=True), fill=(255, 255, 255, 255))
    else:
        title_font = load_font(54, bold=True)
        body_font = load_font(30, bold=True)
        tw = draw.textlength(segment.title, font=title_font)
        draw.text(((width - tw) / 2, 400), segment.title, font=title_font, fill=(255, 255, 255, 255))
        lines = textwrap.wrap(segment.caption, width=62)
        y = 475
        for line in lines:
            lw = draw.textlength(line, font=body_font)
            draw.text(((width - lw) / 2, y), line, font=body_font, fill=(235, 247, 239, 255))
            y += 38
    return image.convert("RGB")


def write_srt(path: Path) -> None:
    blocks = []
    scenes = [s for s in SEGMENTS if s.kind in {"scene", "outro"}]
    for idx, segment in enumerate(scenes, start=1):
        blocks.append(f"{idx}\n{timestamp(segment.start)} --> {timestamp(segment.end)}\n{segment.caption}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


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
    total_frames = round(SEGMENTS[-1].end * args.output_fps)
    for output_idx in range(total_frames):
        time_s = output_idx / args.output_fps
        segment = segment_at(time_s)
        base = source_frame(frames, segment, time_s, args.source_fps)
        if segment.kind in {"title", "chapter", "outro"}:
            image = card_frame(base, segment, segment.kind)
            if segment.kind == "outro":
                image = draw_scene_overlay(crop_zoom(base, 1.02, (0.55, 0.54)), segment, time_s)
        else:
            image = crop_zoom(base, segment.zoom, segment.focus)
            image = draw_scene_overlay(image, segment, time_s)
        image.save(args.output_dir / f"{output_idx + 1:05}.jpg", quality=92)

    if args.srt:
        args.srt.parent.mkdir(parents=True, exist_ok=True)
        write_srt(args.srt)


if __name__ == "__main__":
    main()
