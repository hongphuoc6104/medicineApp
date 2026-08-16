"""Deterministic ingestion pipeline for Android Google ML Kit OCR JSON documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import (
    BoundingBox,
    OcrDocument,
    OcrEngine,
    OcrPage,
    OcrRegion,
    Point,
)

DEFAULT_OCR_ENGINE_NAME = "google_mlkit_text_recognition"
DEFAULT_OCR_ENGINE_VERSION = "0.15.1"


def _clamp(val: float | int, min_val: float, max_val: float) -> float:
    """Clamp a coordinate or float value to [min_val, max_val]."""
    return max(min_val, min(float(val), max_val))


def _extract_bbox(
    item: dict[str, Any], width: float, height: float
) -> BoundingBox:
    """Extract and clamp a 4-point BoundingBox from cornerPoints or boundingBox."""
    corner_points = item.get("cornerPoints")
    if isinstance(corner_points, list) and len(corner_points) == 4:
        points: tuple[Point, Point, Point, Point] = tuple(  # type: ignore[assignment]
            (
                _clamp(pt.get("x", 0.0), 0.0, width),
                _clamp(pt.get("y", 0.0), 0.0, height),
            )
            for pt in corner_points
        )
        return BoundingBox(points=points)

    bbox = item.get("boundingBox")
    if isinstance(bbox, dict):
        left = _clamp(bbox.get("left", 0.0), 0.0, width)
        top = _clamp(bbox.get("top", 0.0), 0.0, height)
        right = _clamp(bbox.get("right", 0.0), 0.0, width)
        bottom = _clamp(bbox.get("bottom", 0.0), 0.0, height)
        points = (
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom),
        )
        return BoundingBox(points=points)

    # Degenerate fallback
    zero_box = ((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0))
    return BoundingBox(points=zero_box)


def parse_mlkit_json_data(
    data: dict[str, Any],
    document_id: str | None = None,
    page_index: int = 0,
) -> OcrDocument:
    """Parse a deserialized ML Kit OCR JSON dictionary into a canonical OcrDocument."""
    metadata = data.get("metadata", {})
    if document_id is None:
        file_name = metadata.get("fileName")
        if file_name:
            document_id = Path(file_name).stem
        else:
            document_id = "doc_unknown"

    if not document_id:
        raise ValueError("document_id must be non-empty")

    image_width = max(1, int(metadata.get("imageWidth", 1000)))
    image_height = max(1, int(metadata.get("imageHeight", 1000)))

    regions: list[OcrRegion] = []
    reading_order = 0

    blocks = data.get("blocks", [])
    for b_idx, block in enumerate(blocks):
        lines = block.get("lines", [])
        if not lines:
            # Fallback for block without sub-lines
            block_text = block.get("text", "")
            if block_text:
                bbox = _extract_bbox(block, float(image_width), float(image_height))
                regions.append(
                    OcrRegion(
                        region_id=f"p{page_index}_b{b_idx}",
                        text=block_text,
                        confidence=None,
                        reading_order=reading_order,
                        bbox=bbox,
                    )
                )
                reading_order += 1
            continue

        for l_idx, line in enumerate(lines):
            line_text = line.get("text", "")
            bbox = _extract_bbox(line, float(image_width), float(image_height))
            raw_conf = line.get("confidence")
            confidence = (
                _clamp(raw_conf, 0.0, 1.0) if raw_conf is not None else None
            )

            regions.append(
                OcrRegion(
                    region_id=f"p{page_index}_b{b_idx}_l{l_idx}",
                    text=line_text,
                    confidence=confidence,
                    reading_order=reading_order,
                    bbox=bbox,
                )
            )
            reading_order += 1

    page = OcrPage(
        width=image_width,
        height=image_height,
        page_index=page_index,
        regions=regions,
    )

    return OcrDocument(
        schema_version="rxie.ocr.v1",
        document_id=document_id,
        ocr_engine=OcrEngine(
            name=DEFAULT_OCR_ENGINE_NAME,
            version=DEFAULT_OCR_ENGINE_VERSION,
        ),
        pages=[page],
    )


def load_mlkit_ocr_document(
    path: Path | str,
    document_id: str | None = None,
) -> OcrDocument:
    """Load and parse an Android ML Kit OCR JSON file from disk."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"ML Kit OCR file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if document_id is None:
        document_id = file_path.stem

    return parse_mlkit_json_data(data, document_id=document_id)


def ingest_all_mlkit_captures(
    source_dir: Path | str = "data/ocr_final",
) -> dict[str, OcrDocument]:
    """Ingest and validate all ML Kit OCR JSON captures in a directory."""
    directory = Path(source_dir)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"OCR source directory not found: {directory}")

    documents: dict[str, OcrDocument] = {}
    for json_file in sorted(directory.glob("*.json")):
        doc = load_mlkit_ocr_document(json_file)
        documents[doc.document_id] = doc

    return documents
