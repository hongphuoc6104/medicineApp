#!/usr/bin/env python3
"""Normalize thesis app screenshots into stable PNG assets.

Source: docs/thesis_report/image/app/*.jpg
Target: docs/thesis_report/assets/app/*.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "image" / "app"
DEST = ROOT / "assets" / "app"

MAPPINGS = {
    "hình thông báo ở màn hìn khóa.jpg": "notification_lockscreen.png",
    "màn hìn tra cứu (Kiểm tra hơp chất).jpg": "lookup_interaction_check.png",
    "màn hình chính có thuốc sắp đến giờ.jpg": "home_upcoming_today.png",
    "màn hình chụp hình đơn thuố quét đơn.jpg": "scan_camera.png",
    "màn hình lịch sử biểu đồ tuần.jpg": "history_week_chart.png",
    "màn hình lịch sử dùng lại kế hoạch thuốc cũ.jpg": "history_reuse_old_plan.png",
    "màn hình lịch sử phần chi tiết.jpg": "history_detail.png",
    "màn hình thiết lập giờ uống 2.jpg": "set_schedule_variant_2.png",
    "màn hình thiết lập giờ uống cuối.jpg": "set_schedule.png",
    "màn hinh thông báo kiểm tra.jpg": "notification_in_app_check.png",
    "màn hình xác nhận kết quả an toàn.jpg": "scan_review.png",
    "màn hình xác nhận kết quả- thông báo nguy hiểm.jpg": "scan_review_warning.png",
    "thiết lập giờ uống 3.jpg": "set_schedule_variant_3.png",
}


def export_png(src_path: Path, dest_path: Path) -> None:
    with Image.open(src_path) as image:
        normalized = image.convert("RGB")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(dest_path, format="PNG", optimize=True)


def main() -> None:
    missing = [name for name in MAPPINGS if not (SRC / name).exists()]
    if missing:
        raise SystemExit(f"Missing screenshot sources: {missing}")

    for source_name, target_name in MAPPINGS.items():
        export_png(SRC / source_name, DEST / target_name)

    # Canonical alias used by current thesis text.
    export_png(SRC / "màn hình chính có thuốc sắp đến giờ.jpg", DEST / "home_today.png")

    print(f"Exported {len(MAPPINGS) + 1} PNG assets to {DEST}")


if __name__ == "__main__":
    main()
