#!/usr/bin/env python3
"""
Tạo Sequence diagram SVG thuần tay — cỡ chữ lớn, dễ đọc khi in A4.
Số thứ tự nổi bật (nền đậm, chữ trắng).
Participant box rõ ràng.
"""

import xml.etree.ElementTree as ET
import os

# ─── Canvas ───────────────────────────────────────────────────────────────────
W = 1050
H = 840

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
                  **{"stroke-width": "1.5"})
    return defs

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = """
  text { font-family: Arial, sans-serif; }
  .seq-num { font-size: 11px; font-weight: bold; fill: white; }
  .msg     { font-size: 12px; fill: #1a1a2e; }
  .self    { font-size: 11px; fill: #1a1a2e; }
"""

ET.SubElement(svg, "rect", x="0", y="0",
              width=str(W), height=str(H), fill="white")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def lbl(svg, x, y, txt, size=12, bold=False, color="#111",
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
#  (id, x_center, label_lines, fill, stroke, text_color)
PART_TOP  = 20
PART_H    = 52
PART_W    = 140

participants = [
    ("U",   80,  ["Người dùng"],                    "#fff7e8", "#b7791f", "#7a4512"),
    ("M",  270,  ["Ứng dụng", "di động"],            "#e8f3fd", "#3a7ec9", "#1a4a80"),
    ("N",  480,  ["Máy chủ", "Node.js"],             "#edfaf3", "#2d7a46", "#1a5c32"),
    ("P",  700,  ["Dịch vụ AI", "(FastAPI)"],        "#fffbec", "#c49a00", "#7a5c00"),
    ("D",  960,  ["PostgreSQL"],                     "#eef2ff", "#2457a5", "#1a337a"),
]

px_map = {pid: cx for pid, cx, *_ in participants}

# vẽ participant boxes + lifelines
LIFE_TOP  = PART_TOP + PART_H
LIFE_BOT  = H - 30

for pid, cx, lines, fill, stroke, tc in participants:
    # hộp
    ET.SubElement(svg, "rect",
                  x=str(cx - PART_W // 2), y=str(PART_TOP),
                  width=str(PART_W), height=str(PART_H),
                  rx="6", fill=fill, stroke=stroke,
                  **{"stroke-width": "2"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 17
        lbl(svg, cx, PART_TOP + PART_H / 2 + dy, ln,
            size=13, bold=True, color=tc)
    # đường lifeline
    ET.SubElement(svg, "line",
                  x1=str(cx), y1=str(LIFE_TOP),
                  x2=str(cx), y2=str(LIFE_BOT),
                  stroke="#aaaaaa", **{"stroke-width": "1.2",
                                       "stroke-dasharray": "6,4"})

# ─── Messages ──────────────────────────────────────────────────────────────────
# (from, to, label, is_return, step_num, note)
# is_return=True → nét đứt + open arrowhead
# step_num=0 → self-call (không vẽ mũi tên ngang)

STEP_GAP = 52     # px giữa các bước
MSG_START_Y = PART_TOP + PART_H + 28

def step_y(idx):
    return MSG_START_Y + idx * STEP_GAP

messages = [
    # (from_id, to_id, label, is_return, step_num)
    ("U", "M",  "Chụp hoặc chọn ảnh đơn thuốc",               False, 1),
    ("M", "M",  "Kiểm tra chất lượng ảnh cục bộ",             False, 2),
    ("M", "N",  "Gửi ảnh lên API quét đơn",                    False, 3),
    ("N", "P",  "Chuyển tiếp ảnh đến dịch vụ AI",              False, 4),
    ("P", "P",  "Phát hiện vùng đơn thuốc (YOLO)",             False, 5),
    ("P", "P",  "Tiền xử lý ảnh (deskew, căn hướng)",          False, 6),
    ("P", "P",  "Nhận dạng ký tự quang học (PaddleOCR + VietOCR)", False, 7),
    ("P", "P",  "Trích xuất tên thuốc (PhoBERT NER)",           False, 8),
    ("P", "P",  "Tra cứu và chuẩn hóa tên thuốc",               False, 9),
    ("P", "N",  "Trả về kết quả nhận diện",                    True, 10),
    ("N", "D",  "Lưu lịch sử quét và kết quả",                 False, 11),
    ("N", "M",  "Trả về danh sách thuốc",                      True, 12),
    ("M", "U",  "Hiển thị để rà soát và lập lịch",             True, 13),
]

SELF_W = 44   # chiều rộng self-loop

def draw_number_badge(svg, x, y, num):
    """Vẽ badge số thứ tự: hình tròn nền xanh đậm, chữ trắng."""
    r = 11
    ET.SubElement(svg, "circle", cx=str(x), cy=str(y), r=str(r),
                  fill="#1a3a6e")
    lbl(svg, x, y, str(num), size=10, bold=True, color="white")

def draw_message(svg, from_id, to_id, label, is_return, step_num):
    y = step_y(step_num - 1)
    x1 = px_map[from_id]
    x2 = px_map[to_id]

    # activation box tại participan gửi
    box_h = STEP_GAP - 4
    if not is_return and from_id != to_id:
        ET.SubElement(svg, "rect",
                      x=str(x1 - 5), y=str(y - 4),
                      width="10", height=str(box_h),
                      fill="#cde5ff", stroke="#3a7ec9",
                      **{"stroke-width": "1"})

    if from_id == to_id:
        # self-loop: 3 đoạn
        loop_x = x1 + SELF_W
        loop_y_top = y - 6
        loop_y_bot = y + 22
        ET.SubElement(svg, "path",
                      d=f"M {x1} {loop_y_top} L {loop_x} {loop_y_top} "
                        f"L {loop_x} {loop_y_bot} L {x1} {loop_y_bot}",
                      fill="none", stroke="#37474f",
                      **{"stroke-width": "1.4",
                         "marker-end": "url(#arr)"})
        # nhãn bên phải — giới hạn chiều rộng bằng wrap thủ công
        max_label = label if len(label) <= 50 else label[:48] + "…"
        lbl(svg, loop_x + 6, loop_y_top + 14, max_label,
            size=11, color="#1a1a2e", anchor="start")
        # badge số
        draw_number_badge(svg, x1 - 18, loop_y_top + 8, step_num)
    else:
        # đường ngang
        stroke_dash = "8,5" if is_return else "none"
        marker = "url(#arr-open)" if is_return else "url(#arr)"
        ET.SubElement(svg, "line",
                      x1=str(x1), y1=str(y),
                      x2=str(x2), y2=str(y),
                      stroke="#37474f",
                      **{"stroke-width": "1.5",
                         "stroke-dasharray": stroke_dash,
                         "marker-end": marker})
        # nhãn trên đường
        mid_x = (x1 + x2) / 2
        lbl(svg, mid_x, y - 8, label, size=12, color="#1a1a2e")
        # badge số tại điểm xuất phát
        badge_x = x1 + (14 if x2 > x1 else -14)
        draw_number_badge(svg, badge_x, y, step_num)

# activation bars cho N và P
# Tính range activation: N activate từ step 3 → step 12, P từ step 4 → step 10
def activation_bar(svg, pid, step_from, step_to):
    cx = px_map[pid]
    y1 = step_y(step_from - 1) - 4
    y2 = step_y(step_to - 1) + 4
    ET.SubElement(svg, "rect",
                  x=str(cx - 5), y=str(y1),
                  width="10", height=str(y2 - y1),
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

import cairosvg
for sp, pp in [
    (out1, f"{DIAG}/png/sequence_scan.png"),
    (out2, f"{ASSETS}/sequence_scan.png"),
]:
    cairosvg.svg2png(url=sp, write_to=pp, scale=2.5)
    print(f"PNG: {pp}")
