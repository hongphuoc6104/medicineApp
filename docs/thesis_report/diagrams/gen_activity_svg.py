#!/usr/bin/env python3
"""
Tạo Activity diagram "Tạo kế hoạch" SVG thuần tay.
Bố cục 2 hàng:
  Hàng trên (ROW1): Bắt đầu → Quét → [Cần chỉnh sửa?] → Chọn ngày → Chọn giờ → Nhập số viên
  Hàng dưới (ROW2):                   Chỉnh sửa ──────→ Lưu kế hoạch → Thiết lập thông báo → Kết thúc
  Nhánh "Không": diamond đi thẳng sang phải → Chọn ngày
  Nhánh "Có": diamond đi xuống → Chỉnh sửa → Lưu kế hoạch
  "Nhập số viên" → xuống → "Lưu kế hoạch" (L-shape)
Cỡ chữ 12-13px, đọc rõ khi in A4 landscape.
"""

import xml.etree.ElementTree as ET
import os

W = 900
H = 420

def svg_root(w, h):
    return ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                      width=str(w), height=str(h),
                      viewBox=f"0 0 {w} {h}")

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    m = ET.SubElement(defs, "marker", id="arr",
                      markerWidth="9", markerHeight="7",
                      refX="8", refY="3.5", orient="auto")
    ET.SubElement(m, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")
    return defs

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = "text { font-family: Arial, sans-serif; }"

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

def step_box(svg, cx, cy, w, h, lines, fill="#edf7f0",
             stroke="#2d7a46", size=12, rx=7):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.5"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 16
        lbl(svg, cx, cy + dy, ln, size=size)

def diamond(svg, cx, cy, w, h, lines, fill="#fff8e1",
            stroke="#b7791f", size=12):
    hw, hh = w / 2, h / 2
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    ET.SubElement(svg, "polygon", points=pts, fill=fill,
                  stroke=stroke, **{"stroke-width": "1.5"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 14
        lbl(svg, cx, cy + dy, ln, size=size)

def terminal(svg, cx, cy, w, h, txt, fill="#1a3a6e", size=13):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(h / 2),
                  fill=fill, stroke=fill, **{"stroke-width": "1.5"})
    lbl(svg, cx, cy, txt, size=size, bold=True, color="white")

def arrow(svg, x1, y1, x2, y2, label="", lx=None, ly=None):
    ET.SubElement(svg, "path",
                  d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
    if label:
        _lx = lx if lx is not None else (x1 + x2) / 2
        _ly = ly if ly is not None else (y1 + y2) / 2 - 10
        lbl(svg, _lx, _ly, label, size=11, italic=True, color="#555")

def path_arrow(svg, d, label="", lx=None, ly=None):
    ET.SubElement(svg, "path", d=d, fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
    if label and lx is not None:
        lbl(svg, lx, ly, label, size=11, italic=True, color="#555")

# ─── Bố cục ──────────────────────────────────────────────────────────────────
# ROW1 (hàng trên): y = 120
# ROW2 (hàng dưới): y = 310
#
# Các node ROW1: START  A    B(diam)   D    E    F
# x positions =   55   180    310    455  590  730
#
# Các node ROW2:              C        G    H   END
# x positions =              310      455  600  745

ROW1_Y = 115
ROW2_Y = 305

# Kích thước
BW  = 120   # box width
BH  = 62    # box height
DW  = 110   # diamond width
DH  = 70    # diamond height
TW  = 84    # terminator width
TH  = 36    # terminator height

# X
x_START = 55
x_A     = 185
x_B     = 315   # diamond
x_D     = 460
x_E     = 595
x_F     = 735

x_C     = 315   # dưới B
x_G     = 460   # dưới D
x_H     = 595   # Thiết lập thông báo
x_END   = 740   # Kết thúc

# ── Hàng 1 ───────────────────────────────────────────────────────────────────
terminal(svg, x_START, ROW1_Y, TW, TH, "Bắt đầu")

step_box(svg, x_A, ROW1_Y, BW, BH,
         ["Quét đơn thuốc", "và nhận kết quả"])

diamond(svg, x_B, ROW1_Y, DW, DH,
        ["Cần", "chỉnh sửa?"])

step_box(svg, x_D, ROW1_Y, BW, BH,
         ["Chọn ngày bắt đầu", "& số ngày dùng"])

step_box(svg, x_E, ROW1_Y, BW, BH,
         ["Chọn khung giờ", "uống thuốc"])

step_box(svg, x_F, ROW1_Y, BW, BH,
         ["Nhập số", "viên / khung giờ"])

# ── Hàng 2 ───────────────────────────────────────────────────────────────────
step_box(svg, x_C, ROW2_Y, BW, BH,
         ["Chỉnh sửa", "danh sách thuốc"])

step_box(svg, x_G, ROW2_Y, BW, BH,
         ["Lưu kế hoạch", "lên máy chủ"])

step_box(svg, x_H, ROW2_Y, BW, BH,
         ["Thiết lập thông báo", "nhắc uống thuốc"])

terminal(svg, x_END, ROW2_Y, TW, TH, "Kết thúc")

# ─── Mũi tên hàng 1 ──────────────────────────────────────────────────────────
# START → A
arrow(svg, x_START + TW // 2, ROW1_Y,
           x_A - BW // 2, ROW1_Y)

# A → B
arrow(svg, x_A + BW // 2, ROW1_Y,
           x_B - DW // 2, ROW1_Y)

# B → D (Không)
arrow(svg, x_B + DW // 2, ROW1_Y,
           x_D - BW // 2, ROW1_Y,
      "Không",
      lx=(x_B + DW // 2 + x_D - BW // 2) / 2,
      ly=ROW1_Y - 11)

# D → E
arrow(svg, x_D + BW // 2, ROW1_Y,
           x_E - BW // 2, ROW1_Y)

# E → F
arrow(svg, x_E + BW // 2, ROW1_Y,
           x_F - BW // 2, ROW1_Y)

# ─── F (hàng 1) xuống G (hàng 2): L-shape ───────────────────────────────────
# F đi xuống đến giữa, sang trái đến x_G, rồi xuống G
MID_Y = (ROW1_Y + ROW2_Y) // 2  # = 210
path_arrow(svg,
           f"M {x_F} {ROW1_Y + BH // 2} "
           f"L {x_F} {MID_Y} "
           f"L {x_G} {MID_Y} "
           f"L {x_G} {ROW2_Y - BH // 2}")

# ─── G → H → END hàng 2 ──────────────────────────────────────────────────────
arrow(svg, x_G + BW // 2, ROW2_Y,
           x_H - BW // 2, ROW2_Y)

arrow(svg, x_H + BW // 2, ROW2_Y,
           x_END - TW // 2, ROW2_Y)

# ─── Nhánh Có: B ↓ → C ───────────────────────────────────────────────────────
# Từ đáy diamond B thẳng xuống đến đỉnh C
arrow(svg, x_B, ROW1_Y + DH // 2,
           x_C, ROW2_Y - BH // 2,
      "Có",
      lx=x_B + 28,
      ly=(ROW1_Y + DH // 2 + ROW2_Y - BH // 2) // 2)

# ─── C (hàng 2) → G (hàng 2) ────────────────────────────────────────────────
arrow(svg, x_C + BW // 2, ROW2_Y,
           x_G - BW // 2, ROW2_Y)

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

os.makedirs(f"{DIAG}/svg", exist_ok=True)
out1 = f"{DIAG}/svg/activity_create_plan.svg"
out2 = f"{ASSETS}/activity_create_plan.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")

import cairosvg
for sp, pp in [
    (out1, f"{DIAG}/png/activity_create_plan.png"),
    (out2, f"{ASSETS}/activity_create_plan.png"),
]:
    cairosvg.svg2png(url=sp, write_to=pp, scale=2.5)
    print(f"PNG: {pp}")
