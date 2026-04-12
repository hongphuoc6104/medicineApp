#!/usr/bin/env python3
"""
Tạo UML Use Case diagram chuẩn học thuật bằng SVG thuần.
Không dùng Mermaid vì không thể render actor + oval đúng chuẩn UML.
"""

import xml.etree.ElementTree as ET
import math

# ─── Helpers ─────────────────────────────────────────────────────────────────

def add_style(svg, css):
    style = ET.SubElement(svg, "style")
    style.text = css

def rect(parent, x, y, w, h, rx=0, ry=0, **attrs):
    el = ET.SubElement(parent, "rect", x=str(x), y=str(y), width=str(w), height=str(h),
                       rx=str(rx), ry=str(ry))
    for k, v in attrs.items():
        el.set(k.replace("_", "-"), str(v))
    return el

def ellipse(parent, cx, cy, rx, ry, **attrs):
    el = ET.SubElement(parent, "ellipse", cx=str(cx), cy=str(cy), rx=str(rx), ry=str(ry))
    for k, v in attrs.items():
        el.set(k.replace("_", "-"), str(v))
    return el

def text(parent, x, y, content, **attrs):
    el = ET.SubElement(parent, "text", x=str(x), y=str(y))
    for k, v in attrs.items():
        el.set(k.replace("_", "-"), str(v))
    el.text = content
    return el

def tspan(parent_text, x, dy, content):
    el = ET.SubElement(parent_text, "tspan", x=str(x), dy=str(dy))
    el.text = content
    return el

def line(parent, x1, y1, x2, y2, **attrs):
    el = ET.SubElement(parent, "line", x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2))
    for k, v in attrs.items():
        el.set(k.replace("_", "-"), str(v))
    return el

def path(parent, d, **attrs):
    el = ET.SubElement(parent, "path", d=d)
    for k, v in attrs.items():
        el.set(k.replace("_", "-"), str(v))
    return el

# ─── Actor (stick figure) ─────────────────────────────────────────────────────

def draw_actor(parent, cx, top_y, label, label_lines=None):
    """Draw UML actor: circle head + stick body."""
    r = 16
    head_cy = top_y + r
    # head
    ellipse(parent, cx, head_cy, r, r, fill="white", stroke="#333", stroke_width="1.5")
    # body
    body_top = head_cy + r
    body_bot = body_top + 38
    line(parent, cx, body_top, cx, body_bot, stroke="#333", stroke_width="1.5")
    # arms
    line(parent, cx - 24, body_top + 12, cx + 24, body_top + 12, stroke="#333", stroke_width="1.5")
    # legs
    line(parent, cx, body_bot, cx - 20, body_bot + 28, stroke="#333", stroke_width="1.5")
    line(parent, cx, body_bot, cx + 20, body_bot + 28, stroke="#333", stroke_width="1.5")
    # label
    label_y = body_bot + 28 + 20
    if label_lines is None:
        label_lines = [label]
    t = ET.SubElement(parent, "text", x=str(cx), y=str(label_y),
                      **{"text-anchor": "middle", "font-size": "14",
                         "font-family": "Arial, sans-serif", "font-weight": "bold", "fill": "#222"})
    for i, ln in enumerate(label_lines):
        ts = ET.SubElement(t, "tspan", x=str(cx), dy="0" if i == 0 else "17")
        ts.text = ln
    return body_bot + 28  # bottom of legs

# ─── Use Case oval ────────────────────────────────────────────────────────────

def draw_usecase(parent, cx, cy, label_lines, rx=100, ry=28):
    """Draw UML use case: ellipse + centered text."""
    ellipse(parent, cx, cy, rx, ry, fill="#f0f4ff", stroke="#2457a5", stroke_width="1.8")
    t = ET.SubElement(parent, "text", x=str(cx), y=str(cy),
                      **{"text-anchor": "middle", "dominant-baseline": "central",
                         "font-size": "13", "font-family": "Arial, sans-serif", "fill": "#111"})
    n = len(label_lines)
    for i, ln in enumerate(label_lines):
        dy_val = (i - (n - 1) / 2) * 16
        ts = ET.SubElement(t, "tspan", x=str(cx), dy=str(dy_val) if i == 0 else "16")
        if i == 0:
            ts.set("dy", str(round((0 - (n - 1) / 2) * 16)))
        ts.text = ln
    return (cx - rx, cy - ry, 2 * rx, 2 * ry)  # bbox

# ─── Arrow ────────────────────────────────────────────────────────────────────

def arrow_line(parent, x1, y1, x2, y2, dashed=False, label=None):
    stroke_dash = "6,4" if dashed else "none"
    marker = "url(#arrowhead)" if not dashed else "url(#arrowhead-dash)"
    p = path(parent, f"M {x1} {y1} L {x2} {y2}",
              fill="none", stroke="#455a64", stroke_width="1.4",
              stroke_dasharray=stroke_dash, marker_end=marker)
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 - 8
        t = ET.SubElement(parent, "text", x=str(mx), y=str(my),
                          **{"text-anchor": "middle", "font-size": "11",
                             "font-family": "Arial, sans-serif", "fill": "#444",
                             "font-style": "italic"})
        t.text = label

def arrow_from_actor_to_uc(parent, actor_cx, actor_right_x, uc_left_x, uc_cy, body_mid_y):
    """Connect actor midpoint to left edge of use case."""
    x1 = actor_right_x
    y1 = body_mid_y
    x2 = uc_left_x
    y2 = uc_cy
    p = path(parent, f"M {x1} {y1} L {x2} {y2}",
              fill="none", stroke="#455a64", stroke_width="1.3",
              marker_end="url(#arrowhead)")

# ─── Defs (arrowheads) ────────────────────────────────────────────────────────

def add_defs(svg):
    defs = ET.SubElement(svg, "defs")
    # solid arrowhead
    marker = ET.SubElement(defs, "marker", id="arrowhead",
                           markerWidth="8", markerHeight="6",
                           refX="7", refY="3", orient="auto")
    ET.SubElement(marker, "polygon", points="0 0, 8 3, 0 6",
                  fill="#455a64")
    # dashed arrowhead
    marker2 = ET.SubElement(defs, "marker", id="arrowhead-dash",
                            markerWidth="8", markerHeight="6",
                            refX="7", refY="3", orient="auto")
    ET.SubElement(marker2, "polygon", points="0 0, 8 3, 0 6",
                  fill="#455a64")
    return defs

# ─── Main ─────────────────────────────────────────────────────────────────────

W = 900
H = 620

svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg",
                 width=str(W), height=str(H),
                 viewBox=f"0 0 {W} {H}")
add_defs(svg)

add_style(svg, """
  text { font-family: Arial, sans-serif; }
  .boundary-label { font-size: 13px; font-weight: bold; fill: #2457a5; }
""")

# background
rect(svg, 0, 0, W, H, fill="white")

# ── System boundary ──────────────────────────────────────────────────────────
BX, BY, BW, BH = 200, 40, 640, 540
rect(svg, BX, BY, BW, BH, rx=8, ry=8,
     fill="#f9fbfd", stroke="#8aa4c8", stroke_width="1.8",
     stroke_dasharray="none")

t = ET.SubElement(svg, "text", x=str(BX + 14), y=str(BY + 22),
                  **{"class": "boundary-label"})
t.text = "Hệ thống MedicineApp"

# ── Use cases (cx, cy, label_lines) ─────────────────────────────────────────
RX_UC = 108
RY_UC = 28

use_cases = [
    # (cx, cy, label_lines, id)
    (520, 130, ["Đăng nhập / Đăng ký"],          "uc1"),
    (480, 220, ["Quét đơn thuốc"],                "uc2"),
    (480, 310, ["Rà soát danh sách thuốc"],       "uc3"),
    (480, 400, ["Lập lịch dùng thuốc"],           "uc4"),
    (480, 490, ["Xem lịch hôm nay"],              "uc5"),
    (700, 400, ["Ghi nhận đã uống / bỏ qua"],     "uc6"),
    (700, 490, ["Xem lịch sử quét"],              "uc7"),
]

for cx, cy, labels, uid in use_cases:
    draw_usecase(svg, cx, cy, labels, rx=RX_UC, ry=RY_UC)

# ── Actor ────────────────────────────────────────────────────────────────────
ACTOR_CX = 90
ACTOR_TOP = 200
actor_leg_bottom = draw_actor(svg, ACTOR_CX, ACTOR_TOP, "", ["Người dùng"])
actor_body_mid_y = ACTOR_TOP + 16 + 19  # head_r + half body

# actor body midpoint (for arm level):
actor_arm_y = ACTOR_TOP + 16 + 12  # top_y + head_r + arm offset from body_top

# ── Connections: actor → use case ────────────────────────────────────────────
# Actor right edge approximate x
actor_right = ACTOR_CX + 24

connections_actor = [
    # (uc_cx, uc_cy, uc_rx)
    (520, 130, RX_UC),
    (480, 220, RX_UC),
    (480, 310, RX_UC),
    (480, 400, RX_UC),
    (480, 490, RX_UC),
    (700, 400, RX_UC),
    (700, 490, RX_UC),
]

for uc_cx, uc_cy, uc_rx in connections_actor:
    # from actor right to left edge of use case
    x1 = actor_right
    y1 = actor_arm_y
    x2 = uc_cx - uc_rx
    y2 = uc_cy
    path(svg, f"M {x1} {y1} L {x2} {y2}",
         fill="none", stroke="#455a64", stroke_width="1.2",
         marker_end="url(#arrowhead)")

# ── Include / Extend relationships ───────────────────────────────────────────
# uc2 --include--> uc3
def dashed_arrow(parent, x1, y1, x2, y2, label=""):
    path(parent, f"M {x1} {y1} L {x2} {y2}",
         fill="none", stroke="#455a64", stroke_width="1.2",
         stroke_dasharray="6,4", marker_end="url(#arrowhead-dash)")
    if label:
        mx = (x1 + x2) / 2 + 10
        my = (y1 + y2) / 2
        t = ET.SubElement(parent, "text", x=str(mx), y=str(my),
                          **{"text-anchor": "middle", "font-size": "10",
                             "font-family": "Arial, sans-serif", "fill": "#555",
                             "font-style": "italic"})
        t.text = label

# uc2 --include--> uc3 (vertical, right side of use cases)
dashed_arrow(svg, 480, 220 + RY_UC, 480, 310 - RY_UC, "«include»")
dashed_arrow(svg, 480, 310 + RY_UC, 480, 400 - RY_UC, "«include»")
dashed_arrow(svg, 480, 400 + RY_UC, 480, 490 - RY_UC, "«include»")
# uc5 --extend--> uc6
dashed_arrow(svg, 480 + RX_UC, 490, 700 - RX_UC, 400, "«extend»")

# ─── Output ──────────────────────────────────────────────────────────────────
import sys, os

out_svg = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/diagrams/svg/use_case.svg"
out_svg_assets = "/home/hongphuoc/Desktop/medicineApp/docs/thesis_report/assets/diagrams"

tree = ET.ElementTree(svg)
ET.indent(tree, space="  ")

os.makedirs(os.path.dirname(out_svg), exist_ok=True)
tree.write(out_svg, xml_declaration=True, encoding="unicode")
print(f"SVG written: {out_svg}")

# Also write a copy to assets/diagrams/use_case.svg (for reference)
out_svg2 = os.path.join(out_svg_assets, "use_case.svg")
tree.write(out_svg2, xml_declaration=True, encoding="unicode")
print(f"SVG copy: {out_svg2}")
