#!/usr/bin/env python3
"""
Tạo Architecture diagram SVG thuần tay.
Bố cục dọc: Người dùng → Tầng 1 (Flutter) → Tầng 2 (Node.js) → Tầng 3 (AI)
+ 2 CSDL ở dưới với khoảng cách đủ rõ + mũi tên 2 chiều rõ ràng.
Tối ưu cho in A4.
"""

import xml.etree.ElementTree as ET
import os

W = 820
H = 720

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    for mid, col, aid in [("arr", "#37474f", "arr"), ("arr-b", "#37474f", "arr-b")]:
        m = ET.SubElement(defs, "marker", id=aid,
                          markerWidth="9", markerHeight="7",
                          refX="8", refY="3.5", orient="auto")
        ET.SubElement(m, "polygon", points="0 0, 9 3.5, 0 7", fill=col)
    # mũi tên ngược (refX=1 để đầu mũi nằm ở đầu kia)
    m3 = ET.SubElement(defs, "marker", id="arr-start",
                       markerWidth="9", markerHeight="7",
                       refX="1", refY="3.5", orient="auto-start-reverse")
    ET.SubElement(m3, "polygon", points="0 0, 9 3.5, 0 7", fill="#37474f")

svg = svg_root(W, H)
add_defs(svg)

st = ET.SubElement(svg, "style")
st.text = "text { font-family: Arial, sans-serif; }"

ET.SubElement(svg, "rect", x="0", y="0", width=str(W), height=str(H), fill="white")

# ─── Label helpers ─────────────────────────────────────────────────────────────

def lbl(svg, x, y, txt, size=12, bold=False, color="#111111",
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

def layer_rect(svg, x, y, w, h, fill, stroke, title, title_color, rx=8):
    ET.SubElement(svg, "rect", x=str(x), y=str(y), width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.8"})
    lbl(svg, x + 12, y + 19, title, size=12, bold=True,
        color=title_color, anchor="start")

def item_box(svg, cx, cy, w, h, lines, fill, stroke, size=11, rx=5):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.3"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        lbl(svg, cx, cy + dy, ln, size=size)

def bidir_arrow(svg, x1, y1, x2, y2, off=12):
    """Hai mũi tên song song (2 chiều) được tách ra off px."""
    # Đường từ trên xuống / trái sang phải
    ET.SubElement(svg, "path",
                  d=f"M {x1 - off} {y1} L {x2 - off} {y2}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
    # Đường ngược lại
    ET.SubElement(svg, "path",
                  d=f"M {x2 + off} {y2} L {x1 + off} {y1}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})

def single_arrow(svg, x1, y1, x2, y2):
    ET.SubElement(svg, "path",
                  d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})

def cylinder(svg, cx, cy, rw, rh, body_h, fill, stroke, lines, size=11):
    """CSDL hình trụ."""
    # thân
    ET.SubElement(svg, "rect",
                  x=str(cx - rw), y=str(cy - body_h / 2),
                  width=str(2 * rw), height=str(body_h),
                  fill=fill, stroke="none")
    ET.SubElement(svg, "line",
                  x1=str(cx - rw), y1=str(cy - body_h / 2),
                  x2=str(cx - rw), y2=str(cy + body_h / 2),
                  stroke=stroke, **{"stroke-width": "1.5"})
    ET.SubElement(svg, "line",
                  x1=str(cx + rw), y1=str(cy - body_h / 2),
                  x2=str(cx + rw), y2=str(cy + body_h / 2),
                  stroke=stroke, **{"stroke-width": "1.5"})
    # nắp dưới
    ET.SubElement(svg, "ellipse",
                  cx=str(cx), cy=str(cy + body_h / 2),
                  rx=str(rw), ry=str(rh),
                  fill=fill, stroke=stroke, **{"stroke-width": "1.5"})
    # nắp trên (vẽ sau để che thân)
    ET.SubElement(svg, "ellipse",
                  cx=str(cx), cy=str(cy - body_h / 2),
                  rx=str(rw), ry=str(rh),
                  fill=fill, stroke=stroke, **{"stroke-width": "1.5"})
    # nhãn
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        lbl(svg, cx, cy + dy, ln, size=size, bold=(i == 0))

# ─── Bố cục ────────────────────────────────────────────────────────────────────

PAD_X = 30
L_W   = W - 2 * PAD_X   # 760

# Người dùng
U_CX  = W // 2
U_Y   = 22
ET.SubElement(svg, "rect",
              x=str(U_CX - 80), y=str(U_Y),
              width="160", height="38", rx="19",
              fill="#fff7e8", stroke="#b7791f", **{"stroke-width": "2"})
lbl(svg, U_CX, U_Y + 24, "Người dùng", size=14, bold=True, color="#7a4512")

# Tầng 1 — Flutter
L1_Y, L1_H = 94, 134
layer_rect(svg, PAD_X, L1_Y, L_W, L1_H,
           "#e8f3fd", "#3a7ec9",
           "Tầng 1 — Ứng dụng di động (Flutter)", "#1a4a80")

items1 = [
    ["Quét đơn thuốc"],
    ["Rà soát danh sách"],
    ["Lập lịch dùng thuốc"],
    ["Xem lịch hôm nay"],
]
bw = (L_W - 60) // 4
gap = (L_W - 60 - 4 * bw) // 3
bh = 68
for i, its in enumerate(items1):
    bx = PAD_X + 24 + i * (bw + gap) + bw // 2
    item_box(svg, bx, L1_Y + 35 + bh // 2, bw, bh,
             its, "#c8e4fa", "#3a7ec9", size=11)

# Tầng 2 — Node.js
L2_Y, L2_H = 268, 134
layer_rect(svg, PAD_X, L2_Y, L_W, L2_H,
           "#edfaf3", "#2d7a46",
           "Tầng 2 — Máy chủ chính (Node.js / Express)", "#1a5c32")

items2 = [
    ["Xác thực", "người dùng"],
    ["Lịch sử", "quét"],
    ["Quản lý", "kế hoạch"],
    ["Nhật ký", "uống thuốc"],
]
for i, its in enumerate(items2):
    bx = PAD_X + 24 + i * (bw + gap) + bw // 2
    item_box(svg, bx, L2_Y + 35 + bh // 2, bw, bh,
             its, "#bef0d0", "#2d7a46", size=11)

# Tầng 3 — AI / FastAPI
L3_Y, L3_H = 442, 138
layer_rect(svg, PAD_X, L3_Y, L_W, L3_H,
           "#fffbec", "#c49a00",
           "Tầng 3 — Dịch vụ AI (FastAPI / GPU RTX 3050)", "#7a5c00")

items3 = [
    ["YOLO", "Detect"],
    ["OCR", "(PaddleOCR", "+ VietOCR)"],
    ["NER", "(PhoBERT)"],
    ["Tra cứu", "thuốc"],
]
for i, its in enumerate(items3):
    bx = PAD_X + 24 + i * (bw + gap) + bw // 2
    item_box(svg, bx, L3_Y + 38 + bh // 2, bw, bh + 8,
             its, "#fff0b0", "#c49a00", size=10)

# ─── 2 khối CSDL ──────────────────────────────────────────────────────────────
# Khoảng cách rõ ràng, tách biệt với L3
DB_Y = 635    # tâm y của CSDL
CYL_RW = 78
CYL_RH = 14
CYL_BH = 44

DB1_CX = 210   # PostgreSQL — dưới Tầng 2
DB2_CX = 580   # CSDL thuốc — dưới Tầng 3

cylinder(svg, DB1_CX, DB_Y, CYL_RW, CYL_RH, CYL_BH,
         "#eef2ff", "#2457a5",
         ["PostgreSQL", "(Dữ liệu hệ thống)"], size=11)

cylinder(svg, DB2_CX, DB_Y, CYL_RW + 22, CYL_RH, CYL_BH,
         "#eef2ff", "#2457a5",
         ["CSDL thuốc &", "Mô hình AI"], size=11)

# ─── Các mũi tên ──────────────────────────────────────────────────────────────

# Người dùng → Tầng 1
single_arrow(svg, U_CX, U_Y + 38, U_CX, L1_Y)

# Tầng 1 ↔ Tầng 2 (bidir)
MID_X = W // 2
bidir_arrow(svg, MID_X, L1_Y + L1_H, MID_X, L2_Y, off=14)

# Tầng 2 ↔ Tầng 3 (bidir)
bidir_arrow(svg, MID_X, L2_Y + L2_H, MID_X, L3_Y, off=14)

# Tầng 2 → PostgreSQL (bidir: lưu + truy vấn)
# Vẽ mũi tên thẳng xuống từ cạnh bên trái Tầng 2
bidir_arrow(svg, DB1_CX, L2_Y + L2_H, DB1_CX, DB_Y - CYL_BH // 2 - CYL_RH, off=10)

# nhãn bên cạnh mũi tên DB1
lbl(svg, DB1_CX + 42, (L2_Y + L2_H + DB_Y - CYL_BH // 2 - CYL_RH) // 2,
    "Đọc / Ghi", size=10, italic=True, color="#444444")

# Tầng 3 → CSDL thuốc (một chiều)
single_arrow(svg, DB2_CX, L3_Y + L3_H, DB2_CX, DB_Y - CYL_BH // 2 - CYL_RH)
lbl(svg, DB2_CX + 46, (L3_Y + L3_H + DB_Y - CYL_BH // 2 - CYL_RH) // 2,
    "Tra cứu", size=10, italic=True, color="#444444")

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

os.makedirs(f"{DIAG}/svg", exist_ok=True)
out1 = f"{DIAG}/svg/architecture.svg"
out2 = f"{ASSETS}/architecture.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")

import cairosvg
for sp, pp in [
    (out1, f"{DIAG}/png/architecture.png"),
    (out2, f"{ASSETS}/architecture.png"),
]:
    cairosvg.svg2png(url=sp, write_to=pp, scale=2.5)
    print(f"PNG: {pp}")
