#!/usr/bin/env python3
"""
Tạo Architecture diagram SVG thuần tay.
Bố cục dọc (top-down) với 3 lớp rõ ràng + DB nodes.
"""

import xml.etree.ElementTree as ET
import os

W = 780
H = 680

def svg_root(w, h):
    el = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                    width=str(w), height=str(h),
                    viewBox=f"0 0 {w} {h}")
    return el

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    marker = ET.SubElement(defs, "marker", id="arr",
                           markerWidth="8", markerHeight="6",
                           refX="7", refY="3", orient="auto")
    ET.SubElement(marker, "polygon", points="0 0, 8 3, 0 6", fill="#455a64")
    # bidirectional (double arrow - we draw two lines)

def bg_rect(svg, x, y, w, h, fill, stroke, rx=6):
    ET.SubElement(svg, "rect", x=str(x), y=str(y), width=str(w), height=str(h),
                  rx=str(rx), fill=fill, stroke=stroke,
                  **{"stroke-width": "1.5"})

def label(svg, x, y, txt, size=13, bold=False, color="#111", anchor="middle"):
    attrs = {
        "x": str(x), "y": str(y),
        "text-anchor": anchor,
        "font-size": str(size),
        "font-family": "Arial, sans-serif",
        "fill": color,
    }
    if bold:
        attrs["font-weight"] = "bold"
    t = ET.SubElement(svg, "text", **attrs)
    t.text = txt
    return t

def multiline_label(svg, cx, top_y, lines, size=12, color="#111", line_h=16):
    """Centered multiline text, top_y is top of text block."""
    total_h = len(lines) * line_h
    start_y = top_y + line_h
    for i, ln in enumerate(lines):
        label(svg, cx, start_y + i * line_h, ln, size=size, color=color)

def box(svg, x, y, w, h, fill, stroke, lines, size=12, rx=5):
    bg_rect(svg, x, y, w, h, fill, stroke, rx=rx)
    cy = y + h / 2
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        label(svg, x + w / 2, cy + dy, ln, size=size)

def arrow(svg, x1, y1, x2, y2, bidir=False):
    ET.SubElement(svg, "path",
                  d=f"M {x1} {y1} L {x2} {y2}",
                  fill="none", stroke="#455a64",
                  **{"stroke-width": "1.4", "marker-end": "url(#arr)"})
    if bidir:
        ET.SubElement(svg, "path",
                      d=f"M {x2} {y2} L {x1} {y1}",
                      fill="none", stroke="#455a64",
                      **{"stroke-width": "1.4", "marker-end": "url(#arr)"})

def cylinder(svg, cx, cy, rw, rh, body_h, fill, stroke, lines):
    """Simplified cylinder (database) shape."""
    # top ellipse
    ET.SubElement(svg, "ellipse", cx=str(cx), cy=str(cy - body_h / 2),
                  rx=str(rw), ry=str(rh),
                  fill=fill, stroke=stroke, **{"stroke-width": "1.5"})
    # body rectangle
    ET.SubElement(svg, "rect",
                  x=str(cx - rw), y=str(cy - body_h / 2),
                  width=str(2 * rw), height=str(body_h),
                  fill=fill, stroke="none")
    # left/right sides
    ET.SubElement(svg, "line",
                  x1=str(cx - rw), y1=str(cy - body_h / 2),
                  x2=str(cx - rw), y2=str(cy + body_h / 2),
                  stroke=stroke, **{"stroke-width": "1.5"})
    ET.SubElement(svg, "line",
                  x1=str(cx + rw), y1=str(cy - body_h / 2),
                  x2=str(cx + rw), y2=str(cy + body_h / 2),
                  stroke=stroke, **{"stroke-width": "1.5"})
    # bottom ellipse
    ET.SubElement(svg, "ellipse", cx=str(cx), cy=str(cy + body_h / 2),
                  rx=str(rw), ry=str(rh),
                  fill=fill, stroke=stroke, **{"stroke-width": "1.5"})
    # text
    n = len(lines)
    for i, ln in enumerate(lines):
        dy = (i - (n - 1) / 2) * 15
        label(svg, cx, cy + dy, ln, size=11)

# ─── Build SVG ───────────────────────────────────────────────────────────────

svg = svg_root(W, H)
add_defs(svg)
ET.SubElement(svg, "rect", x="0", y="0", width=str(W), height=str(H), fill="white")

add_style = ET.SubElement(svg, "style")
add_style.text = "text { font-family: Arial, sans-serif; }"

# ── User node (top center) ────────────────────────────────────────────────────
user_cx = W // 2
user_y = 30
ET.SubElement(svg, "rect", x=str(user_cx - 70), y=str(user_y),
              width="140", height="36", rx="18",
              fill="#fff7e8", stroke="#b7791f", **{"stroke-width": "1.8"})
label(svg, user_cx, user_y + 23, "Người dùng", size=13, bold=True, color="#7a4512")

# ── Layer 1: Flutter App ──────────────────────────────────────────────────────
L1_Y = 100
L1_H = 130
L1_X = 40
L1_W = W - 80

bg_rect(svg, L1_X, L1_Y, L1_W, L1_H, "#eef7ff", "#4a90d9", rx=8)
label(svg, L1_X + 10, L1_Y + 18, "Tầng 1 — Ứng dụng di động (Flutter)",
      size=12, bold=True, color="#2457a5", anchor="start")

items1 = ["Quét đơn thuốc", "Rà soát danh sách", "Lập lịch dùng thuốc", "Xem lịch hôm nay"]
bw = (L1_W - 60) // 4
by_start = L1_X + 20
for i, it in enumerate(items1):
    bx = by_start + i * (bw + 10)
    box(svg, bx, L1_Y + 35, bw - 10, 70,
        "#d6eaff", "#4a90d9", [it], size=11, rx=5)

# ── Layer 2: Node.js Server ───────────────────────────────────────────────────
L2_Y = 270
L2_H = 130
L2_X = 40
L2_W = W - 80

bg_rect(svg, L2_X, L2_Y, L2_W, L2_H, "#f0fff4", "#2d7a46", rx=8)
label(svg, L2_X + 10, L2_Y + 18, "Tầng 2 — Máy chủ chính (Node.js / Express)",
      size=12, bold=True, color="#1a5c32", anchor="start")

items2 = ["Xác thực\nngười dùng", "Lịch sử\nquét", "Quản lý\nkế hoạch", "Nhật ký\nuống thuốc"]
for i, it in enumerate(items2):
    bx = by_start + i * (bw + 10)
    lines = it.split("\n")
    box(svg, bx, L2_Y + 35, bw - 10, 70,
        "#c3f0d0", "#2d7a46", lines, size=11, rx=5)

# ── Layer 3: AI Service ───────────────────────────────────────────────────────
L3_Y = 440
L3_H = 130
L3_X = 40
L3_W = W - 80

bg_rect(svg, L3_X, L3_Y, L3_W, L3_H, "#fff8e1", "#b7791f", rx=8)
label(svg, L3_X + 10, L3_Y + 18, "Tầng 3 — Dịch vụ AI (FastAPI / GPU)",
      size=12, bold=True, color="#7a4512", anchor="start")

items3 = ["YOLO\nDetect", "OCR\n(PaddleOCR\n+VietOCR)", "NER\n(PhoBERT)", "Tra cứu\nthuốc"]
heights3 = [70, 70, 70, 70]
for i, it in enumerate(items3):
    bx = by_start + i * (bw + 10)
    lines = it.split("\n")
    box(svg, bx, L3_Y + 35, bw - 10, 70,
        "#fff0c0", "#b7791f", lines, size=10, rx=5)

# ── DB nodes (bottom) ─────────────────────────────────────────────────────────
# PostgreSQL - left
DB_Y = 610
cylinder(svg, 220, DB_Y, 68, 14, 40, "#f0f4ff", "#2457a5",
         ["PostgreSQL"])

# KG - right
cylinder(svg, 560, DB_Y, 90, 14, 40, "#f0f4ff", "#2457a5",
         ["CSDL thuốc & Mô hình AI"])

# ── Arrows ────────────────────────────────────────────────────────────────────
# User → Layer 1
arrow(svg, user_cx, user_y + 36, user_cx, L1_Y)

# Layer 1 ↔ Layer 2
arrow(svg, W // 2 - 15, L1_Y + L1_H, W // 2 - 15, L2_Y, bidir=False)
arrow(svg, W // 2 + 15, L2_Y, W // 2 + 15, L1_Y + L1_H, bidir=False)

# Layer 2 ↔ Layer 3
arrow(svg, W // 2 - 15, L2_Y + L2_H, W // 2 - 15, L3_Y, bidir=False)
arrow(svg, W // 2 + 15, L3_Y, W // 2 + 15, L2_Y + L2_H, bidir=False)

# Layer 2 → PostgreSQL
arrow(svg, 220, L2_Y + L2_H, 220, DB_Y - 40 - 14)

# Layer 3 → KG
arrow(svg, 560, L3_Y + L3_H, 560, DB_Y - 40 - 14)

# ── Output ────────────────────────────────────────────────────────────────────
tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

DIAG = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams"
ASSETS = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

out1 = f"{DIAG}/svg/architecture.svg"
out2 = f"{ASSETS}/architecture.svg"

tree.write(out1, xml_declaration=True, encoding="unicode")
tree.write(out2, xml_declaration=True, encoding="unicode")
print(f"SVG written: {out1}")
print(f"SVG copy:    {out2}")
