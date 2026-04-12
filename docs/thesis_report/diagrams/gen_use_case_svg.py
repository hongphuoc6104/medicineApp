#!/usr/bin/env python3
"""
Hình 3.1 — Sơ đồ trường hợp sử dụng (UML Use Case).
Tiêu chí:
  - Actor hình người que chuẩn UML, bên trái.
  - System boundary có tiêu đề tiếng Việt phù hợp đề tài.
  - Oval use case không bị mũi tên đâm xuyên.
  - Include/Extend đi theo trục riêng, không chồng chéo.
  - Cỡ chữ đủ đọc khi in A4.
  - Không emoji, toàn tiếng Việt có dấu.
"""

import xml.etree.ElementTree as ET
import os
import math

# ─── Canvas ───────────────────────────────────────────────────────────────────
W = 900
H = 620

# ─── Helpers ──────────────────────────────────────────────────────────────────

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def mk(parent, tag, **attrs):
    clean = {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    return ET.SubElement(parent, tag, **clean)

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    # mũi tên đặc (actor → use case)
    m1 = ET.SubElement(defs, "marker", id="arr",
                       markerWidth="8", markerHeight="7",
                       refX="7", refY="3.5", orient="auto")
    ET.SubElement(m1, "polygon", points="0 0, 8 3.5, 0 7",
                  fill="#37474f")
    # mũi tên nét đứt (include / extend)
    m2 = ET.SubElement(defs, "marker", id="arr-dash",
                       markerWidth="8", markerHeight="7",
                       refX="7", refY="3.5", orient="auto")
    ET.SubElement(m2, "polygon", points="0 0, 8 3.5, 0 7",
                  fill="#37474f")
    return defs

# ─── Điểm cắt biên oval ───────────────────────────────────────────────────────

def ellipse_edge(cx, cy, rx, ry, toward_x, toward_y):
    """Tìm điểm trên viền oval theo hướng tới (toward_x, toward_y)."""
    dx = toward_x - cx
    dy = toward_y - cy
    if dx == 0 and dy == 0:
        return cx, cy - ry
    angle = math.atan2(dy * rx, dx * ry)
    return cx + rx * math.cos(angle), cy + ry * math.sin(angle)

# ─── Actor ────────────────────────────────────────────────────────────────────

def draw_actor(svg, cx, top_y, label):
    """Người dùng dạng que chuẩn UML."""
    R  = 16          # bán kính đầu
    hy = top_y + R   # tâm đầu
    bt = hy + R      # đỉnh thân
    bb = bt + 42     # đáy thân
    ay = bt + 14     # ngang tay
    ls = 20          # độ mở chân

    props = dict(stroke="#222222", stroke_width="1.8")
    mk(svg, "circle", cx=cx, cy=hy, r=R,
       fill="white", **props)
    mk(svg, "line", x1=cx, y1=bt, x2=cx, y2=bb, **props)
    mk(svg, "line", x1=cx - 26, y1=ay, x2=cx + 26, y2=ay, **props)
    mk(svg, "line", x1=cx, y1=bb, x2=cx - ls, y2=bb + 28, **props)
    mk(svg, "line", x1=cx, y1=bb, x2=cx + ls, y2=bb + 28, **props)

    foot_y = bb + 28
    lbl_y  = foot_y + 20
    t = mk(svg, "text", x=cx, y=lbl_y,
           text_anchor="middle", font_size="14",
           font_family="Arial, sans-serif",
           font_weight="bold", fill="#222222")
    t.text = label

    return ay, cx + 26, lbl_y + 6   # (arm_y, right_x, bottom_y)

# ─── Use Case oval ────────────────────────────────────────────────────────────

UC_RX = 112
UC_RY = 30

def draw_usecase(svg, cx, cy, lines, rx=UC_RX, ry=UC_RY):
    mk(svg, "ellipse", cx=cx, cy=cy, rx=rx, ry=ry,
       fill="#eef3fb", stroke="#2457a5", stroke_width="2.0")
    n = len(lines)
    t = mk(svg, "text", x=cx, y=cy,
           text_anchor="middle", dominant_baseline="central",
           font_size="13", font_family="Arial, sans-serif",
           fill="#0d1f40")
    for i, ln in enumerate(lines):
        if n == 1:
            ts = ET.SubElement(t, "tspan", x=str(cx), dy="0")
        elif n == 2:
            dy = "-9" if i == 0 else "18"
            ts = ET.SubElement(t, "tspan", x=str(cx), dy=dy)
        elif n == 3:
            offsets = ["-17", "17", "17"]
            ts = ET.SubElement(t, "tspan", x=str(cx), dy=offsets[i])
        else:
            dy_val = str(round((i - (n - 1) / 2) * 15))
            ts = ET.SubElement(t, "tspan", x=str(cx),
                               dy=(dy_val if i == 0 else "15"))
        ts.text = ln

# ─── Mũi tên ─────────────────────────────────────────────────────────────────

def solid_arrow(svg, x1, y1, x2, y2):
    mk(svg, "path", d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}",
       fill="none", stroke="#37474f", stroke_width="1.4",
       marker_end="url(#arr)")

def dashed_arrow(svg, x1, y1, x2, y2, label=""):
    mk(svg, "path", d=f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}",
       fill="none", stroke="#37474f", stroke_width="1.3",
       stroke_dasharray="7,4",
       marker_end="url(#arr-dash)")
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        # offset nhãn: nếu đường thẳng đứng → sang phải; nếu nằm ngang → lên trên
        if abs(x2 - x1) < 8:      # gần thẳng đứng
            lx, ly = mx + 38, my
        else:                      # nằm ngang
            lx, ly = mx, my - 10
        t = mk(svg, "text", x=lx, y=ly,
               text_anchor="middle", font_size="11",
               font_family="Arial, sans-serif",
               fill="#444444", font_style="italic")
        t.text = label

# ─── Build diagram ────────────────────────────────────────────────────────────

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = """
  text { font-family: Arial, sans-serif; }
  .bnd-title { font-size: 14px; font-weight: bold; fill: #1a3a6e; }
"""

# nền trắng
mk(svg, "rect", x=0, y=0, width=W, height=H, fill="white")

# ── System boundary ───────────────────────────────────────────────────────────
BX, BY = 170, 24
BW, BH = 710, 574

mk(svg, "rect", x=BX, y=BY, width=BW, height=BH,
   rx=6, ry=6,
   fill="#f8fafd", stroke="#7a9abf", stroke_width="1.8")

title_t = mk(svg, "text", x=BX + BW / 2, y=BY + 22,
             **{"class": "bnd-title", "text-anchor": "middle"})
title_t.text = "Hệ thống Hỗ trợ Quản lý Đơn Thuốc"

# ── Bố cục use cases ─────────────────────────────────────────────────────────
#  Cột trái (chuỗi chính): uc1 → uc2 → uc3 → uc4 → uc5
#  Cột phải (phụ trợ):                          uc6, uc7
#
#  Khoảng cách dọc: 92px giữa các oval cùng cột
#  Include đi theo trục dọc phụ (x offset = +30) tránh overlap actor arrows
#  Extend đi theo trục ngang

COL_L = 420     # x trung tâm cột trái
COL_R = 710     # x trung tâm cột phải

uc_data = [
    # (id, cx, cy, label_lines)
    ("uc1", COL_L, 100,  ["Đăng nhập / Đăng ký"]),
    ("uc2", COL_L, 200,  ["Quét đơn thuốc"]),
    ("uc3", COL_L, 300,  ["Rà soát danh sách thuốc"]),
    ("uc4", COL_L, 400,  ["Lập lịch dùng thuốc"]),
    ("uc5", COL_L, 500,  ["Xem lịch hôm nay"]),
    ("uc6", COL_R, 395,  ["Ghi nhận trạng thái", "uống thuốc"]),
    ("uc7", COL_R, 505,  ["Xem lịch sử quét"]),
]

uc_map = {uid: (cx, cy) for uid, cx, cy, _ in uc_data}

for uid, cx, cy, lbls in uc_data:
    draw_usecase(svg, cx, cy, lbls)

# ── Actor ─────────────────────────────────────────────────────────────────────
ACTOR_CX  = 82
ACTOR_TOP = 160

arm_y, actor_right, actor_bottom = draw_actor(svg, ACTOR_CX, ACTOR_TOP, "Người dùng")
actor_top_y = ACTOR_TOP + 32   # khoảng y phần thân actor

# ── Nối actor → use cases ─────────────────────────────────────────────────────
# Phân bổ điểm xuất phát theo y của use case (giữa đầu và chân actor)
uc_ys = [cy for _, _, cy, _ in uc_data]
y_min_uc, y_max_uc = min(uc_ys), max(uc_ys)
actor_y_range = actor_bottom - actor_top_y

for uid, cx, cy, _ in uc_data:
    # Nội suy điểm xuất phát y theo vị trí use case tương đối
    t = (cy - y_min_uc) / max(y_max_uc - y_min_uc, 1)
    src_y = actor_top_y + t * actor_y_range * 0.75
    ex, ey = ellipse_edge(cx, cy, UC_RX, UC_RY, actor_right, src_y)
    solid_arrow(svg, actor_right, src_y, ex, ey)

# ── Include (chuỗi dọc) ───────────────────────────────────────────────────────
# Đường đi: từ đáy oval src → đỉnh oval dst, lệch sang phải 28px
INCL_OFF = 28   # offset ngang để tránh arrow actor

include_pairs = [
    ("uc2", "uc3", "«include»"),
    ("uc3", "uc4", "«include»"),
    ("uc4", "uc5", "«include»"),
]

for src_id, dst_id, lbl_text in include_pairs:
    sx, sy = uc_map[src_id]
    dx, dy = uc_map[dst_id]
    # điểm xuất = cạnh dưới oval src (lệch phải)
    x1, y1 = ellipse_edge(sx, sy, UC_RX, UC_RY, sx + INCL_OFF, sy + 100)
    # điểm đích = cạnh trên oval dst (lệch phải)
    x2, y2 = ellipse_edge(dx, dy, UC_RX, UC_RY, dx + INCL_OFF, dy - 100)
    dashed_arrow(svg, x1 + INCL_OFF, y1, x2 + INCL_OFF, y2, lbl_text)

# ── Extend: uc5 → uc6 (ngang) ────────────────────────────────────────────────
# Đường đi ngang, từ cạnh phải oval uc5 → cạnh trái oval uc6
sx5, sy5 = uc_map["uc5"]
dx6, dy6 = uc_map["uc6"]
ex5, ey5 = ellipse_edge(sx5, sy5, UC_RX, UC_RY, dx6, dy6)
ex6, ey6 = ellipse_edge(dx6, dy6, UC_RX, UC_RY, sx5, sy5)
dashed_arrow(svg, ex5, ey5, ex6, ey6, "«extend»")

# ── Actor → uc7 (extend dưới): thêm nối trực tiếp actor → uc7 ───────────────
# (uc7 đã nối trong vòng lặp bên trên rồi — không cần thêm)

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

os.makedirs(f"{DIAG}/svg", exist_ok=True)
out1 = f"{DIAG}/svg/use_case.svg"
out2 = f"{ASSETS}/use_case.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
print(f"SVG: {out2}")

import cairosvg
for sv, pn in [
    (out1, f"{DIAG}/png/use_case.png"),
    (out2, f"{ASSETS}/use_case.png"),
]:
    cairosvg.svg2png(url=sv, write_to=pn, scale=2.5)
    print(f"PNG: {pn}")
