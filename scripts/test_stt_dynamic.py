import json
import os
import glob
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TextBlock:
    text: str
    confidence: float
    bbox: list


# ── Hàm phân chia cột động (Dynamic Gap Detection) ────────────────────────
def detect_dynamic_cols(blocks, num_cols=4):
    """
    Tự động tìm (num_cols - 1) ranh giới cột dựa trên khoảng trống (gap)
    lớn nhất theo trục X.
    """
    if len(blocks) < num_cols:
        return []

    # Thu thập tất cả hộp bao (bounding boxes)
    all_x_bounds = []
    for b in blocks:
        xs = [pt[0] for pt in b.bbox]
        min_x = min(xs)
        max_x = max(xs)
        # Chỉ xét các block nhỏ/vừa để tìm gap chính xác.
        # Bỏ qua các block quá dài (ví dụ: dòng mô tả dài chạy qua nhiều cột)
        if max_x - min_x < 500:
            all_x_bounds.append((min_x, max_x))

    if len(all_x_bounds) < num_cols:
        return []

    # Sắp xếp các block theo tọa độ X bên trái
    all_x_bounds.sort(key=lambda x: x[0])

    # Tìm các khoảng trống (gaps) giữa block X_{i} kết thúc và block X_{i+1} bắt đầu
    gaps = []
    current_max_x = all_x_bounds[0][1]

    for i in range(1, len(all_x_bounds)):
        next_min_x, next_max_x = all_x_bounds[i]

        # Nếu có khoảng trống giữa block hiện tại và block tiếp theo
        if next_min_x > current_max_x:
            gap_size = next_min_x - current_max_x
            gap_center = (next_min_x + current_max_x) / 2.0
            gaps.append((gap_size, gap_center))

        # Cập nhật đuôi xa nhất bên phải
        current_max_x = max(current_max_x, next_max_x)

    # Lấy (num_cols - 1) khoảng trống lớn nhất làm ranh giới cột
    # Sắp xếp theo gap_size giảm dần
    gaps.sort(key=lambda x: x[0], reverse=True)

    # Trích xuất tọa độ trung tâm của các khe hở lớn ấy và sắp xếp từ trái qua phải
    top_gaps = [g[1] for g in gaps[: num_cols - 1]]
    top_gaps.sort()

    return top_gaps


def group_by_stt_dynamic(blocks: list) -> list:
    """Phiên bản mới: Sử dụng Dynamic Gap thay vì Hardcode tỉ lệ."""
    if not blocks:
        return []

    def _y_center(bbox):
        ys = [pt[1] for pt in bbox]
        return (sum(ys)) / len(ys)

    def _x_center(bbox):
        xs = [pt[0] for pt in bbox]
        return (sum(xs)) / len(xs)

    # 1. Tìm ranh giới cột CHÍNH XÁC từ mảng tọa độ tuyệt đối
    # Mặc định cần 4 cột (STT, Tên+HD, Số lượng, Đơn vị) -> 3 ranh giới
    col_bounds = detect_dynamic_cols(blocks, num_cols=4)
    if len(col_bounds) < 3:
        # Nếu không đủ 3 gap lớn (ví dụ đơn quá lộn xộn, mờ),
        # fallback về fallback tương đối
        all_xs = [pt[0] for b in blocks for pt in b.bbox]
        min_x, max_x = min(all_xs), max(all_xs)
        W = max(max_x - min_x, 1)
        col_bounds = [min_x + W * 0.13, min_x + W * 0.75, min_x + W * 0.88]

    def _col_idx(block):
        xc = _x_center(block.bbox)
        for i, bound in enumerate(col_bounds):
            if xc <= bound:
                return i
        return len(col_bounds)

    # 2. Tìm Anchor STT
    stt_re = re.compile(r"^\d+$")
    anchors = [b for b in blocks if _col_idx(b) == 0 and stt_re.match(b.text.strip())]
    anchors.sort(key=lambda b: _y_center(b.bbox))

    if not anchors:
        return blocks

    # 3. Phân band
    boundaries = [
        (_y_center(anchors[i].bbox) + _y_center(anchors[i + 1].bbox)) / 2.0
        for i in range(len(anchors) - 1)
    ]
    bands = [[] for _ in anchors]
    headers = []

    for b in blocks:
        yc = _y_center(b.bbox)
        if yc < _y_center(anchors[0].bbox) - 20:
            headers.append(b)
            continue
        ok = False
        for i, bd in enumerate(boundaries):
            if yc <= bd:
                bands[i].append(b)
                ok = True
                break
        if not ok:
            bands[-1].append(b)

    # 4. Gộp
    merged = []
    headers.sort(key=lambda b: _y_center(b.bbox))
    merged.extend(headers)

    num_cols = len(col_bounds) + 1
    for band_idx, band in enumerate(bands):
        if not band:
            continue
        cols = {i: [] for i in range(num_cols)}
        for b in band:
            cols[_col_idx(b)].append(b)

        for c in cols.values():
            c.sort(key=lambda b: _y_center(b.bbox))

        parts = [
            " ".join(b.text.strip() for b in cols[c] if b.text.strip())
            for c in sorted(cols)
            if cols[c]
        ]
        res = " | ".join(p for p in parts if p)

        all_pts = [pt for b in band for pt in b.bbox]
        xs = [pt[0] for pt in all_pts]
        ys = [pt[1] for pt in all_pts]
        m_bbox = [
            [min(xs), min(ys)],
            [max(xs), min(ys)],
            [max(xs), max(ys)],
            [min(xs), max(ys)],
        ]

        merged.append(TextBlock(text=res, confidence=1.0, bbox=m_bbox))

    return merged, col_bounds


# ── Main ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parents[1]
    file_path = (
        root_dir
        / "data"
        / "output"
        / "phase_a"
        / "IMG_20260209_180423"
        / "step-3.2_ocr.json"
    )
    if not os.path.exists(file_path):
        print("Không tìm thấy file kết quả OCR. Thực thi pipeline trước.")
        exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    blocks_data = data if isinstance(data, list) else data.get("blocks", [])
    blocks = [TextBlock(b["text"], b["confidence"], b["bbox"]) for b in blocks_data]

    print("=" * 70)
    print("TEST: DYNAMIC GAP DETECTION")
    print("=" * 70)

    merged, dynamic_bounds = group_by_stt_dynamic(blocks)

    print(f"Khoảng X biên của các cột (Tuyệt đối): {[int(x) for x in dynamic_bounds]}")
    all_x = [pt[0] for b in blocks for pt in b.bbox]
    W = max(all_x) - min(all_x)
    print(
        f"Khoảng X biên của các cột (Tỉ lệ %):  {[round((x - min(all_x)) / W, 2) for x in dynamic_bounds]}"
    )

    print("\nKết quả Gộp:")
    for b in merged:
        if "|" in b.text:
            print(f"  → {b.text}")
