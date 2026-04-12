#!/usr/bin/env python3
"""
Tạo UML Use Case diagram chuẩn học thuật bằng SVG thuần.
Bố cục: actor bên trái, system boundary, các use case theo cột dọc.
Đường nối không xuyên qua oval, include/extend không chồng chéo.
Tối ưu cho in A4 (landscape hoặc portrait crop).
"""

import xml.etree.ElementTree as ET
import os
import math

# ─── Kích thước canvas ────────────────────────────────────────────────────────
W = 860
H = 580

# ─── Helpers ──────────────────────────────────────────────────────────────────

def mk(parent, tag, **attrs):
    clean = {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    return ET.SubElement(parent, tag, **clean)

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    # mũi tên đặc
    m = ET.SubElement(defs, "marker", id="arr",
                      markerWidth="9", markerHeight="7",
                      refX="8", refY="3.5", orient="auto")
    ET.SubElement(m, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")
    # mũi tên nét đứt
    m2 = ET.SubElement(defs, "marker", id="arr-dash",
                       markerWidth="9", markerHeight="7",
                       refX="8", refY="3.5", orient="auto")
    ET.SubElement(m2, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")
    return defs

# ─── Actor (hình người que UML) ───────────────────────────────────────────────

def draw_actor(svg, cx, top_y, label_lines):
    """Vẽ người dùng UML chuẩn: đầu tròn + thân que."""
    r = 18
    hy = top_y + r          # tâm đầu
    body_top = hy + r
    body_bot = body_top + 44
    arm_y = body_top + 14
    leg_spread = 22
    leg_h = 30

    # đầu
    mk(svg, "circle", cx=cx, cy=hy, r=r,
       fill="white", stroke="#333333", stroke_width="1.8")
    # thân
    mk(svg, "line", x1=cx, y1=body_top, x2=cx, y2=body_bot,
       stroke="#333333", stroke_width="1.8")
    # tay
    mk(svg, "line", x1=cx-28, y1=arm_y, x2=cx+28, y2=arm_y,
       stroke="#333333", stroke_width="1.8")
    # chân trái
    mk(svg, "line", x1=cx, y1=body_bot, x2=cx-leg_spread, y2=body_bot+leg_h,
       stroke="#333333", stroke_width="1.8")
    # chân phải
    mk(svg, "line", x1=cx, y1=body_bot, x2=cx+leg_spread, y2=body_bot+leg_h,
       stroke="#333333", stroke_width="1.8")

    # nhãn
    label_y0 = body_bot + leg_h + 18
    t = mk(svg, "text", x=cx, y=label_y0,
           text_anchor="middle", font_size="14",
           font_family="Arial, sans-serif",
           font_weight="bold", fill="#222222")
    for i, ln in enumerate(label_lines):
        ts = ET.SubElement(t, "tspan", x=str(cx),
                           dy="0" if i == 0 else "17")
        ts.text = ln

    # trả về: y giữa thân (để nối arrow), x tay phải
    return arm_y, cx + 28, body_bot + leg_h + 22

# ─── Use Case Oval ────────────────────────────────────────────────────────────

def draw_usecase(svg, cx, cy, label_lines, rx=105, ry=28):
    """Vẽ oval use case UML với text căn giữa nhiều dòng."""
    mk(svg, "ellipse", cx=cx, cy=cy, rx=rx, ry=ry,
       fill="#eef3fb", stroke="#2457a5", stroke_width="2.0")
    n = len(label_lines)
    t = mk(svg, "text", x=cx, y=cy,
           text_anchor="middle", dominant_baseline="central",
           font_size="13", font_family="Arial, sans-serif", fill="#0d1f40")
    for i, ln in enumerate(label_lines):
        if n == 1:
            ts = ET.SubElement(t, "tspan", x=str(cx), dy="0")
        elif n == 2:
            dy = "0" if i == 0 else "16"
            ts = ET.SubElement(t, "tspan", x=str(cx), dy=dy)
            if i == 0:
                ts.set("dy", "-8")
        else:
            dy_val = str(round((i - (n - 1) / 2) * 15))
            ts = ET.SubElement(t, "tspan", x=str(cx),
                               dy=(dy_val if i == 0 else "15"))
            if i == 0:
                ts.set("dy", dy_val)
        ts.text = ln

# ─── Mũi tên ──────────────────────────────────────────────────────────────────

def solid_arrow(svg, x1, y1, x2, y2):
    mk(svg, "path", d=f"M {x1} {y1} L {x2} {y2}",
       fill="none", stroke="#37474f", stroke_width="1.4",
       marker_end="url(#arr)")

def dashed_arrow(svg, x1, y1, x2, y2, label=""):
    mk(svg, "path", d=f"M {x1} {y1} L {x2} {y2}",
       fill="none", stroke="#37474f", stroke_width="1.3",
       stroke_dasharray="7,4", marker_end="url(#arr-dash)")
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        # offset sang phải nếu đường thẳng đứng
        dx_off = 30 if abs(x2 - x1) < 5 else 0
        dy_off = -10 if abs(x2 - x1) >= 5 else 0
        lbl = mk(svg, "text", x=mx + dx_off, y=my + dy_off,
                 text_anchor="middle", font_size="11",
                 font_family="Arial, sans-serif",
                 fill="#555555", font_style="italic")
        lbl.text = label

# ─── Điểm cắt oval ────────────────────────────────────────────────────────────

def edge_of_ellipse(cx, cy, rx, ry, toward_x, toward_y):
    """Trả về điểm trên biên oval gần nhất theo hướng (toward_x, toward_y)."""
    dx = toward_x - cx
    dy = toward_y - cy
    if dx == 0 and dy == 0:
        return cx, cy - ry
    angle = math.atan2(dy * rx, dx * ry)
    ex = cx + rx * math.cos(angle)
    ey = cy + ry * math.sin(angle)
    return ex, ey

# ─── Build SVG ────────────────────────────────────────────────────────────────

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = """
  text { font-family: Arial, sans-serif; }
  .boundary-title { font-size: 13px; font-weight: bold; fill: #1a3a6e; }
"""

# nền trắng
mk(svg, "rect", x=0, y=0, width=W, height=H, fill="white")

# ── System boundary ──────────────────────────────────────────────────────────
BX, BY = 165, 28
BW, BH = 670, 522

mk(svg, "rect", x=BX, y=BY, width=BW, height=BH,
   rx=6, ry=6,
   fill="#f8fafd", stroke="#7a9abf", stroke_width="1.8")

# tiêu đề boundary — mô tả đúng đề tài
title_t = mk(svg, "text", x=BX + BW / 2, y=BY + 20,
             **{"class": "boundary-title", "text-anchor": "middle"})
title_t.text = "Hệ thống Hỗ trợ Quản lý Thuốc"

# ── Use cases (cx, cy, label, rx, ry) ────────────────────────────────────────
UC_RX = 108
UC_RY = 30

# 2 cột: cột trái (chính), cột phải (phụ)
uc_data = [
    # (id, cx, cy, label_lines)
    ("uc1", 390, 100,  ["Đăng nhập / Đăng ký"]),
    ("uc2", 390, 192,  ["Quét đơn thuốc"]),
    ("uc3", 390, 290,  ["Rà soát danh sách thuốc"]),
    ("uc4", 390, 388,  ["Lập lịch dùng thuốc"]),
    ("uc5", 390, 486,  ["Xem lịch hôm nay"]),
    ("uc6", 660, 388,  ["Ghi nhận đã uống", "/ bỏ qua"]),
    ("uc7", 660, 486,  ["Xem lịch sử quét"]),
]

uc_map = {uid: (cx, cy) for uid, cx, cy, _ in uc_data}

for uid, cx, cy, lbls in uc_data:
    draw_usecase(svg, cx, cy, lbls, rx=UC_RX, ry=UC_RY)

# ── Actor ────────────────────────────────────────────────────────────────────
ACTOR_CX = 80
ACTOR_TOP = 155

arm_y, actor_right_x, actor_bottom = draw_actor(svg, ACTOR_CX, ACTOR_TOP, ["Người dùng"])

# ── Nối actor → use cases ─────────────────────────────────────────────────────
# Actor nối tới cạnh trái của từng oval.
# Dùng điểm xuất phát cố định: (actor_right_x, arm_y) cho tất cả.
# Dùng edge_of_ellipse cho điểm đích trên oval.

for uid, cx, cy, _ in uc_data:
    ex, ey = edge_of_ellipse(cx, cy, UC_RX, UC_RY, actor_right_x, arm_y)
    solid_arrow(svg, actor_right_x, arm_y, ex, ey)

# ── Include / Extend ──────────────────────────────────────────────────────────
# Tất cả các include đi theo trục dọc bên PHẢI của cột trái (x + 20)
# để không đi qua oval.

include_pairs = [
    ("uc2", "uc3", "«include»"),
    ("uc3", "uc4", "«include»"),
    ("uc4", "uc5", "«include»"),
]

for src_id, dst_id, lbl in include_pairs:
    sx, sy = uc_map[src_id]
    dx, dy = uc_map[dst_id]
    # từ điểm dưới oval src đến điểm trên oval dst
    x1, y1 = edge_of_ellipse(sx, sy, UC_RX, UC_RY, sx, sy + 100)
    x2, y2 = edge_of_ellipse(dx, dy, UC_RX, UC_RY, dx, dy - 100)
    # lệch sang phải để tránh chồng lên đường actor
    off = 22
    dashed_arrow(svg,
                 x1 + off, y1,
                 x2 + off, y2,
                 lbl)

# uc5 --extend--> uc6
sx5, sy5 = uc_map["uc5"]
dx6, dy6 = uc_map["uc6"]
ex5, ey5 = edge_of_ellipse(sx5, sy5, UC_RX, UC_RY, dx6, dy6)
ex6, ey6 = edge_of_ellipse(dx6, dy6, UC_RX, UC_RY, sx5, sy5)
dashed_arrow(svg, ex5, ey5, ex6, ey6, "«extend»")

# ── Output ────────────────────────────────────────────────────────────────────
DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

os.makedirs(f"{DIAG}/svg", exist_ok=True)

out1 = f"{DIAG}/svg/use_case.svg"
out2 = f"{ASSETS}/use_case.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
print(f"SVG: {out2}")

# PNG via cairosvg
import cairosvg
png_scale = 2.5   # ~2150px wide → in A4 landscape rất sắc
for svg_path, png_path in [
    (out1, f"{DIAG}/png/use_case.png"),
    (out2, f"{ASSETS}/use_case.png"),
]:
    cairosvg.svg2png(url=svg_path, write_to=png_path, scale=png_scale)
    print(f"PNG: {png_path}")
