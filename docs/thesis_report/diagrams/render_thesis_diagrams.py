#!/usr/bin/env python3
"""Render thesis diagrams optimized for A4 readability.

Outputs SVG and PNG files into docs/thesis_report/assets/diagrams.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET

try:
    import cairosvg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("cairosvg is required to render thesis diagrams") from exc


ROOT = os.path.dirname(os.path.dirname(__file__))
ASSETS = os.path.join(ROOT, "assets", "diagrams")

PALETTE = {
    "ink": "#2f2f2f",
    "text": "#111111",
    "muted": "#555555",
    "blue_fill": "#fcfcfc",
    "blue_stroke": "#3e3e3e",
    "green_fill": "#f8f8f8",
    "green_stroke": "#3e3e3e",
    "yellow_fill": "#f6f6f6",
    "yellow_stroke": "#3e3e3e",
    "orange_fill": "#fbfbfb",
    "orange_stroke": "#3e3e3e",
    "red_fill": "#f5f5f5",
    "red_stroke": "#3e3e3e",
    "purple_fill": "#f7f7f7",
    "purple_stroke": "#3e3e3e",
    "gray_fill": "#f4f4f4",
    "gray_stroke": "#6a6a6a",
    "db_fill": "#fbfbfb",
    "db_stroke": "#3e3e3e",
}


def svg_root(width: int, height: int) -> ET.Element:
    root = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(width),
        height=str(height),
        viewBox=f"0 0 {width} {height}",
    )
    defs = ET.SubElement(root, "defs")
    marker = ET.SubElement(
        defs,
        "marker",
        id="arrow",
        markerWidth="10",
        markerHeight="8",
        refX="9",
        refY="4",
        orient="auto",
    )
    ET.SubElement(
        marker,
        "path",
        d="M 0 0 L 10 4 L 0 8 z",
        fill=PALETTE["ink"],
    )
    open_marker = ET.SubElement(
        defs,
        "marker",
        id="open-arrow",
        markerWidth="10",
        markerHeight="8",
        refX="9",
        refY="4",
        orient="auto",
    )
    ET.SubElement(
        open_marker,
        "path",
        d="M 0 0 L 10 4 L 0 8",
        fill="none",
        stroke=PALETTE["ink"],
        **{"stroke-width": "1.4"},
    )
    style = ET.SubElement(root, "style")
    style.text = "text { font-family: Arial, sans-serif; }"
    ET.SubElement(root, "rect", x="0", y="0", width=str(width), height=str(height), fill="white")
    return root


def add_text(parent, x, y, text, size=12, fill=None, weight=None, anchor="middle", italic=False):
    attrs = {
        "x": f"{x}",
        "y": f"{y}",
        "font-size": f"{size}",
        "fill": fill or PALETTE["text"],
        "text-anchor": anchor,
    }
    if weight:
        attrs["font-weight"] = weight
    if italic:
        attrs["font-style"] = "italic"
    node = ET.SubElement(parent, "text", **attrs)
    node.text = text
    return node


def add_multiline_text(parent, x, y, lines, size=12, line_gap=16, fill=None, weight=None, anchor="middle"):
    text = ET.SubElement(
        parent,
        "text",
        x=f"{x}",
        y=f"{y}",
        **{
            "font-size": f"{size}",
            "fill": fill or PALETTE["text"],
            "text-anchor": anchor,
        },
    )
    if weight:
        text.set("font-weight", weight)
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else line_gap
        tspan = ET.SubElement(text, "tspan", x=f"{x}", dy=f"{dy}")
        tspan.text = line
    return text


def rounded_box(parent, x, y, w, h, fill, stroke, stroke_width=1.5, rx=10):
    return ET.SubElement(
        parent,
        "rect",
        x=f"{x}",
        y=f"{y}",
        width=f"{w}",
        height=f"{h}",
        rx=f"{rx}",
        fill=fill,
        stroke=stroke,
        **{"stroke-width": f"{stroke_width}"},
    )


def pill_box(parent, x, y, w, h, fill, stroke, text, size=13):
    rounded_box(parent, x, y, w, h, fill, stroke, stroke_width=1.4, rx=h / 2)
    add_text(parent, x + w / 2, y + h / 2 + 5, text, size=size, fill=PALETTE["text"], weight="bold")


def cylinder(parent, x, y, w, h, fill, stroke, title_lines, body_lines):
    body_h = h - 22
    ET.SubElement(parent, "rect", x=f"{x}", y=f"{y+11}", width=f"{w}", height=f"{body_h}", fill=fill)
    ET.SubElement(parent, "line", x1=f"{x}", y1=f"{y+11}", x2=f"{x}", y2=f"{y+11+body_h}", stroke=stroke, **{"stroke-width": "1.4"})
    ET.SubElement(parent, "line", x1=f"{x+w}", y1=f"{y+11}", x2=f"{x+w}", y2=f"{y+11+body_h}", stroke=stroke, **{"stroke-width": "1.4"})
    ET.SubElement(parent, "ellipse", cx=f"{x+w/2}", cy=f"{y+11}", rx=f"{w/2}", ry="11", fill=fill, stroke=stroke, **{"stroke-width": "1.4"})
    ET.SubElement(parent, "ellipse", cx=f"{x+w/2}", cy=f"{y+11+body_h}", rx=f"{w/2}", ry="11", fill=fill, stroke=stroke, **{"stroke-width": "1.4"})
    add_multiline_text(parent, x + w / 2, y + 28, title_lines, size=12, line_gap=15, weight="bold")
    add_multiline_text(parent, x + w / 2, y + 58, body_lines, size=11, line_gap=15, fill=PALETTE["muted"])


def diamond(parent, x, y, w, h, fill, stroke, lines, size=12):
    points = f"{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}"
    ET.SubElement(parent, "polygon", points=points, fill=fill, stroke=stroke, **{"stroke-width": "1.5"})
    start_y = y + h / 2 - (len(lines) - 1) * 8
    for idx, line in enumerate(lines):
        add_text(parent, x + w / 2, start_y + idx * 16 + 4, line, size=size)


def arrow(parent, x1, y1, x2, y2, dashed=False, open_arrow=False, width=1.5):
    attrs = {
        "x1": f"{x1}",
        "y1": f"{y1}",
        "x2": f"{x2}",
        "y2": f"{y2}",
        "stroke": PALETTE["ink"],
        "stroke-width": f"{width}",
        "fill": "none",
        "marker-end": "url(#open-arrow)" if open_arrow else "url(#arrow)",
    }
    if dashed:
        attrs["stroke-dasharray"] = "7,5"
    ET.SubElement(parent, "line", **attrs)


def path_arrow(parent, d, dashed=False, open_arrow=False, width=1.5):
    attrs = {
        "d": d,
        "stroke": PALETTE["ink"],
        "stroke-width": f"{width}",
        "fill": "none",
        "marker-end": "url(#open-arrow)" if open_arrow else "url(#arrow)",
    }
    if dashed:
        attrs["stroke-dasharray"] = "7,5"
    ET.SubElement(parent, "path", **attrs)


def connector(parent, x1, y1, x2, y2, dashed=False, width=1.5):
    attrs = {
        "x1": f"{x1}",
        "y1": f"{y1}",
        "x2": f"{x2}",
        "y2": f"{y2}",
        "stroke": PALETTE["ink"],
        "stroke-width": f"{width}",
        "fill": "none",
    }
    if dashed:
        attrs["stroke-dasharray"] = "7,5"
    ET.SubElement(parent, "line", **attrs)


def path_connector(parent, d, dashed=False, width=1.5):
    attrs = {
        "d": d,
        "stroke": PALETTE["ink"],
        "stroke-width": f"{width}",
        "fill": "none",
    }
    if dashed:
        attrs["stroke-dasharray"] = "7,5"
    ET.SubElement(parent, "path", **attrs)


def label_box(parent, x, y, text):
    rounded_box(parent, x - 42, y - 11, 84, 22, "white", "none", stroke_width=0, rx=6)
    add_text(parent, x, y + 4, text, size=10, fill=PALETTE["muted"], italic=True)


def actor(parent, x, y, label):
    ET.SubElement(parent, "circle", cx=f"{x}", cy=f"{y}", r="16", fill="white", stroke=PALETTE["ink"], **{"stroke-width": "1.5"})
    ET.SubElement(parent, "line", x1=f"{x}", y1=f"{y+16}", x2=f"{x}", y2=f"{y+58}", stroke=PALETTE["ink"], **{"stroke-width": "1.5"})
    ET.SubElement(parent, "line", x1=f"{x-28}", y1=f"{y+31}", x2=f"{x+28}", y2=f"{y+31}", stroke=PALETTE["ink"], **{"stroke-width": "1.5"})
    ET.SubElement(parent, "line", x1=f"{x}", y1=f"{y+58}", x2=f"{x-24}", y2=f"{y+90}", stroke=PALETTE["ink"], **{"stroke-width": "1.5"})
    ET.SubElement(parent, "line", x1=f"{x}", y1=f"{y+58}", x2=f"{x+24}", y2=f"{y+90}", stroke=PALETTE["ink"], **{"stroke-width": "1.5"})
    add_text(parent, x, y + 114, label, size=13, weight="bold")


def entity(parent, x, y, w, h, title_lines, attrs, fill, stroke):
    rounded_box(parent, x, y, w, h, fill, stroke, stroke_width=1.4, rx=10)
    ET.SubElement(parent, "line", x1=f"{x}", y1=f"{y+34}", x2=f"{x+w}", y2=f"{y+34}", stroke=stroke, **{"stroke-width": "1.2"})
    add_multiline_text(parent, x + w / 2, y + 18, title_lines, size=12, line_gap=14, weight="bold")
    current_y = y + 58
    for attr in attrs:
        add_text(parent, x + 14, current_y, attr, size=10.5, anchor="start", fill=PALETTE["muted"])
        current_y += 16


def save_svg_and_png(root: ET.Element, name: str, scale: float = 2.6):
    os.makedirs(ASSETS, exist_ok=True)
    svg_path = os.path.join(ASSETS, f"{name}.svg")
    png_path = os.path.join(ASSETS, f"{name}.png")
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(svg_path, encoding="unicode", xml_declaration=True)
    cairosvg.svg2png(url=svg_path, write_to=png_path, scale=scale)
    return svg_path, png_path


def render_architecture():
    svg = svg_root(980, 640)
    pill_box(svg, 390, 20, 200, 42, PALETTE["orange_fill"], PALETTE["orange_stroke"], "Người dùng")

    rounded_box(svg, 40, 96, 900, 132, PALETTE["blue_fill"], PALETTE["blue_stroke"], stroke_width=1.6)
    add_text(svg, 72, 118, "Tầng 1 - Ứng dụng di động (Flutter)", size=12, anchor="start", weight="bold", fill="#222222")
    mobile_labels = [
        ["Quét đơn thuốc"],
        ["Rà soát", "danh sách thuốc"],
        ["Lập lịch", "dùng thuốc"],
        ["Lịch hôm nay", "và theo dõi"],
    ]
    for idx, lines in enumerate(mobile_labels):
        x = 66 + idx * 214
        rounded_box(svg, x, 142, 184, 58, "#f6fbff", PALETTE["blue_stroke"], stroke_width=1.2, rx=8)
        add_multiline_text(svg, x + 92, 166, lines, size=11.5, line_gap=14)

    rounded_box(svg, 40, 256, 900, 144, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.6)
    add_text(svg, 72, 278, "Tầng 2 - Máy chủ chính (Node.js / Express)", size=12, anchor="start", weight="bold", fill="#222222")
    backend_labels = [
        ["Xác thực", "và phân quyền"],
        ["Quét đơn", "và lưu kết quả"],
        ["Kế hoạch,", "slots và logs"],
        ["Tra cứu thuốc", "và API phụ trợ"],
    ]
    for idx, lines in enumerate(backend_labels):
        x = 66 + idx * 214
        rounded_box(svg, x, 304, 184, 64, "#f7fcf8", PALETTE["green_stroke"], stroke_width=1.2, rx=8)
        add_multiline_text(svg, x + 92, 327, lines, size=11.5, line_gap=14)

    rounded_box(svg, 40, 430, 900, 144, PALETTE["yellow_fill"], PALETTE["yellow_stroke"], stroke_width=1.6)
    add_text(svg, 72, 452, "Tầng 3 - Dịch vụ AI (FastAPI)", size=12, anchor="start", weight="bold", fill="#222222")
    ai_labels = [
        ["Detect và crop", "đơn thuốc"],
        ["Preprocess +", "quality gate"],
        ["Hybrid OCR +", "group by STT"],
        ["PhoBERT NER +", "drug lookup"],
    ]
    for idx, lines in enumerate(ai_labels):
        x = 66 + idx * 214
        rounded_box(svg, x, 478, 184, 64, "#fffdf5", PALETTE["yellow_stroke"], stroke_width=1.2, rx=8)
        add_multiline_text(svg, x + 92, 501, lines, size=11.5, line_gap=14)

    cylinder(svg, 64, 588, 220, 48, PALETTE["db_fill"], PALETTE["db_stroke"], ["PostgreSQL"], ["users, scans, plans, logs"])
    cylinder(svg, 672, 588, 240, 48, PALETTE["db_fill"], PALETTE["db_stroke"], ["Drug DB + Models"], ["9.284 thuốc, weights AI"])

    arrow(svg, 490, 62, 490, 96)
    arrow(svg, 490, 228, 490, 256)
    arrow(svg, 490, 400, 490, 430)
    path_arrow(svg, "M 118 400 L 118 560 L 174 560 L 174 588")
    label_box(svg, 226, 558, "Đọc / ghi")
    arrow(svg, 792, 574, 792, 588)
    label_box(svg, 850, 582, "Tra cứu")

    save_svg_and_png(svg, "architecture_a4_v3")


def render_use_case():
    svg = svg_root(980, 560)
    actor(svg, 88, 206, "Người dùng")
    rounded_box(svg, 234, 24, 680, 500, "#fbfcfe", PALETTE["gray_stroke"], stroke_width=1.2, rx=10)
    add_text(svg, 574, 52, "Hệ thống MedicineApp", size=15, weight="bold", fill="#222222")

    ellipses = [
        (576, 94, ["Đăng nhập / Đăng ký"]),
        (576, 154, ["Quét đơn thuốc"]),
        (576, 214, ["Rà soát danh sách thuốc"]),
        (576, 274, ["Lập lịch dùng thuốc"]),
        (576, 334, ["Xem lịch hôm nay"]),
        (576, 394, ["Ghi nhận trạng thái", "uống thuốc"]),
        (576, 454, ["Xem lịch sử kế hoạch", "và nhật ký"]),
    ]

    for cx, cy, lines in ellipses:
        ET.SubElement(svg, "ellipse", cx=f"{cx}", cy=f"{cy}", rx="128", ry="28", fill=PALETTE["blue_fill"], stroke=PALETTE["blue_stroke"], **{"stroke-width": "1.3"})
        add_multiline_text(svg, cx, cy - (8 if len(lines) > 1 else -4), lines, size=12, line_gap=15)
        connector(svg, 126, cy, cx - 128, cy, width=1.4)

    save_svg_and_png(svg, "use_case_a4_v3")


def render_sequence():
    svg = svg_root(1180, 760)
    lanes = [
        (90, "Người dùng", PALETTE["orange_fill"], PALETTE["orange_stroke"]),
        (300, "Ứng dụng\ndi động", PALETTE["blue_fill"], PALETTE["blue_stroke"]),
        (520, "Máy chủ\nNode.js", PALETTE["green_fill"], PALETTE["green_stroke"]),
        (760, "Dịch vụ AI\n(FastAPI)", PALETTE["yellow_fill"], PALETTE["yellow_stroke"]),
        (1040, "PostgreSQL", PALETTE["db_fill"], PALETTE["db_stroke"]),
    ]
    for x, label, fill, stroke in lanes:
        rounded_box(svg, x - 74, 20, 148, 56, fill, stroke, stroke_width=1.5, rx=8)
        add_multiline_text(svg, x, 43 if "\n" not in label else 34, label.split("\n"), size=13, line_gap=16, weight="bold")
        ET.SubElement(svg, "line", x1=f"{x}", y1="76", x2=f"{x}", y2="728", stroke="#c5ccd3", **{"stroke-width": "1.2", "stroke-dasharray": "6,5"})

    ET.SubElement(svg, "rect", x="514", y="206", width="12", height="326", fill="#dceafe", stroke="#8eb0d8", **{"stroke-width": "0.8"})
    ET.SubElement(svg, "rect", x="754", y="260", width="12", height="188", fill="#fff4c9", stroke="#d9c06e", **{"stroke-width": "0.8"})

    steps = [
        (102, 90, 300, 90, "Chụp ảnh đơn thuốc", False, False),
        (300, 142, 356, 142, "Kiểm tra chất lượng cục bộ", False, False),
        (300, 206, 520, 206, "Gửi ảnh tới POST /api/scan", False, False),
        (520, 260, 760, 260, "Node.js chuyển tiếp ảnh sang AI", False, False),
        (760, 316, 836, 316, "Detect, crop, preprocess, quality gate", False, False),
        (760, 372, 836, 372, "OCR, group by STT, NER, drug lookup", False, False),
        (760, 448, 520, 448, "Trả về danh sách thuốc có cấu trúc", True, True),
        (520, 516, 1040, 516, "Lưu scans, quality state và kết quả", False, False),
        (520, 584, 300, 584, "Trả về scan result cho ứng dụng", True, True),
        (300, 652, 90, 652, "Mở màn hình rà soát trước khi lập lịch", True, True),
    ]
    for idx, (x1, y1, x2, y2, label, dashed, open_arrow) in enumerate(steps, start=1):
        arrow(svg, x1, y1, x2, y2, dashed=dashed, open_arrow=open_arrow)
        add_text(svg, (x1 + x2) / 2, y1 - 10, label, size=11.5, fill="#24313a")
        ET.SubElement(svg, "circle", cx=f"{x1 + 18 if x2 > x1 else x1 - 18}", cy=f"{y1}", r="11", fill="#eef2ff", stroke=PALETTE["db_stroke"], **{"stroke-width": "1.0"})
        add_text(svg, x1 + 18 if x2 > x1 else x1 - 18, y1 + 4, str(idx), size=10.5, weight="bold", fill="#2f3f8a")

    save_svg_and_png(svg, "sequence_scan_a4_v3")


def render_scan_flow():
    svg = svg_root(1380, 720)
    pill_box(svg, 34, 304, 188, 42, PALETTE["blue_fill"], PALETTE["blue_stroke"], "Ảnh đơn thuốc đầu vào")

    main_nodes = [
        (270, 282, 190, 76, PALETTE["green_fill"], PALETTE["green_stroke"], ["1. YOLO Detect & Crop", "Convex Hull crop"]),
        (500, 282, 208, 76, PALETTE["green_fill"], PALETTE["green_stroke"], ["2. Preprocess", "Deskew Modulo 90 + AI orientation"]),
        (916, 282, 216, 76, PALETTE["green_fill"], PALETTE["green_stroke"], ["3. Hybrid OCR", "PaddleOCR + VietOCR"]),
        (1158, 282, 170, 76, PALETTE["green_fill"], PALETTE["green_stroke"], ["3.5 Group by STT", "ổn định chuỗi OCR"]),
        (1158, 416, 150, 70, PALETTE["green_fill"], PALETTE["green_stroke"], ["4. PhoBERT NER"]),
        (1158, 540, 170, 70, PALETTE["green_fill"], PALETTE["green_stroke"], ["5. Drug lookup", "DB 9.284 thuốc"]),
        (916, 540, 220, 46, PALETTE["blue_fill"], PALETTE["blue_stroke"], ["Danh sách thuốc để người dùng rà soát"]),
    ]
    for x, y, w, h, fill, stroke, lines in main_nodes:
        rounded_box(svg, x, y, w, h, fill, stroke, stroke_width=1.35, rx=10)
        add_multiline_text(svg, x + w / 2, y + h / 2 - (7 if len(lines) > 1 else -4), lines, size=12, line_gap=15)

    diamond(svg, 734, 270, 126, 100, PALETTE["yellow_fill"], PALETTE["yellow_stroke"], ["Quality", "gate"], size=12)
    rounded_box(svg, 720, 112, 170, 60, PALETTE["red_fill"], PALETTE["red_stroke"], stroke_width=1.3, rx=10)
    add_multiline_text(svg, 805, 136, ["Reject ảnh", "Yêu cầu chụp lại"], size=11.5, line_gap=14)
    diamond(svg, 734, 432, 126, 100, PALETTE["yellow_fill"], PALETTE["yellow_stroke"], ["Table ROI", "hợp lệ?"], size=12)
    rounded_box(svg, 916, 406, 216, 76, PALETTE["purple_fill"], PALETTE["purple_stroke"], stroke_width=1.3, rx=10)
    add_multiline_text(svg, 1024, 432, ["OCR trên Table ROI", "fallback full image nếu fail"], size=11.5, line_gap=15)

    arrow(svg, 222, 325, 270, 325)
    arrow(svg, 460, 325, 500, 325)
    arrow(svg, 708, 325, 734, 325)
    arrow(svg, 860, 325, 916, 325)
    path_arrow(svg, "M 797 270 L 797 172", width=1.4)
    label_box(svg, 866, 226, "Reject")
    path_arrow(svg, "M 797 370 L 797 432", width=1.4)
    label_box(svg, 866, 406, "Good / Warning")
    arrow(svg, 860, 482, 916, 444)
    label_box(svg, 900, 500, "Có ROI")
    path_arrow(svg, "M 734 532 L 734 575 L 916 575", width=1.4)
    label_box(svg, 836, 595, "Không có ROI")
    path_arrow(svg, "M 1132 444 L 1210 444 L 1210 358", width=1.4)
    path_arrow(svg, "M 1132 320 L 1158 320", width=1.4)
    arrow(svg, 1243, 358, 1243, 416)
    arrow(svg, 1233, 486, 1233, 540)
    arrow(svg, 1158, 563, 1136, 563)

    save_svg_and_png(svg, "scan_flow_a4_v3")


def relation(parent, x1, y1, x2, y2, label, start_card="1", end_card="N"):
    arrow(parent, x1, y1, x2, y2, width=1.3)
    add_text(parent, (x1 + x2) / 2, (y1 + y2) / 2 - 8, label, size=10.5, fill=PALETTE["muted"], italic=True)
    add_text(parent, x1 + (10 if x2 >= x1 else -10), y1 - 6, start_card, size=10.5, weight="bold", fill="#33507a")
    add_text(parent, x2 + (-12 if x2 >= x1 else 12), y2 - 6, end_card, size=10.5, weight="bold", fill="#33507a")


def relation_path(parent, d, label, label_x, label_y, start_card, start_x, start_y, end_card, end_x, end_y):
    path_arrow(parent, d, width=1.3)
    add_text(parent, label_x, label_y, label, size=10.5, fill=PALETTE["muted"], italic=True)
    add_text(parent, start_x, start_y, start_card, size=10.5, weight="bold", fill="#33507a")
    add_text(parent, end_x, end_y, end_card, size=10.5, weight="bold", fill="#33507a")


def render_erd():
    svg = svg_root(1280, 760)
    entity(svg, 50, 56, 240, 124, ["users"], ["id (PK)", "email", "name", "created_at"], PALETTE["orange_fill"], PALETTE["orange_stroke"])
    entity(svg, 360, 56, 250, 148, ["scan_sessions"], ["id (PK)", "user_id (FK)", "status", "converged", "merged_result"], PALETTE["blue_fill"], PALETTE["blue_stroke"])
    entity(svg, 690, 56, 240, 148, ["scans"], ["id (PK)", "user_id (FK)", "session_id (FK)", "quality_state", "drug_count"], PALETTE["blue_fill"], PALETTE["blue_stroke"])

    entity(svg, 360, 286, 270, 148, ["prescription_plans"], ["id (PK)", "user_id (FK)", "title", "start_date", "end_date", "is_active"], PALETTE["green_fill"], PALETTE["green_stroke"])
    entity(svg, 980, 286, 240, 124, ["prescription_plan_logs"], ["id (PK)", "plan_id (FK)", "occurrence_id", "slot_time", "status"], PALETTE["green_fill"], PALETTE["green_stroke"])
    entity(svg, 50, 570, 260, 132, ["prescription_plan_drugs"], ["id (PK)", "plan_id (FK)", "drug_name", "dosage", "sort_order"], PALETTE["green_fill"], PALETTE["green_stroke"])
    entity(svg, 360, 570, 260, 124, ["prescription_plan_slots"], ["id (PK)", "plan_id (FK)", "time", "sort_order"], PALETTE["green_fill"], PALETTE["green_stroke"])
    entity(svg, 690, 570, 290, 124, ["prescription_plan_slot_drugs"], ["id (PK)", "slot_id (FK)", "drug_id (FK)", "pills"], PALETTE["purple_fill"], PALETTE["purple_stroke"])

    relation_path(svg, "M 290 110 L 360 110", "sở hữu", 324, 94, "1", 298, 94, "N", 350, 94)
    relation_path(svg, "M 610 124 L 690 124", "gom ảnh quét", 636, 106, "1", 620, 108, "N", 680, 108)
    relation_path(svg, "M 290 78 L 330 78 L 330 30 L 810 30 L 810 56", "tạo lịch sử quét", 570, 18, "1", 300, 64, "N", 822, 42)
    relation_path(svg, "M 170 180 L 170 248 L 495 248 L 495 286", "tạo kế hoạch", 334, 232, "1", 182, 168, "N", 508, 272)
    relation_path(svg, "M 630 348 L 980 348", "ghi nhật ký", 804, 332, "1", 642, 332, "N", 970, 332)
    relation_path(svg, "M 440 434 L 440 520 L 180 520 L 180 570", "gồm thuốc", 310, 504, "1", 452, 420, "N", 192, 556)
    relation_path(svg, "M 520 434 L 520 570", "gồm khung giờ", 584, 502, "1", 532, 420, "N", 532, 556)
    relation_path(svg, "M 310 620 L 330 620 L 330 718 L 840 718 L 840 694", "gán thuốc", 566, 702, "1", 322, 604, "N", 852, 682)
    relation_path(svg, "M 620 636 L 690 636", "gán số viên", 652, 620, "1", 632, 620, "N", 680, 620)

    save_svg_and_png(svg, "erd_main_a4_v3")


def render_activity_create_plan():
    svg = svg_root(1240, 620)

    pill_box(svg, 58, 86, 120, 42, PALETTE["blue_fill"], PALETTE["blue_stroke"], "Bắt đầu")

    rounded_box(svg, 232, 58, 180, 86, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 322, 88, ["Quét đơn thuốc", "và nhận kết quả"], size=12, line_gap=16)

    diamond(svg, 474, 52, 140, 102, PALETTE["yellow_fill"], PALETTE["yellow_stroke"], ["Cần", "chỉnh sửa?"], size=12)

    rounded_box(svg, 680, 58, 188, 86, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 774, 88, ["Chọn ngày bắt đầu", "và số ngày dùng"], size=12, line_gap=16)

    rounded_box(svg, 926, 58, 188, 86, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 1020, 88, ["Chọn khung giờ", "uống thuốc"], size=12, line_gap=16)

    rounded_box(svg, 926, 240, 188, 86, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 1020, 270, ["Nhập số viên", "theo từng khung giờ"], size=12, line_gap=16)

    rounded_box(svg, 680, 422, 188, 86, PALETTE["green_fill"], PALETTE["green_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 774, 452, ["Lưu kế hoạch", "lên máy chủ"], size=12, line_gap=16)

    rounded_box(svg, 410, 422, 188, 86, PALETTE["purple_fill"], PALETTE["purple_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 504, 452, ["Thiết lập nhắc uống", "cục bộ trên thiết bị"], size=12, line_gap=16)

    rounded_box(svg, 150, 422, 188, 86, PALETTE["blue_fill"], PALETTE["blue_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 244, 452, ["Chuyển sang theo dõi", "liều uống trong ngày"], size=12, line_gap=16)

    rounded_box(svg, 410, 240, 188, 86, PALETTE["orange_fill"], PALETTE["orange_stroke"], stroke_width=1.4, rx=10)
    add_multiline_text(svg, 504, 270, ["Chỉnh sửa danh sách", "thuốc khi cần"], size=12, line_gap=16)

    pill_box(svg, 68, 450, 120, 42, PALETTE["blue_fill"], PALETTE["blue_stroke"], "Kết thúc")

    arrow(svg, 178, 107, 232, 101)
    arrow(svg, 412, 101, 474, 103)
    arrow(svg, 614, 103, 680, 101)
    label_box(svg, 648, 84, "Không")
    path_arrow(svg, "M 1020 144 L 1020 240")
    path_arrow(svg, "M 926 283 L 774 283 L 774 422")
    path_arrow(svg, "M 680 465 L 598 465")
    path_arrow(svg, "M 410 465 L 338 465")
    path_arrow(svg, "M 150 465 L 128 465")
    path_arrow(svg, "M 544 154 L 544 240 L 598 240")
    label_box(svg, 584, 188, "Có")
    path_arrow(svg, "M 598 283 L 680 283 L 680 101")

    save_svg_and_png(svg, "activity_create_plan")


def main():
    render_architecture()
    render_use_case()
    render_sequence()
    render_scan_flow()
    render_erd()
    render_activity_create_plan()
    print("Rendered thesis diagrams into", ASSETS)


if __name__ == "__main__":
    main()
