"""
ocr_to_pima.py — Convert PaddleOCR JSON output → Zero-PIMA prescription JSON format.

Input  : PaddleOCR JSON (output/step-3_ocr-paddle/json/*.json)
Output : Zero-PIMA prescription JSON (data/pres/train/*.json or test/*.json)

Zero-PIMA prescription format (list of text blocks):
[
    {
        "text":    "Paracetamol 500mg",
        "label":   "drugname",          # "drugname" | "other" — GCN will predict this
        "box":     [x_min, y_min, x_max, y_max],
        "mapping": "Paracetamol-500mg"  # canonical label from ALL_PILL_LABELS, or null
    },
    ...
]

Usage:
    from core.converter.ocr_to_pima import OcrToPimaConverter
    converter = OcrToPimaConverter()
    pima_json = converter.convert_file("output/step-3_ocr-paddle/json/img.json")
    converter.save(pima_json, "data/pres/train/img.json")
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Allow importing DrugMapper from the same package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.converter.drug_mapper import DrugMapper


class OcrToPimaConverter:
    """
    Converts PaddleOCR JSON output to Zero-PIMA prescription JSON format.

    Pipeline:
        1. Load PaddleOCR JSON (list of text blocks with 4-point bbox)
        2. Normalize bbox: 4-point polygon → [xmin, ymin, xmax, ymax]
        3. DrugMapper: fuzzy-match text → canonical drug label
        4. Assign label: matched drug → "drugname", others → "other"
        5. Output Zero-PIMA format JSON

    Note on labels:
        - Blocks matched by DrugMapper get label="drugname", mapping=<canonical>
        - All others get label="other", mapping=null
        - Zero-PIMA's GCN will re-predict labels at inference time — this labeling
          is used for TRAINING the GCN. For inference only, you can pass all as
          "other" and GCN predicts on its own.
    """

    def __init__(self, drug_mapper: Optional[DrugMapper] = None, mapper_threshold: float = 60.0):
        """
        Args:
            drug_mapper: DrugMapper instance. If None, creates one with given threshold.
            mapper_threshold: Fuzzy match threshold for DrugMapper (default: 60.0).
        """
        self.mapper = drug_mapper or DrugMapper(threshold=mapper_threshold)

    # ── bbox normalization ────────────────────────────────────────────────────

    @staticmethod
    def _bbox_4pt_to_rect(bbox_4pt: list) -> list[int]:
        """
        Convert PaddleOCR 4-point polygon → [xmin, ymin, xmax, ymax].

        PaddleOCR bbox format:
            [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]  (top-left → clockwise)

        Args:
            bbox_4pt: List of 4 [x, y] points.

        Returns:
            [xmin, ymin, xmax, ymax] as integers.
        """
        xs = [pt[0] for pt in bbox_4pt]
        ys = [pt[1] for pt in bbox_4pt]
        return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]

    # ── line merging ─────────────────────────────────────────────────────────

    @staticmethod
    def merge_same_line_blocks(
        blocks: list, y_tol: int = 15, x_gap_max: int = 40
    ) -> list:
        """
        Merge text blocks that are on the same line into one block.

        "Same line" = Y-center coordinates within `y_tol` pixels AND
        blocks are within `x_gap_max` pixels horizontally.

        Ví dụ:
            ['Calcium', 'D3', 'Corbiere', '10ml'] → 'Calcium D3 Corbiere 10ml'

        Mục đích: cải thiện DrugMapper fuzzy match — full drug name khớp
        tốt hơn fragment. Zero-PIMA GCN vẫn dùng blocks gốc (word-level).

        Args:
            blocks: List of PaddleOCR blocks with 'text' and 'bbox'.
            y_tol: Max vertical distance (pixels) to consider same line.
            x_gap_max: Max horizontal gap (pixels) to merge blocks.

        Returns:
            List of merged blocks (same format as input).
        """
        if not blocks:
            return blocks

        def _y_center(block):
            bbox = block.get("bbox", [])
            if not bbox or len(bbox) < 4:
                return 0
            ys = [pt[1] for pt in bbox]
            return (min(ys) + max(ys)) / 2

        def _x_min(block):
            bbox = block.get("bbox", [])
            if not bbox:
                return 0
            return min(pt[0] for pt in bbox)

        def _x_max(block):
            bbox = block.get("bbox", [])
            if not bbox:
                return 0
            return max(pt[0] for pt in bbox)

        # Sort blocks top-to-bottom, left-to-right
        sorted_blocks = sorted(blocks, key=lambda b: (_y_center(b), _x_min(b)))

        merged = []
        used = [False] * len(sorted_blocks)

        for i, b in enumerate(sorted_blocks):
            if used[i]:
                continue

            # Start a new group with this block
            group = [b]
            used[i] = True
            y_i = _y_center(b)

            # Look for adjacent blocks on the same line
            for j in range(i + 1, len(sorted_blocks)):
                if used[j]:
                    continue
                b2 = sorted_blocks[j]
                y_j = _y_center(b2)

                # Must be on the same line
                if abs(y_j - y_i) > y_tol:
                    continue

                # Must be close horizontally to the last block in group
                last = group[-1]
                gap = _x_min(b2) - _x_max(last)
                if gap < x_gap_max:
                    group.append(b2)
                    used[j] = True

            if len(group) == 1:
                merged.append(b)
            else:
                # Merge: combine text + union bbox
                merged_text = " ".join(
                    g.get("text", "").strip() for g in group
                )
                all_xs = [pt[0] for g in group for pt in g.get("bbox", [])]
                all_ys = [pt[1] for g in group for pt in g.get("bbox", [])]
                if all_xs and all_ys:
                    xmin, xmax = min(all_xs), max(all_xs)
                    ymin, ymax = min(all_ys), max(all_ys)
                    merged_bbox = [
                        [xmin, ymin], [xmax, ymin],
                        [xmax, ymax], [xmin, ymax],
                    ]
                else:
                    merged_bbox = group[0].get("bbox", [])

                avg_conf = sum(
                    g.get("confidence", 0) for g in group
                ) / len(group)

                merged.append({
                    "text": merged_text,
                    "confidence": round(avg_conf, 4),
                    "bbox": merged_bbox,
                })

        return merged

    # ── cross-line drug grouping ──────────────────────────────────────────────

    @staticmethod
    def group_drug_lines(
        blocks: list,
        y_line_height_factor: float = 1.8,
        indent_threshold: int = 30,
    ) -> list:
        """
        Gộp các block thuộc cùng 1 mục thuốc nhưng xuống dòng.

        Quy tắc:
          - Block bắt đầu bằng số thứ tự ("1.", "2.", "3.") → đầu mục mới
          - Block tiếp theo nếu:
              * Bắt đầu bằng '(', '+', '-'  → tiếp nối tên thuốc
              * Thụt vào (x_min > first_x + indent_threshold) → tiếp nối
              * Y-distance < y_line_height_factor × avg_line_height → cùng nhóm
          - Block là DOSAGE (chứa từ khoá uống/viên/lần/buổi) → KHÔNG gộp
            vào tên thuốc, giữ riêng với label="other"

        Trả về list block đã gộp (format giữ nguyên).
        """
        import re

        if not blocks:
            return blocks

        # Keywords chỉ dẫn sử dụng → KHÔNG gộp vào tên thuốc
        DOSAGE_KEYWORDS = {
            "uống", "ngày", "lần", "viên", "ống", "sáng", "trưa",
            "chiều", "tối", "sau ăn", "trước ăn", "hòa tan", "nhỏ",
            "chia", "mỗi", "uong", "sang", "toi",
        }

        # Pattern số-đơn vị (ví dụ: "30", "12 10ml", "60", "1 Lọ")
        NUMBER_UNIT_RE = re.compile(
            r"^[\d\s\.]+("
            r"viên|ống|lọ|gói|ml|mg|tab|cap|g|ui|"
            r"vien|ong|lo|goi"
            r")?$",
            re.IGNORECASE | re.UNICODE,
        )

        def _is_dosage(text: str) -> bool:
            t = text.lower().strip()
            return any(kw in t for kw in DOSAGE_KEYWORDS)

        def _is_number_block(text: str) -> bool:
            """Block toàn số / đơn vị → bỏ qua (STT, số lượng)."""
            return bool(NUMBER_UNIT_RE.match(text.strip()))

        def _is_new_item(text: str) -> bool:
            """Block bắt đầu mục mới (số thứ tự)."""
            return bool(re.match(r"^\d+\s*[.)]\s", text.strip()))

        def _is_continuation(text: str) -> bool:
            """Block là tiếp nối tên thuốc dài."""
            t = text.strip()
            return t and t[0] in "(-+—"

        def _y_center(block):
            bbox = block.get("bbox", [])
            if not bbox:
                return 0
            ys = [pt[1] for pt in bbox]
            return (min(ys) + max(ys)) / 2

        def _x_min(block):
            bbox = block.get("bbox", [])
            return min(pt[0] for pt in bbox) if bbox else 0

        def _height(block):
            bbox = block.get("bbox", [])
            if not bbox:
                return 20
            ys = [pt[1] for pt in bbox]
            return max(ys) - min(ys)

        # Sort top → bottom, left → right
        sorted_blocks = sorted(blocks, key=lambda b: (_y_center(b), _x_min(b)))

        avg_h = max(1, sum(_height(b) for b in sorted_blocks) / len(sorted_blocks))

        grouped = []
        current_group = []
        current_x0 = 0

        def flush():
            if not current_group:
                return
            if len(current_group) == 1:
                grouped.append(current_group[0])
            else:
                # Merge drug name lines
                merged_text = " ".join(
                    g.get("text", "").strip() for g in current_group
                )
                all_xs = [pt[0] for g in current_group
                          for pt in g.get("bbox", [])]
                all_ys = [pt[1] for g in current_group
                          for pt in g.get("bbox", [])]
                xmin, xmax = min(all_xs), max(all_xs)
                ymin, ymax = min(all_ys), max(all_ys)
                avg_conf = sum(
                    g.get("confidence", 0) for g in current_group
                ) / len(current_group)
                grouped.append({
                    "text": merged_text,
                    "confidence": round(avg_conf, 4),
                    "bbox": [
                        [xmin, ymin], [xmax, ymin],
                        [xmax, ymax], [xmin, ymax],
                    ],
                })

        for block in sorted_blocks:
            text = block.get("text", "").strip()
            if not text:
                continue

            y = _y_center(block)
            x = _x_min(block)

            # Bỏ qua block thuần số/đơn vị (STT, số lượng)
            if _is_number_block(text):
                flush()
                current_group = []
                continue  # Không giữ lại, loại hẳn

            # Dosage lines giữ riêng ngay lập tức
            if _is_dosage(text):
                flush()
                current_group = []
                grouped.append({
                    **block,
                    "label": "dosage",
                })
                continue

            # Đầu mục mới
            if _is_new_item(text):
                flush()
                current_group = [block]
                current_x0 = x
                continue

            # Kiểm tra xem có phải tiếp nối của mục hiện tại không
            if current_group:
                last_y = _y_center(current_group[-1])
                y_gap = y - last_y
                is_close = y_gap < y_line_height_factor * avg_h
                is_indented = x > current_x0 + indent_threshold
                is_cont = _is_continuation(text)

                if is_close and (is_indented or is_cont):
                    current_group.append(block)
                    continue

            # Không phải tiếp nối → flush và bắt đầu nhóm mới
            flush()
            current_group = [block]
            current_x0 = x

        flush()
        return grouped

    # ── core conversion ───────────────────────────────────────────────────────

    def convert_blocks(self, blocks: list[dict]) -> list[dict]:
        """
        Convert a list of PaddleOCR blocks to Zero-PIMA format.

        Pipeline:
          1. Merge same-line blocks   → gộp từ bị tách trong 1 dòng
          2. Group cross-line blocks  → gộp tên thuốc xuống dòng (≠ dosage)
          3. Normalize bbox + DrugMapper match

        Args:
            blocks: List of dicts with {"text", "confidence", "bbox"}

        Returns:
            List of Zero-PIMA text block dicts.
        """
        # Bước 1: Gộp cùng dòng
        merged = self.merge_same_line_blocks(blocks)
        # Bước 2: Gộp xuống dòng (chỉ tên thuốc, không gộp dosage)
        merged = self.group_drug_lines(merged)

        pima_blocks = []

        for block in merged:
            text = block.get("text", "").strip()
            bbox_4pt = block.get("bbox", [])
            confidence = block.get("confidence", 0.0)

            if not text:
                continue

            # Normalize bbox
            if bbox_4pt and len(bbox_4pt) == 4:
                box = self._bbox_4pt_to_rect(bbox_4pt)
            else:
                box = [int(v) for v in bbox_4pt] if bbox_4pt else [0, 0, 0, 0]

            # Try drug name matching
            match_result = self.mapper.match(text)

            if match_result["status"] == "matched":
                label = "drugname"
                mapping = match_result["matched_label"]
            else:
                label = "other"
                mapping = None

            pima_block = {
                "text": text,
                "label": label,
                "box": box,
                "mapping": mapping,
                # Extra fields for debugging (not used by Zero-PIMA)
                "_ocr_confidence": round(confidence, 4),
                "_match_score": match_result["score"],
            }
            pima_blocks.append(pima_block)

        return pima_blocks


    def convert_ocr_json(self, ocr_json: dict) -> list[dict]:
        """
        Convert a full PaddleOCR JSON object.

        Args:
            ocr_json: Dict loaded from PaddleOCR output JSON file.
                      Expected keys: "blocks" (list of OCR blocks).

        Returns:
            List of Zero-PIMA format text block dicts.
        """
        blocks = ocr_json.get("blocks", [])
        return self.convert_blocks(blocks)

    def convert_file(self, ocr_json_path: str) -> list[dict]:
        """
        Load a PaddleOCR JSON file and convert to Zero-PIMA format.

        Args:
            ocr_json_path: Path to PaddleOCR JSON file.

        Returns:
            List of Zero-PIMA format text block dicts.
        """
        with open(ocr_json_path, "r", encoding="utf-8") as f:
            ocr_json = json.load(f)
        return self.convert_ocr_json(ocr_json)

    # ── output ────────────────────────────────────────────────────────────────

    @staticmethod
    def save(pima_blocks: list[dict], output_path: str, strip_debug: bool = True) -> None:
        """
        Save Zero-PIMA format blocks to a JSON file.

        Args:
            pima_blocks: List of Zero-PIMA blocks.
            output_path: Output file path (created including parent dirs).
            strip_debug: If True, remove internal debug fields (_ocr_confidence, _match_score).
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if strip_debug:
            clean_blocks = [
                {k: v for k, v in b.items() if not k.startswith("_")}
                for b in pima_blocks
            ]
        else:
            clean_blocks = pima_blocks

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(clean_blocks, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved: {output_path}  ({len(clean_blocks)} blocks)")

    def convert_and_save(self, ocr_json_path: str, output_path: str, strip_debug: bool = True) -> list[dict]:
        """
        Convenience: convert a file and save in one call.

        Returns:
            The converted blocks (with debug fields intact for inspection).
        """
        blocks = self.convert_file(ocr_json_path)
        self.save(blocks, output_path, strip_debug=strip_debug)
        return blocks

    # ── stats ─────────────────────────────────────────────────────────────────

    @staticmethod
    def print_stats(blocks: list[dict]) -> None:
        """Print a summary of conversion results."""
        total = len(blocks)
        drug_blocks = [b for b in blocks if b.get("label") == "drugname"]
        other_blocks = [b for b in blocks if b.get("label") == "other"]

        print(f"\n{'─'*50}")
        print(f"  Total blocks : {total}")
        print(f"  drugname     : {len(drug_blocks)}")
        print(f"  other        : {len(other_blocks)}")
        print(f"{'─'*50}")
        if drug_blocks:
            print(f"  Matched drugs:")
            for b in drug_blocks:
                score = b.get("_match_score", "?")
                print(f"    [{score:5}] '{b['text']}' → {b['mapping']}")
        print(f"{'─'*50}\n")


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import glob

    project_root = Path(__file__).parent.parent.parent
    ocr_json_dir = project_root / "output" / "step-3_ocr-paddle" / "json"
    output_dir   = project_root / "data" / "pres" / "test"

    json_files = sorted(glob.glob(str(ocr_json_dir / "*_mask.json")))

    if not json_files:
        print(f"❌ No OCR JSON files found in: {ocr_json_dir}")
        print("   Run the OCR pipeline first.")
        exit(1)

    converter = OcrToPimaConverter(mapper_threshold=60)

    print(f"\n{'='*60}")
    print(f"  OcrToPimaConverter — converting {len(json_files)} file(s)")
    print(f"{'='*60}")

    for ocr_path in json_files:
        stem = Path(ocr_path).stem  # e.g. "IMG_20260209_180420_mask"
        out_path = str(output_dir / f"{stem}.json")

        print(f"\n📄 {Path(ocr_path).name}")
        blocks = converter.convert_and_save(ocr_path, out_path, strip_debug=False)
        converter.print_stats(blocks)
