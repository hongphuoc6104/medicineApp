#!/usr/bin/env python3
"""
Tạo scan_flow diagram — Pipeline AI Phase A.
Bố cục: 2 cột (Cột A = pipeline chính, Cột B = nhánh lỗi + kết quả cuối).
Đủ lớn để đọc khi in A4 portrait.
Không dùng emoji. Toàn bộ nhãn tiếng Việt có dấu.
"""

import xml.etree.ElementTree as ET
import os

W = 740
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

def step_box(svg, cx, cy, w, h, lines, fill, stroke, size=12, rx=7):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.6"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 16
        lbl(svg, cx, cy + dy, ln, size=size)

def diamond(svg, cx, cy, w, h, lines, fill="#fff8e1",
            stroke="#b7791f", size=12):
    hw, hh = w / 2, h / 2
    pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
    ET.SubElement(svg, "polygon", points=pts, fill=fill,
                  stroke=stroke, **{"stroke-width": "1.6"})
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        lbl(svg, cx, cy + dy, ln, size=size)

def terminal(svg, cx, cy, w, h, txt, fill="#1a3a6e", size=13):
    ET.SubElement(svg, "rect",
                  x=str(cx - w / 2), y=str(cy - h / 2),
                  width=str(w), height=str(h),
                  rx=str(h / 2),
                  fill=fill, stroke=fill, **{"stroke-width": "1.5"})
    lbl(svg, cx, cy, txt, size=size, bold=True, color="white")

def arrow(svg, x1, y1, x2, y2, label="", label_side="right"):
    ET.SubElement(svg, "path",
                  d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        off_x = 28 if label_side == "right" else -28
        off_y = -10 if abs(x2 - x1) > 10 else 0
        lbl(svg, mx + off_x, my + off_y, label,
            size=11, italic=True, color="#555")

def path_arrow(svg, d, label="", lx=None, ly=None):
    ET.SubElement(svg, "path", d=d, fill="none", stroke="#37474f",
                  **{"stroke-width": "1.5", "marker-end": "url(#arr)"})
    if label and lx is not None:
        lbl(svg, lx, ly, label, size=11, italic=True, color="#555")

# ─── Bố cục ────────────────────────────────────────────────────────────────────
# Cột trái: pipeline chính (input → bước 5 → danh sách → lịch)
# Cột phải: nhánh lỗi reject

COL_L  = 290    # x trung tâm cột trái (pipeline chính)
COL_R  = 570    # x trung tâm cột phải (reject / cạnh)

BW = 300        # chiều rộng box
BH = 62         # chiều cao box
GAP = 90        # khoảng cách giữa các bước

y_pos = {
    "input":   60,
    "b1":     155,
    "b2":     255,
    "qg":     355,
    "b3":     460,
    "b4":     555,
    "b5":     650,
    "result": 730,
}

REJ_Y  = y_pos["qg"]      # nhánh reject ngang hàng với QG
SCHED_Y = y_pos["result"]

# ── Node: đầu vào ──────────────────────────────────────────────────────────────
terminal(svg, COL_L, y_pos["input"], 220, 36, "Ảnh đơn thuốc đầu vào")

# ── Bước 1 ──────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_pos["b1"], BW, BH,
         ["Bước 1: Phát hiện và cắt vùng đơn thuốc",
          "(YOLO Detect — Convex Hull Crop)"],
         "#edf7f0", "#2d7a46", size=12)

# ── Bước 2 ──────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_pos["b2"], BW, BH,
         ["Bước 2: Tiền xử lý ảnh",
          "(Chỉnh nghiêng Modulo 90 + Căn hướng AI)"],
         "#edf7f0", "#2d7a46", size=12)

# ── Quality Gate ─────────────────────────────────────────────────────────────────
diamond(svg, COL_L, y_pos["qg"], 210, 70,
        ["Kiểm tra", "chất lượng ảnh"],
        fill="#fff8e1", stroke="#b7791f", size=12)

# ── Reject (cột phải) ─────────────────────────────────────────────────────────
step_box(svg, COL_R, REJ_Y, 220, 56,
         ["Từ chối —", "Yêu cầu chụp lại"],
         "#fff3f3", "#c53030", size=12)

# ── Bước 3 ──────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_pos["b3"], BW, BH,
         ["Bước 3: Nhận dạng ký tự quang học",
          "(PaddleOCR + VietOCR)"],
         "#edf7f0", "#2d7a46", size=12)

# ── Bước 4 ──────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_pos["b4"], BW, BH,
         ["Bước 4: Trích xuất tên thuốc",
          "(PhoBERT NER)"],
         "#edf7f0", "#2d7a46", size=12)

# ── Bước 5 ──────────────────────────────────────────────────────────────────────
step_box(svg, COL_L, y_pos["b5"], BW, BH,
         ["Bước 5: Tra cứu và chuẩn hóa",
          "(Cơ sở dữ liệu 9.284 thuốc)"],
         "#edf7f0", "#2d7a46", size=12)

# ── Kết quả + Lập lịch ───────────────────────────────────────────────────────
step_box(svg, COL_L, SCHED_Y, BW, 56,
         ["Danh sách thuốc — Rà soát và Lập lịch"],
         "#dbeafe", "#2457a5", size=12)

# ─── Mũi tên chính ─────────────────────────────────────────────────────────────
arrow(svg, COL_L, y_pos["input"] + 18, COL_L, y_pos["b1"] - BH // 2)
arrow(svg, COL_L, y_pos["b1"] + BH // 2, COL_L, y_pos["b2"] - BH // 2)
arrow(svg, COL_L, y_pos["b2"] + BH // 2, COL_L, y_pos["qg"] - 35)

# QG → Bước 3 (Đạt yêu cầu)
arrow(svg, COL_L, y_pos["qg"] + 35, COL_L, y_pos["b3"] - BH // 2,
      "Đạt yêu cầu", label_side="right")

# QG → Reject (nhánh phải)
path_arrow(svg,
           f"M {COL_L + 105} {REJ_Y} L {COL_R - 110} {REJ_Y}",
           "Quá mờ / chói", lx=(COL_L + COL_R) / 2, ly=REJ_Y - 12)

arrow(svg, COL_L, y_pos["b3"] + BH // 2, COL_L, y_pos["b4"] - BH // 2)
arrow(svg, COL_L, y_pos["b4"] + BH // 2, COL_L, y_pos["b5"] - BH // 2)
arrow(svg, COL_L, y_pos["b5"] + BH // 2, COL_L, SCHED_Y - 28)

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

import cairosvg
for sp, pp in [
    (out1, f"{DIAG}/png/scan_flow.png"),
    (out2, f"{ASSETS}/scan_flow.png"),
]:
    cairosvg.svg2png(url=sp, write_to=pp, scale=2.5)
    print(f"PNG: {pp}")
