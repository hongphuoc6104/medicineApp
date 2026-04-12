#!/usr/bin/env python3
"""
Tạo Activity diagram "Tạo kế hoạch" SVG thuần tay.
Bố cục LR (trái → phải) compact, tránh tràn trang PDF.
"""

import xml.etree.ElementTree as ET
import os

# Canvas: ngang rộng, chiều cao vừa đủ
W = 1020
H = 260

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    m = ET.SubElement(defs, "marker", id="arr",
                      markerWidth="8", markerHeight="6",
                      refX="7", refY="3", orient="auto")
    ET.SubElement(m, "polygon", points="0 0, 8 3, 0 6", fill="#455a64")

svg = svg_root(W, H)
add_defs(svg)
ET.SubElement(svg, "rect", x="0", y="0", width=str(W), height=str(H), fill="white")
st = ET.SubElement(svg, "style")
st.text = "text { font-family: Arial, sans-serif; }"

def arrow(svg, x1, y1, x2, y2):
    ET.SubElement(svg, "path", d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#455a64",
                  **{"stroke-width": "1.4", "marker-end": "url(#arr)"})

def step_box(svg, cx, cy, w, h, lines, fill="#f0f7f4", stroke="#2d7a46", rx=6, size=11):
    ET.SubElement(svg, "rect", x=str(cx - w/2), y=str(cy - h/2),
                  width=str(w), height=str(h), rx=str(rx),
                  fill=fill, stroke=stroke, **{"stroke-width": "1.3"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n-1)/2) * 14
        t = ET.SubElement(svg, "text", x=str(cx), y=str(cy + dy),
                          **{"text-anchor": "middle", "dominant-baseline": "central",
                             "font-size": str(size), "fill": "#111"})
        t.text = ln

def diamond(svg, cx, cy, w, h, lines, fill="#fff8e1", stroke="#b7791f", size=10):
    hw, hh = w/2, h/2
    pts = f"{cx},{cy-hh} {cx+hw},{cy} {cx},{cy+hh} {cx-hw},{cy}"
    ET.SubElement(svg, "polygon", points=pts, fill=fill, stroke=stroke,
                  **{"stroke-width": "1.3"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n-1)/2) * 13
        t = ET.SubElement(svg, "text", x=str(cx), y=str(cy + dy),
                          **{"text-anchor": "middle", "dominant-baseline": "central",
                             "font-size": str(size), "fill": "#111"})
        t.text = ln

def terminator(svg, cx, cy, w, h, txt, fill="#2457a5", size=12):
    ET.SubElement(svg, "rect", x=str(cx - w/2), y=str(cy - h/2),
                  width=str(w), height=str(h), rx=str(h/2),
                  fill=fill, stroke=fill, **{"stroke-width": "1.5"})
    t = ET.SubElement(svg, "text", x=str(cx), y=str(cy),
                      **{"text-anchor": "middle", "dominant-baseline": "central",
                         "font-size": str(size), "fill": "white", "font-weight": "bold"})
    t.text = txt

def label_edge(svg, x, y, txt, size=10):
    t = ET.SubElement(svg, "text", x=str(x), y=str(y),
                      **{"text-anchor": "middle", "font-size": str(size),
                         "fill": "#555", "font-style": "italic"})
    t.text = txt

# ── Layout ────────────────────────────────────────────────────────────────────
MID_Y = H // 2   # = 130
TOP_Y = 60
BOT_Y = H - 60   # = 200

# X positions for each step
# START  A  B(diamond)  C  D  E  F  G  H  END
xs = {
    "START": 40,
    "A":     145,
    "B":     270,
    "C":     270,   # below B (branch YES)
    "D":     400,
    "E":     510,
    "F":     620,
    "G":     730,
    "H":     840,
    "END":   945,
}

BW, BH = 100, 56   # box width / height
DW, DH = 90, 56    # diamond width/height
TW, TH = 70, 34    # terminator

# Branch YES goes DOWN to C then right to D
# Main flow stays on MID_Y

# Draw nodes
terminator(svg, xs["START"], MID_Y, TW, TH, "Bắt đầu")

step_box(svg, xs["A"], MID_Y, BW, BH,
         ["Quét đơn", "thuốc &", "nhận kết quả"])

diamond(svg, xs["B"], MID_Y, DW, DH,
        ["Cần", "chỉnh", "sửa?"])

# C is below B
C_Y = BOT_Y
step_box(svg, xs["C"], C_Y, BW, BH,
         ["Chỉnh sửa", "danh sách", "thuốc"])

step_box(svg, xs["D"], MID_Y, BW, BH,
         ["Chọn ngày", "& số ngày"])

step_box(svg, xs["E"], MID_Y, BW, BH,
         ["Chọn khung", "giờ uống"])

step_box(svg, xs["F"], MID_Y, BW, BH,
         ["Nhập số", "viên/khung", "giờ"])

step_box(svg, xs["G"], MID_Y, BW, BH,
         ["Lưu kế", "hoạch"])

step_box(svg, xs["H"], MID_Y, BW, BH,
         ["Thông báo", "nhắc uống"])

terminator(svg, xs["END"], MID_Y, TW, TH, "Kết thúc")

# ── Arrows ────────────────────────────────────────────────────────────────────
# START → A
arrow(svg, xs["START"] + TW/2, MID_Y, xs["A"] - BW/2, MID_Y)

# A → B
arrow(svg, xs["A"] + BW/2, MID_Y, xs["B"] - DW/2, MID_Y)

# B → (NO) → D  (top branch, label "Không")
arrow(svg, xs["B"] + DW/2, MID_Y, xs["D"] - BW/2, MID_Y)
label_edge(svg, (xs["B"] + DW/2 + xs["D"] - BW/2)/2, MID_Y - 8, "Không")

# B → (YES) down → C
arrow(svg, xs["B"], MID_Y + DH/2, xs["C"], C_Y - BH/2)
label_edge(svg, xs["B"] + 20, MID_Y + DH/2 + 20, "Có")

# C → D (from bottom-branch right to D)
# C right → horizontal to D bottom
arrow(svg, xs["C"] + BW/2, C_Y, xs["D"] - BW/2 + 10, MID_Y + BH/2 + 5)

# D → E → F → G → H → END
for a, b in [("D","E"),("E","F"),("F","G"),("G","H"),("H","END")]:
    x1 = xs[a] + (BW/2 if a != "END" else TW/2)
    x2 = xs[b] - (BW/2 if b != "END" else TW/2)
    arrow(svg, x1, MID_Y, x2, MID_Y)

# ── Output ─────────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

out1 = f"{DIAG}/svg/activity_create_plan.svg"
out2 = f"{ASSETS}/activity_create_plan.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
