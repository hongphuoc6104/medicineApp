#!/usr/bin/env python3
"""
Hình 3.3 — Sơ đồ tuần tự (Sequence Diagram) chức năng quét đơn thuốc.
Cải tiến:
  - Canvas lớn hơn (W=1100, H=920): đủ chỗ cho 13 bước.
  - Font 14px cho participant, 13px cho message.
  - Số thứ tự: nền đậm (hình tròn) chữ trắng — rõ khi in đen trắng.
  - Participant box rõ ràng, lifeline dài đủ.
  - Không emoji. Toàn tiếng Việt có dấu.
"""

import xml.etree.ElementTree as ET
import os

# ─── Canvas ───────────────────────────────────────────────────────────────────
W = 1100
H = 920

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    # mũi tên đặc (gửi)
    m = ET.SubElement(defs, "marker", id="arr",
                      markerWidth="9", markerHeight="7",
                      refX="8", refY="3.5", orient="auto")
    ET.SubElement(m, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")
    # mũi tên mở (trả về)
    m2 = ET.SubElement(defs, "marker", id="arr-open",
                       markerWidth="9", markerHeight="7",
                       refX="8", refY="3.5", orient="auto")
    ET.SubElement(m2, "path",
                  d="M 0 0 L 9 3.5 L 0 7",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.6"})
    return defs

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = "text { font-family: Arial, sans-serif; }"

ET.SubElement(svg, "rect", x="0", y="0",
              width=str(W), height=str(H), fill="white")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def lbl(svg, x, y, txt, size=13, bold=False, color="#111",
        anchor="middle", italic=False):
    attrs = {
        "x": str(x), "y": str(y),
        "text-anchor": anchor,
        "font-size": str(size),
        "font-family": "Arial, sans-serif",
        "fill": color,
    }
    if bold:
        attrs["font-weight"] = "bold"
    if italic:
        attrs["font-style"] = "italic"
    t = ET.SubElement(svg, "text", **attrs)
    t.text = txt
    return t

# ─── Participants ──────────────────────────────────────────────────────────────
PART_TOP = 18
PART_H   = 58
PART_W   = 148

participants = [
    ("U",   70,  ["Người dùng"],                 "#fff7e8", "#b7791f", "#7a4512"),
    ("M",  268,  ["Ứng dụng", "di động"],         "#e8f3fd", "#3a7ec9", "#1a4a80"),
    ("N",  490,  ["Máy chủ", "Node.js"],          "#edfaf3", "#2d7a46", "#1a5c32"),
    ("P",  730,  ["Dịch vụ AI", "(FastAPI)"],     "#fffbec", "#c49a00", "#7a5c00"),
    ("D", 1010,  ["PostgreSQL"],                  "#eef2ff", "#2457a5", "#1a337a"),
]

px_map = {pid: cx for pid, cx, *_ in participants}

LIFE_TOP = PART_TOP + PART_H
LIFE_BOT = H - 24

for pid, cx, lines, fill, stroke, tc in participants:
    ET.SubElement(svg, "rect",
                  x=str(cx - PART_W // 2), y=str(PART_TOP),
                  width=str(PART_W), height=str(PART_H),
                  rx="6", fill=fill, stroke=stroke,
                  **{"stroke-width": "2"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 18
        lbl(svg, cx, PART_TOP + PART_H / 2 + dy + 1, ln,
            size=14, bold=True, color=tc)
    # lifeline
    ET.SubElement(svg, "line",
                  x1=str(cx), y1=str(LIFE_TOP),
                  x2=str(cx), y2=str(LIFE_BOT),
                  stroke="#bbbbbb",
                  **{"stroke-width": "1.3", "stroke-dasharray": "6,4"})

# ─── Messages ──────────────────────────────────────────────────────────────────
STEP_GAP   = 58
MSG_START_Y = PART_TOP + PART_H + 30

def step_y(idx):
    return MSG_START_Y + idx * STEP_GAP

messages = [
    ("U",  "M",  "Chụp hoặc chọn ảnh đơn thuốc",                   False, 1),
    ("M",  "M",  "Kiểm tra chất lượng ảnh cục bộ",                  False, 2),
    ("M",  "N",  "Gửi ảnh lên API quét đơn",                         False, 3),
    ("N",  "P",  "Chuyển tiếp ảnh đến dịch vụ AI",                   False, 4),
    ("P",  "P",  "Phát hiện vùng đơn thuốc (YOLO)",                  False, 5),
    ("P",  "P",  "Tiền xử lý ảnh (deskew, căn hướng)",               False, 6),
    ("P",  "P",  "Nhận dạng ký tự quang học (PaddleOCR + VietOCR)",  False, 7),
    ("P",  "P",  "Trích xuất tên thuốc (PhoBERT NER)",               False, 8),
    ("P",  "P",  "Tra cứu và chuẩn hóa tên thuốc",                   False, 9),
    ("P",  "N",  "Trả về kết quả nhận diện",                         True,  10),
    ("N",  "D",  "Lưu lịch sử quét và kết quả",                      False, 11),
    ("N",  "M",  "Trả về danh sách thuốc",                           True,  12),
    ("M",  "U",  "Hiển thị để rà soát và lập lịch",                  True,  13),
]

SELF_W = 48  # độ rộng self-loop

def draw_badge(svg, x, y, num):
    """Badge số thứ tự: hình tròn nền xanh đậm, chữ trắng to."""
    r = 12
    ET.SubElement(svg, "circle", cx=str(x), cy=str(y), r=str(r),
                  fill="#1a3a6e")
    lbl(svg, x, y + 1, str(num), size=11, bold=True, color="white")

def draw_message(svg, from_id, to_id, label, is_return, step_num):
    y  = step_y(step_num - 1)
    x1 = px_map[from_id]
    x2 = px_map[to_id]

    # activation box tại người gửi (chỉ cho arrow ngang không phải return)
    if not is_return and from_id != to_id:
        box_h = STEP_GAP - 6
        ET.SubElement(svg, "rect",
                      x=str(x1 - 6), y=str(y - 4),
                      width="12", height=str(box_h),
                      fill="#cde5ff", stroke="#3a7ec9",
                      **{"stroke-width": "1"})

    if from_id == to_id:
        # self-loop
        lx = x1 + SELF_W
        top = y - 8
        bot = y + 24
        ET.SubElement(svg, "path",
                      d=f"M {x1} {top} L {lx} {top} L {lx} {bot} L {x1} {bot}",
                      fill="none", stroke="#37474f",
                      **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
        # nhãn ngay bên phải loop
        lbl(svg, lx + 8, top + 16, label,
            size=12, color="#1a1a2e", anchor="start")
        draw_badge(svg, x1 - 20, top + 8, step_num)
    else:
        # đường ngang
        dash = "8,5" if is_return else "none"
        marker = "url(#arr-open)" if is_return else "url(#arr)"
        ET.SubElement(svg, "line",
                      x1=str(x1), y1=str(y),
                      x2=str(x2), y2=str(y),
                      stroke="#37474f",
                      **{"stroke-width": "1.5",
                         "stroke-dasharray": dash,
                         "marker-end": marker})
        mid_x = (x1 + x2) / 2
        lbl(svg, mid_x, y - 9, label, size=13, color="#1a1a2e")
        badge_x = x1 + (16 if x2 > x1 else -16)
        draw_badge(svg, badge_x, y, step_num)

# Activation bars dài cho N (bước 3–12) và P (bước 4–10)
def activation_bar(svg, pid, s_from, s_to):
    cx = px_map[pid]
    y1 = step_y(s_from - 1) - 4
    y2 = step_y(s_to - 1) + 4
    ET.SubElement(svg, "rect",
                  x=str(cx - 6), y=str(y1),
                  width="12", height=str(y2 - y1),
                  fill="#cde5ff", stroke="#3a7ec9",
                  **{"stroke-width": "1", "opacity": "0.7"})

activation_bar(svg, "N", 3, 12)
activation_bar(svg, "P", 4, 10)

for from_id, to_id, label, is_return, step_num in messages:
    draw_message(svg, from_id, to_id, label, is_return, step_num)

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

os.makedirs(f"{DIAG}/svg", exist_ok=True)
out1 = f"{DIAG}/svg/sequence_scan.svg"
out2 = f"{ASSETS}/sequence_scan.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
print(f"SVG: {out2}")

import cairosvg
for sv, pn in [
    (out1, f"{DIAG}/png/sequence_scan.png"),
    (out2, f"{ASSETS}/sequence_scan.png"),
]:
    cairosvg.svg2png(url=sv, write_to=pn, scale=2.5)
    print(f"PNG: {pn}")
