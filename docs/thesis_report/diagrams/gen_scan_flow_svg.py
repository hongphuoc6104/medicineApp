#!/usr/bin/env python3
"""
Hình 3.4 — Sơ đồ luồng xử lý nhận diện đơn thuốc (Scan Flow).
Cải tiến:
  - Bố cục 2 cột: cột trái = pipeline chính (5 bước), cột phải = reject + endpoint.
  - Canvas rộng 860px × cao 780px, đủ chỗ cho chữ lớn.
  - Font 13px cho tất cả nhãn bên trong box và nhãn mũi tên.
  - Box height 70px, đủ 2 dòng chữ 13px không bị đè nhau.
  - Mũi tên sạch, thẳng, không chồng nhau.
  - Không emoji. Toàn tiếng Việt có dấu.
"""

import xml.etree.ElementTree as ET
import os

W = 860
H = 800

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

def step_box(svg, cx, cy, w, h, lines, fill, stroke, size=13, rx=7):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.7"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 18
        lbl(svg, cx, cy + dy, ln, size=size)

def diamond(svg, cx, cy, w, h, lines, fill="#fff8e1",
            stroke="#b7791f", size=13):
    hw, hh = w / 2, h / 2
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    ET.SubElement(svg, "polygon", points=pts, fill=fill,
                  stroke=stroke, **{"stroke-width": "1.7"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 16
        lbl(svg, cx, cy + dy, ln, size=size)

def terminal(svg, cx, cy, w, h, txt, fill="#1a3a6e", size=14):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(h / 2),
                  fill=fill, stroke=fill, **{"stroke-width": "1.5"})
    lbl(svg, cx, cy + 1, txt, size=size, bold=True, color="white")

def arrow(svg, x1, y1, x2, y2, label="", label_side="right", size=12):
    ET.SubElement(svg, "path",
                  d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.6", "marker-end": "url(#arr)"})
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        off_x = 32 if label_side == "right" else -32
        off_y = -11 if abs(x2 - x1) > 10 else 0
        lbl(svg, mx + off_x, my + off_y, label,
            size=size, italic=True, color="#555")

def path_arrow(svg, d, label="", lx=None, ly=None, size=12):
    ET.SubElement(svg, "path", d=d, fill="none", stroke="#37474f",
                  **{"stroke-width": "1.6", "marker-end": "url(#arr)"})
    if label and lx is not None:
        lbl(svg, lx, ly, label, size=size, italic=True, color="#555")

# ─── Bố cục ────────────────────────────────────────────────────────────────────
# Cột trái (pipeline chính): x = 310
# Cột phải (reject + kết quả): x = 630

COL_L = 310
COL_R = 630

BW  = 330   # box width
BH  = 70    # box height
DW  = 220   # diamond width
DH  = 76    # diamond height
GAP = 95    # khoảng cách dọc giữa các node

y_input  = 55
y_b1     = y_input  + 55 + BH // 2
y_b2     = y_b1     + GAP
y_qg     = y_b2     + GAP + 5   # +5 bù cho diamond cao hơn
y_b3     = y_qg     + GAP + 5
y_b4     = y_b3     + GAP
y_b5     = y_b4     + GAP
y_result = y_b5     + GAP - 5

REJ_Y    = y_qg   # reject ngang hàng diamond

# ── Đầu vào ──────────────────────────────────────────────────────────────────
terminal(svg, COL_L, y_input, 240, 40, "Ảnh đơn thuốc đầu vào")

# ── Bước 1 ────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_b1, BW, BH,
         ["Bước 1: Phát hiện và cắt vùng đơn thuốc",
          "(YOLO Detect — Convex Hull Crop)"],
         "#edf7f0", "#2d7a46", size=13)

# ── Bước 2 ────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_b2, BW, BH,
         ["Bước 2: Tiền xử lý ảnh",
          "(Chỉnh nghiêng Modulo 90 + Căn hướng AI)"],
         "#edf7f0", "#2d7a46", size=13)

# ── Kiểm tra chất lượng ─────────────────────────────────────────────────────
diamond(svg, COL_L, y_qg, DW, DH,
        ["Kiểm tra", "chất lượng ảnh"],
        fill="#fff8e1", stroke="#b7791f", size=13)

# ── Reject (cột phải) ────────────────────────────────────────────────────────
step_box(svg, COL_R, REJ_Y, 230, 62,
         ["Từ chối —", "Yêu cầu chụp lại"],
         "#fff3f3", "#c53030", size=13)

# ── Bước 3 ────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_b3, BW, BH,
         ["Bước 3: Nhận dạng ký tự quang học",
          "(PaddleOCR + VietOCR)"],
         "#edf7f0", "#2d7a46", size=13)

# ── Bước 4 ────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_b4, BW, BH,
         ["Bước 4: Trích xuất tên thuốc",
          "(PhoBERT NER)"],
         "#edf7f0", "#2d7a46", size=13)

# ── Bước 5 ────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_b5, BW, BH,
         ["Bước 5: Tra cứu và chuẩn hóa tên thuốc",
          "(Cơ sở dữ liệu 9.284 thuốc Việt Nam)"],
         "#edf7f0", "#2d7a46", size=13)

# ── Kết quả ──────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_result, BW, 60,
         ["Danh sách thuốc — Rà soát và Lập lịch"],
         "#dbeafe", "#2457a5", size=13)

# ─── Mũi tên chính ─────────────────────────────────────────────────────────────
arrow(svg, COL_L, y_input + 20,      COL_L, y_b1 - BH // 2)
arrow(svg, COL_L, y_b1 + BH // 2,   COL_L, y_b2 - BH // 2)
arrow(svg, COL_L, y_b2 + BH // 2,   COL_L, y_qg - DH // 2)

# QG → Bước 3 (Đạt yêu cầu)
arrow(svg, COL_L, y_qg + DH // 2,   COL_L, y_b3 - BH // 2,
      "Đạt yêu cầu", label_side="right")

# QG → Reject (ngang sang phải)
path_arrow(svg,
           f"M {COL_L + DW // 2} {REJ_Y} L {COL_R - 115} {REJ_Y}",
           "Quá mờ / chói",
           lx=(COL_L + DW // 2 + COL_R - 115) / 2,
           ly=REJ_Y - 12)

arrow(svg, COL_L, y_b3 + BH // 2,   COL_L, y_b4 - BH // 2)
arrow(svg, COL_L, y_b4 + BH // 2,   COL_L, y_b5 - BH // 2)
arrow(svg, COL_L, y_b5 + BH // 2,   COL_L, y_result - 30)

# ─── Output ───────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG   = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

os.makedirs(f"{DIAG}/svg", exist_ok=True)
out1 = f"{DIAG}/svg/scan_flow.svg"
out2 = f"{ASSETS}/scan_flow.svg"
tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG: {out1}")
print(f"SVG: {out2}")

import cairosvg
for sv, pn in [
    (out1, f"{DIAG}/png/scan_flow.png"),
    (out2, f"{ASSETS}/scan_flow.png"),
]:
    cairosvg.svg2png(url=sv, write_to=pn, scale=2.5)
    print(f"PNG: {pn}")
