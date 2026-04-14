#!/usr/bin/env python3
"""
Hình 3.6 — Sơ đồ hoạt động tạo kế hoạch dùng thuốc (Activity Diagram).
Cải tiến:
  - Bố cục 2 hàng (landscape):
      Hàng 1: Bắt đầu → Quét đơn → [Cần chỉnh sửa?] → Chọn ngày → Chọn giờ → Nhập số viên
      Hàng 2:                       Chỉnh sửa   ───────→ Lưu kế hoạch → Thiết lập thông báo → Kết thúc
  - Canvas 960×440, box width 134px, font 13px.
  - Mũi tên và routing sạch, không chồng nhau.
  - Không emoji. Toàn tiếng Việt có dấu.
"""

import xml.etree.ElementTree as ET
import os

W = 960
H = 450


def svg_root(w, h):
    return ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width=str(w),
        height=str(h),
        viewBox=f"0 0 {w} {h}",
    )


def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    m = ET.SubElement(
        defs,
        "marker",
        id="arr",
        markerWidth="9",
        markerHeight="7",
        refX="8",
        refY="3.5",
        orient="auto",
    )
    ET.SubElement(m, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")
    return defs


svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = "text { font-family: Arial, sans-serif; }"

ET.SubElement(svg, "rect", x="0", y="0", width=str(W), height=str(H), fill="white")

# ─── Helpers ──────────────────────────────────────────────────────────────────


def lbl(
    svg, x, y, txt, size=13, bold=False, color="#111", anchor="middle", italic=False
):
    attrs = {
        "x": str(x),
        "y": str(y),
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


def step_box(svg, cx, cy, w, h, lines, fill="#edf7f0", stroke="#2d7a46", size=13, rx=7):
    ET.SubElement(
        svg,
        "rect",
        x=str(cx - w / 2),
        y=str(cy - h / 2),
        width=str(w),
        height=str(h),
        rx=str(rx),
        fill=fill,
        stroke=stroke,
        **{"stroke-width": "1.6"},
    )
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 17
        lbl(svg, cx, cy + dy, ln, size=size)


def diamond(svg, cx, cy, w, h, lines, fill="#fff8e1", stroke="#b7791f", size=13):
    hw, hh = w / 2, h / 2
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    ET.SubElement(
        svg, "polygon", points=pts, fill=fill, stroke=stroke, **{"stroke-width": "1.6"}
    )
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        lbl(svg, cx, cy + dy, ln, size=size)


def terminal(svg, cx, cy, w, h, txt, fill="#1a3a6e", size=14):
    ET.SubElement(
        svg,
        "rect",
        x=str(cx - w / 2),
        y=str(cy - h / 2),
        width=str(w),
        height=str(h),
        rx=str(h / 2),
        fill=fill,
        stroke=fill,
        **{"stroke-width": "1.5"},
    )
    lbl(svg, cx, cy + 1, txt, size=size, bold=True, color="white")


def arrow(svg, x1, y1, x2, y2, label="", lx=None, ly=None, size=12):
    ET.SubElement(
        svg,
        "path",
        d=f"M {x1} {y1} L {x2} {y2}",
        fill="none",
        stroke="#37474f",
        **{"stroke-width": "1.6", "marker-end": "url(#arr)"},
    )
    if label:
        _lx = lx if lx is not None else (x1 + x2) / 2
        _ly = ly if ly is not None else (y1 + y2) / 2 - 11
        lbl(svg, _lx, _ly, label, size=size, italic=True, color="#555")


def path_arrow(svg, d, label="", lx=None, ly=None, size=12):
    ET.SubElement(
        svg,
        "path",
        d=d,
        fill="none",
        stroke="#37474f",
        **{"stroke-width": "1.6", "marker-end": "url(#arr)"},
    )
    if label and lx is not None:
        lbl(svg, lx, ly, label, size=size, italic=True, color="#555")


# ─── Bố cục ──────────────────────────────────────────────────────────────────
ROW1_Y = 120
ROW2_Y = 320

BW = 134  # box width
BH = 68  # box height
DW = 118  # diamond width
DH = 76  # diamond height
TW = 92  # terminator width
TH = 40  # terminator height

# X positions — hàng 1
x_START = 52
x_A = 196  # Quét đơn thuốc
x_B = 334  # Diamond: Cần chỉnh sửa?
x_D = 490  # Chọn ngày
x_E = 638  # Chọn giờ
x_F = 800  # Nhập số viên

# X positions — hàng 2
x_C = 334  # Chỉnh sửa danh sách (dưới B)
x_G = 490  # Lưu kế hoạch (dưới D)
x_H = 638  # Thiết lập thông báo (dưới E)
x_END = 800  # Kết thúc (dưới F)

# ── Hàng 1 ──────────────────────────────────────────────────────────────────
terminal(svg, x_START, ROW1_Y, TW, TH, "Bắt đầu")

step_box(svg, x_A, ROW1_Y, BW, BH, ["Quét đơn thuốc", "và nhận kết quả"])

diamond(svg, x_B, ROW1_Y, DW, DH, ["Cần", "chỉnh sửa?"])

step_box(svg, x_D, ROW1_Y, BW, BH, ["Chọn ngày bắt đầu", "& số ngày dùng"])

step_box(svg, x_E, ROW1_Y, BW, BH, ["Chọn khung giờ", "uống thuốc"])

step_box(svg, x_F, ROW1_Y, BW, BH, ["Nhập số viên", "mỗi khung giờ"])

# ── Hàng 2 ──────────────────────────────────────────────────────────────────
step_box(svg, x_C, ROW2_Y, BW, BH, ["Chỉnh sửa", "danh sách thuốc"])

step_box(svg, x_G, ROW2_Y, BW, BH, ["Lưu kế hoạch", "lên máy chủ"])

step_box(svg, x_H, ROW2_Y, BW, BH, ["Thiết lập thông báo", "nhắc uống thuốc"])

terminal(svg, x_END, ROW2_Y, TW, TH, "Kết thúc")

# ─── Mũi tên hàng 1 ──────────────────────────────────────────────────────────
# START → A
arrow(svg, x_START + TW // 2, ROW1_Y, x_A - BW // 2, ROW1_Y)
# A → B
arrow(svg, x_A + BW // 2, ROW1_Y, x_B - DW // 2, ROW1_Y)
# B → D (Không)
arrow(
    svg,
    x_B + DW // 2,
    ROW1_Y,
    x_D - BW // 2,
    ROW1_Y,
    "Không",
    lx=(x_B + DW // 2 + x_D - BW // 2) / 2,
    ly=ROW1_Y - 12,
)
# D → E
arrow(svg, x_D + BW // 2, ROW1_Y, x_E - BW // 2, ROW1_Y)
# E → F
arrow(svg, x_E + BW // 2, ROW1_Y, x_F - BW // 2, ROW1_Y)

# ─── F (hàng 1) → G (hàng 2): L-shape ───────────────────────────────────────
MID_Y = (ROW1_Y + ROW2_Y) // 2  # = 220
path_arrow(
    svg,
    f"M {x_F} {ROW1_Y + BH // 2} "
    f"L {x_F} {MID_Y} "
    f"L {x_G} {MID_Y} "
    f"L {x_G} {ROW2_Y - BH // 2}",
)

# ─── Hàng 2: G → H → END ────────────────────────────────────────────────────
arrow(svg, x_G + BW // 2, ROW2_Y, x_H - BW // 2, ROW2_Y)
arrow(svg, x_H + BW // 2, ROW2_Y, x_END - TW // 2, ROW2_Y)

# ─── Nhánh Có: B ↓ → C ───────────────────────────────────────────────────────
arrow(
    svg,
    x_B,
    ROW1_Y + DH // 2,
    x_C,
    ROW2_Y - BH // 2,
    "Có",
    lx=x_B + 30,
    ly=(ROW1_Y + DH // 2 + ROW2_Y - BH // 2) // 2,
)

# ─── C → G ────────────────────────────────────────────────────────────────────
arrow(svg, x_C + BW // 2, ROW2_Y, x_G - BW // 2, ROW2_Y)

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIAG = BASE_DIR
ASSETS = os.path.normpath(os.path.join(BASE_DIR, "../assets/diagrams"))

os.makedirs(f"{DIAG}/svg", exist_ok=True)
os.makedirs(ASSETS, exist_ok=True)
out1 = f"{DIAG}/svg/activity_create_plan.svg"
out2 = f"{ASSETS}/activity_create_plan.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
print(f"SVG: {out2}")

import cairosvg

for sv, pn in [
    (out1, f"{DIAG}/png/activity_create_plan.png"),
    (out2, f"{ASSETS}/activity_create_plan.png"),
]:
    cairosvg.svg2png(url=sv, write_to=pn, scale=2.5)
    print(f"PNG: {pn}")
