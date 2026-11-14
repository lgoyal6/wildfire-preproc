from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CAPTIONS = [
    (0.0, 3.8, "AgriShield starts with a farm boundary, current conditions, and key assets."),
    (3.8, 8.0, "The risk view ranks incoming fire paths instead of treating every direction equally."),
    (8.0, 13.8, "The action plan places low-disruption firebreaks and water points on exposed edges."),
    (13.8, 19.4, "A plain-English report summarizes weather, risk, farm assets, and recommended actions."),
    (19.4, 25.6, "Technical details expose the backend-ready payload and ranked layout alternatives."),
    (25.6, 31.4, "Alert mode turns the same data into practical timing for crews, livestock, and irrigation."),
    (31.4, 36.0, "The final advisory connects simulation, action planning, reporting, and farm operations."),
]

GUIDED_CAPTIONS = [
    (0.0, 5.2, "Start by selecting the farm location and tracing the parcel boundary."),
    (5.2, 8.2, "Farm attributes update the advisory: crop, harvest window, livestock, irrigation, and crew."),
    (8.2, 13.4, "Key assets are added inside the parcel so the plan protects what matters most."),
    (13.4, 22.5, "The risk simulation ranks incoming fire paths by wind, fuels, weather, and asset exposure."),
    (22.5, 33.5, "Protected mode shows how action lines slow the highest-risk corridors before they hit the parcel."),
    (33.5, 44.5, "The report turns the simulation into a plain-English field plan for a manager or crew."),
    (44.5, 53.5, "Technical details keep the backend-ready payload and ranked alternatives available for review."),
    (53.5, 61.5, "Alerts convert the same farm data into practical timing for crews, livestock, and irrigation."),
    (61.5, 66.0, "AgriShield connects parcel selection, farm attributes, simulation, action planning, and reporting."),
]

INTERACTIVE_STEPS = [
    {
        "start": 0.0,
        "end": 5.2,
        "title": "1. Select Parcel",
        "caption": "Trace the protected farm boundary on the satellite map.",
        "hint": "Boundary points define the parcel area and simulation target.",
    },
    {
        "start": 5.2,
        "end": 8.2,
        "title": "2. Set Attributes",
        "caption": "Choose crop type, harvest timing, livestock, irrigation, and crew size.",
        "hint": "These values change risk scores and recommended actions.",
    },
    {
        "start": 8.2,
        "end": 13.4,
        "title": "3. Add Assets",
        "caption": "Mark barns, high-value crops, livestock, roads, and water points.",
        "hint": "Assets help the optimizer protect the most important areas.",
    },
    {
        "start": 13.4,
        "end": 22.5,
        "title": "4. Review Risk",
        "caption": "Risk paths are ranked by wind, fuels, weather, and asset exposure.",
        "hint": "The right panel shows the 7-day operational risk forecast.",
    },
    {
        "start": 22.5,
        "end": 33.5,
        "title": "5. Compare Protection",
        "caption": "Protected mode shows action lines slowing the highest-risk corridors.",
        "hint": "Water points and firebreaks are placed near exposed parcel edges.",
    },
    {
        "start": 33.5,
        "end": 44.5,
        "title": "6. Generate Report",
        "caption": "The report converts simulation output into a plain-English field plan.",
        "hint": "Share this with a farm manager, advisor, or crew lead.",
    },
    {
        "start": 44.5,
        "end": 53.5,
        "title": "7. Inspect Details",
        "caption": "Technical details expose ranked layouts and backend-ready payload data.",
        "hint": "Use this view for validation, export, or ELMFIRE handoff.",
    },
    {
        "start": 53.5,
        "end": 61.5,
        "title": "8. Use Alerts",
        "caption": "Alerts turn the advisory into timing guidance for crews and operations.",
        "hint": "Livestock, irrigation, smoke, and outdoor labor are summarized here.",
    },
    {
        "start": 61.5,
        "end": 66.0,
        "title": "9. Full Workflow",
        "caption": "Parcel selection, attributes, simulation, planning, reports, and alerts connect in one workflow.",
        "hint": "The result is an actionable wildfire plan for farm operations.",
    },
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def caption_for_time(seconds: float, captions: list[tuple[float, float, str]]) -> str | None:
    for start, end, text in captions:
        if start <= seconds < end:
            return text
    return None


def render_caption(image: Image.Image, text: str, clear_style: bool) -> Image.Image:
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    font = load_font(max(28, width // 44))
    margin = max(34, width // 36)
    max_text_width = width - margin * 2 - 44
    words_per_line = max(26, width // 52)
    lines = textwrap.wrap(text, width=words_per_line)

    line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_height = max(box[3] - box[1] for box in line_boxes) + 10
    text_height = line_height * len(lines)
    box_height = text_height + 34
    box_width = min(max_text_width + 44, max(draw.textlength(line, font=font) for line in lines) + 52)
    x0 = (width - box_width) / 2
    y0 = height - box_height - max(28, height // 32)
    x1 = x0 + box_width
    y1 = y0 + box_height

    if not clear_style:
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=18,
            fill=(8, 14, 11, 218),
            outline=(255, 255, 255, 82),
            width=2,
        )

    y = y0 + 18
    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = (width - text_width) / 2
        if clear_style:
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw.text((x + dx, y + dy), line, font=font, fill=(5, 12, 9, 220))
        else:
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 150))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    return Image.alpha_composite(image, overlay).convert("RGB")


def active_step(seconds: float) -> dict[str, object]:
    for step in INTERACTIVE_STEPS:
        if float(step["start"]) <= seconds < float(step["end"]):
            return step
    return INTERACTIVE_STEPS[-1]


def render_interactive_overlay(image: Image.Image, seconds: float) -> Image.Image:
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    step = active_step(seconds)
    title = str(step["title"])
    caption = str(step["caption"])
    hint = str(step["hint"])
    title_font = load_font(max(24, width // 54))
    body_font = load_font(max(26, width // 58))
    small_font = load_font(max(18, width // 82))

    # Top chapter strip.
    strip_h = max(54, height // 15)
    draw.rectangle((0, 0, width, strip_h), fill=(255, 255, 255, 218))
    draw.rectangle((0, strip_h - 2, width, strip_h), fill=(35, 120, 86, 150))
    draw.text((28, 16), title, font=title_font, fill=(19, 31, 24, 255))

    total = INTERACTIVE_STEPS[-1]["end"]
    progress = min(1.0, max(0.0, seconds / float(total)))
    bar_x0 = width * 0.34
    bar_x1 = width - 36
    bar_y = strip_h / 2 + 5
    draw.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 8), radius=4, fill=(210, 224, 214, 255))
    draw.rounded_rectangle(
        (bar_x0, bar_y, bar_x0 + (bar_x1 - bar_x0) * progress, bar_y + 8),
        radius=4,
        fill=(35, 120, 86, 255),
    )
    for idx, item in enumerate(INTERACTIVE_STEPS, start=1):
        x = bar_x0 + (bar_x1 - bar_x0) * (float(item["start"]) / float(total))
        active = item is step
        fill = (35, 120, 86, 255) if seconds >= float(item["start"]) else (160, 178, 166, 255)
        radius = 12 if active else 8
        draw.ellipse((x - radius, bar_y - radius + 4, x + radius, bar_y + radius + 4), fill=fill)
        if active:
            draw.text((x - 5, bar_y - 7), str(idx), font=small_font, fill=(255, 255, 255, 255))

    # Bottom clear caption: no background box, just text with outline.
    lines = textwrap.wrap(caption, width=max(34, width // 46))
    line_height = max(32, height // 30)
    text_y = height - max(122, height // 8)
    for line in lines:
        text_width = draw.textlength(line, font=body_font)
        text_x = (width - text_width) / 2
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((text_x + dx, text_y + dy), line, font=body_font, fill=(5, 12, 9, 230))
        draw.text((text_x, text_y), line, font=body_font, fill=(255, 255, 255, 255))
        text_y += line_height

    # Small contextual hint pill.
    hint_text = f"Showing: {hint}"
    hint_w = draw.textlength(hint_text, font=small_font) + 30
    hint_h = 34
    hint_x = 28
    hint_y = strip_h + 18
    draw.rounded_rectangle(
        (hint_x, hint_y, min(width - 28, hint_x + hint_w), hint_y + hint_h),
        radius=17,
        fill=(255, 255, 255, 224),
        outline=(35, 120, 86, 160),
        width=2,
    )
    draw.text((hint_x + 15, hint_y + 8), hint_text, font=small_font, fill=(24, 47, 34, 255))

    return Image.alpha_composite(image, overlay).convert("RGB")


def srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def write_srt(path: Path, captions: list[tuple[float, float, str]]) -> None:
    blocks = []
    for idx, (start, end, text) in enumerate(captions, start=1):
        blocks.append(f"{idx}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{text}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frames_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--srt", type=Path)
    parser.add_argument("--variant", choices=["showcase", "guided"], default="showcase")
    parser.add_argument("--style", choices=["box", "clear", "interactive"], default="box")
    args = parser.parse_args()
    captions = GUIDED_CAPTIONS if args.variant == "guided" else CAPTIONS

    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(args.frames_dir.glob("*.jpg"))
    for index, frame in enumerate(frames):
        seconds = index / args.fps
        text = caption_for_time(seconds, captions)
        image = Image.open(frame)
        if args.style == "interactive":
            image = render_interactive_overlay(image, seconds)
        elif text:
            image = render_caption(image, text, clear_style=args.style == "clear")
        image.save(args.output_dir / frame.name, quality=90)

    if args.srt:
        args.srt.parent.mkdir(parents=True, exist_ok=True)
        write_srt(args.srt, captions)


if __name__ == "__main__":
    main()
