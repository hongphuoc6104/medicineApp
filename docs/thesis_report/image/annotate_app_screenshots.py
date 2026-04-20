#!/usr/bin/env python3
"""Create thesis-style annotated app screenshots.

Pattern follows the sample thesis, but pushes numbered callouts out to the
frame margin so they do not sit on top of the UI itself.
"""

from __future__ import annotations

from pathlib import Path

from math import hypot

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "app"

FRAME_COLOR = "#e4f6d7"
INNER_COLOR = "#ffffff"
STROKE_COLOR = "#101010"
NUMBER_FILL = "#101010"
NUMBER_TEXT = "#ffffff"
LEADER_COLOR = "#1f1f1f"

OUTER_PAD_X = 34
OUTER_PAD_Y = 28
INNER_PAD_X = 32
INNER_PAD_Y = 24


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT = load_font(26)


CONFIGS = {
    "scan_camera": {
        "source": "scan_camera.png",
        "target": "scan_camera_annotated.png",
        "crop": (20, 60, 926, 1950),
        "callouts": [
            (1, -18, 82, 0, 82),
            (2, 924, 84, 906, 84),
            (3, 924, 1410, 906, 1410),
            (4, 453, 1910, 453, 1890),
        ],
    },
    "scan_review": {
        "source": "scan_review.png",
        "target": "scan_review_annotated.png",
        "crop": (24, 150, 922, 1860),
        "callouts": [
            (1, -18, 166, 0, 166),
            (2, -18, 450, 0, 450),
            (3, 916, 1328, 898, 1328),
            (4, 916, 1622, 898, 1622),
        ],
    },
    "set_schedule": {
        "source": "set_schedule.png",
        "target": "set_schedule_annotated.png",
        "crop": (26, 145, 922, 1915),
        "callouts": [
            (1, -18, 242, 0, 242),
            (2, 914, 548, 896, 548),
            (3, -18, 1118, 0, 1118),
            (4, 914, 1648, 896, 1648),
        ],
    },
    "home_today": {
        "source": "home_today.png",
        "target": "home_today_annotated.png",
        "crop": (24, 130, 922, 1700),
        "callouts": [
            (1, -18, 262, 0, 262),
            (2, 916, 268, 898, 268),
            (3, 916, 1112, 898, 1112),
            (4, 916, 1508, 898, 1508),
        ],
    },
    "history_week": {
        "source": "history_week_chart.png",
        "target": "history_week_annotated.png",
        "crop": (24, 125, 922, 1740),
        "callouts": [
            (1, -18, 180, 0, 180),
            (2, 916, 184, 898, 184),
            (3, 916, 476, 898, 476),
            (4, -18, 1135, 0, 1135),
        ],
    },
}


def draw_callouts(canvas: Image.Image, image_box: tuple[int, int], callouts: list[tuple[int, int, int, int, int]]) -> Image.Image:
    draw = ImageDraw.Draw(canvas)
    image_x, image_y = image_box
    radius = 20
    for number, badge_x, badge_y, anchor_x, anchor_y in callouts:
        badge_cx = image_x + badge_x
        badge_cy = image_y + badge_y
        target_x = image_x + anchor_x
        target_y = image_y + anchor_y

        dx = target_x - badge_cx
        dy = target_y - badge_cy
        distance = max(hypot(dx, dy), 1)
        start_x = badge_cx + dx * radius / distance
        start_y = badge_cy + dy * radius / distance

        draw.line((start_x, start_y, target_x, target_y), fill=LEADER_COLOR, width=3)
        draw.ellipse(
            (badge_cx - radius, badge_cy - radius, badge_cx + radius, badge_cy + radius),
            fill=NUMBER_FILL,
            outline=INNER_COLOR,
            width=3,
        )
        text = str(number)
        bbox = draw.textbbox((0, 0), text, font=FONT)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((badge_cx - tw / 2, badge_cy - th / 2 - 2), text, fill=NUMBER_TEXT, font=FONT)
    return canvas


def compose_frame(image: Image.Image) -> Image.Image:
    canvas = Image.new(
        "RGB",
        (
            image.width + (OUTER_PAD_X + INNER_PAD_X) * 2,
            image.height + (OUTER_PAD_Y + INNER_PAD_Y) * 2,
        ),
        FRAME_COLOR,
    )
    draw = ImageDraw.Draw(canvas)
    inner_box = (
        OUTER_PAD_X,
        OUTER_PAD_Y,
        canvas.width - OUTER_PAD_X,
        canvas.height - OUTER_PAD_Y,
    )
    draw.rectangle(inner_box, fill=INNER_COLOR)
    image_pos = (OUTER_PAD_X + INNER_PAD_X, OUTER_PAD_Y + INNER_PAD_Y)
    canvas.paste(image, image_pos)
    return canvas, image_pos


def process(config: dict[str, object]) -> None:
    source = ASSETS / str(config["source"])
    target = ASSETS / str(config["target"])
    crop = tuple(config["crop"])
    callouts = list(config["callouts"])

    with Image.open(source) as raw:
        cropped = raw.crop(crop).convert("RGB")
        framed, image_pos = compose_frame(cropped)
        annotated = draw_callouts(framed, image_pos, callouts)
        framed = annotated
        framed.save(target, format="PNG", optimize=True)


def main() -> None:
    for config in CONFIGS.values():
        process(config)
    print(f"Annotated {len(CONFIGS)} screenshots in {ASSETS}")


if __name__ == "__main__":
    main()
