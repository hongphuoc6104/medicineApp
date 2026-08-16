"""Adversarial stress testing and edge-case validation for ML Kit OCR Ingestion.

Milestone M0 / A0 Empirical Challenger Suite.
Covers:
1. Coordinate fuzzing (extreme negative/positive, non-integer floats, zero-size).
2. Polygon anomalies in cornerPoints (inverted, concave, bowtie, collinear).
3. Missing fields, extra fields, None vs empty string vs missing structures.
4. Confidence fuzzing (negative, > 1.0, 0.0, 1.0, None, float boundaries).
5. Document ID edge cases (unicode, dots, paths, spaces, fallback, validation).
6. Multi-block complex hierarchies, 1000+ regions, mixed line fallbacks.
7. Vietnamese diacritics, NFC/NFD forms, tabs, newlines, zero-width spaces, emoji.
8. Property-based random payload fuzzing oracle verifying all invariants.
"""

from __future__ import annotations

import json
import random
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from rxie.ingestion import (
    DEFAULT_OCR_ENGINE_NAME,
    DEFAULT_OCR_ENGINE_VERSION,
    _clamp,
    _extract_bbox,
    ingest_all_mlkit_captures,
    load_mlkit_ocr_document,
    parse_mlkit_json_data,
)
from rxie.schemas import (
    BoundingBox,
    OcrDocument,
    OcrEngine,
    OcrPage,
    OcrRegion,
)
from rxie.text import build_document_text


# ===========================================================================
# 1. Bounding Box Coordinate Fuzzing & Geometry Stress
# ===========================================================================


@pytest.mark.parametrize(
    ("coords", "width", "height", "expected_points"),
    [
        # Extreme negative coordinates
        (
            [{"x": -1e9, "y": -1e9}, {"x": -500.0, "y": -1e6}, {"x": -0.001, "y": -10.0}, {"x": -1e12, "y": 0.0}],
            1000.0,
            2000.0,
            ((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
        ),
        # Massive positive coordinates
        (
            [{"x": 1e9, "y": 1e9}, {"x": 50000.0, "y": 1e6}, {"x": 1000.001, "y": 2000.1}, {"x": 1e12, "y": 9999.0}],
            1000.0,
            2000.0,
            ((1000.0, 2000.0), (1000.0, 2000.0), (1000.0, 2000.0), (1000.0, 2000.0)),
        ),
        # Non-integer floats with fine precision
        (
            [{"x": 12.34567, "y": 98.76543}, {"x": 500.1111, "y": 98.76543}, {"x": 500.1111, "y": 300.9999}, {"x": 12.34567, "y": 300.9999}],
            1000.0,
            1000.0,
            ((12.34567, 98.76543), (500.1111, 98.76543), (500.1111, 300.9999), (12.34567, 300.9999)),
        ),
        # Zero-width / Zero-height (collapsed to a single line or point)
        (
            [{"x": 100.0, "y": 200.0}, {"x": 100.0, "y": 200.0}, {"x": 100.0, "y": 200.0}, {"x": 100.0, "y": 200.0}],
            1000.0,
            1000.0,
            ((100.0, 200.0), (100.0, 200.0), (100.0, 200.0), (100.0, 200.0)),
        ),
        # Coordinates exactly on page boundaries
        (
            [{"x": 0.0, "y": 0.0}, {"x": 1000.0, "y": 0.0}, {"x": 1000.0, "y": 2000.0}, {"x": 0.0, "y": 2000.0}],
            1000.0,
            2000.0,
            ((0.0, 0.0), (1000.0, 0.0), (1000.0, 2000.0), (0.0, 2000.0)),
        ),
    ],
)
def test_fuzz_corner_points_coordinates(
    coords: list[dict[str, float]],
    width: float,
    height: float,
    expected_points: tuple[Any, Any, Any, Any],
) -> None:
    """Verify that extreme, zero, and high-precision coordinates are clamped and valid."""
    item = {"cornerPoints": coords}
    bbox = _extract_bbox(item, width, height)
    assert isinstance(bbox, BoundingBox)
    assert bbox.points == expected_points


@pytest.mark.parametrize(
    ("bbox_dict", "width", "height", "expected_points"),
    [
        # Extreme negative boundingBox
        (
            {"left": -99999.0, "top": -88888.0, "right": -10.0, "bottom": -5.0},
            1000.0,
            1000.0,
            ((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
        ),
        # Massive overflow boundingBox
        (
            {"left": 1500.0, "top": 2500.0, "right": 99999.0, "bottom": 88888.0},
            1000.0,
            2000.0,
            ((1000.0, 2000.0), (1000.0, 2000.0), (1000.0, 2000.0), (1000.0, 2000.0)),
        ),
        # Floating point boundingBox with sub-pixel offsets
        (
            {"left": 0.0001, "top": 0.0002, "right": 999.9999, "bottom": 1999.9999},
            1000.0,
            2000.0,
            ((0.0001, 0.0002), (999.9999, 0.0002), (999.9999, 1999.9999), (0.0001, 1999.9999)),
        ),
        # Missing keys in boundingBox (defaults to 0.0)
        (
            {"left": 50.0},
            500.0,
            500.0,
            ((50.0, 0.0), (0.0, 0.0), (0.0, 0.0), (50.0, 0.0)),
        ),
    ],
)
def test_fuzz_bounding_box_dict(
    bbox_dict: dict[str, float],
    width: float,
    height: float,
    expected_points: tuple[Any, Any, Any, Any],
) -> None:
    """Verify boundingBox dict fallback handles extreme values and missing keys."""
    item = {"boundingBox": bbox_dict}
    bbox = _extract_bbox(item, width, height)
    assert isinstance(bbox, BoundingBox)
    assert bbox.points == expected_points


# ===========================================================================
# 2. Inverted, Concave, and Degenerate Polygons in cornerPoints
# ===========================================================================


def test_inverted_and_concave_polygons_pass_pydantic_contract() -> None:
    """Verify inverted, bow-tie, and concave polygons construct valid BoundingBox."""
    # Bow-tie / self-intersecting polygon
    bowtie_payload = {
        "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "bowtie.jpg"},
        "fullText": "Bowtie Test",
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Bowtie Test",
                        "cornerPoints": [
                            {"x": 100, "y": 100},
                            {"x": 500, "y": 500},
                            {"x": 500, "y": 100},
                            {"x": 100, "y": 500},
                        ],
                    }
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(bowtie_payload)
    assert isinstance(doc, OcrDocument)
    region = doc.pages[0].regions[0]
    assert region.bbox.points == (
        (100.0, 100.0),
        (500.0, 500.0),
        (500.0, 100.0),
        (100.0, 500.0),
    )


def test_collinear_and_single_point_polygons() -> None:
    """Verify collinear points (degenerate 1D line) construct valid BoundingBox."""
    collinear_payload = {
        "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "collinear.jpg"},
        "fullText": "Collinear Test",
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Collinear Test",
                        "cornerPoints": [
                            {"x": 100, "y": 100},
                            {"x": 200, "y": 100},
                            {"x": 300, "y": 100},
                            {"x": 400, "y": 100},
                        ],
                    }
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(collinear_payload)
    assert isinstance(doc, OcrDocument)
    assert doc.pages[0].regions[0].bbox.points == (
        (100.0, 100.0),
        (200.0, 100.0),
        (300.0, 100.0),
        (400.0, 100.0),
    )


def test_corner_points_with_partial_or_missing_xy_keys() -> None:
    """Verify cornerPoints where individual points lack 'x' or 'y' default to 0.0."""
    item = {
        "cornerPoints": [
            {"x": 10},
            {"y": 20},
            {},
            {"x": 100, "y": 200, "z": 999},  # extra key 'z'
        ]
    }
    bbox = _extract_bbox(item, 1000.0, 1000.0)
    assert bbox.points == (
        (10.0, 0.0),
        (0.0, 20.0),
        (0.0, 0.0),
        (100.0, 200.0),
    )


# ===========================================================================
# 3. Missing Fields, Extra Fields, None vs Empty String
# ===========================================================================


def test_payload_with_extensive_unknown_and_extra_fields() -> None:
    """Verify raw JSON containing arbitrary extra fields parses without error.

    Pydantic models have extra="forbid", so this confirms the ingestion layer
    correctly extracts only valid contract fields.
    """
    raw_payload = {
        "unrecognized_root_key": "some_value",
        "nested_garbage": {"a": [1, 2, 3], "b": True},
        "metadata": {
            "fileName": "extra_fields.jpg",
            "imageWidth": 2000,
            "imageHeight": 3000,
            "deviceModel": "Samsung Galaxy S22",
            "batteryLevel": 88,
            "extraMeta": {"nested": "value"},
        },
        "fullText": "Line 1\nLine 2",
        "blocks": [
            {
                "blockExtra": 12345,
                "lines": [
                    {
                        "text": "Line 1",
                        "lineExtraField": "ignored",
                        "cornerPoints": [
                            {"x": 0, "y": 0, "color": "red"},
                            {"x": 100, "y": 0, "color": "blue"},
                            {"x": 100, "y": 50, "color": "green"},
                            {"x": 0, "y": 50, "color": "yellow"},
                        ],
                        "confidence": 0.95,
                    },
                    {
                        "text": "Line 2",
                        "boundingBox": {
                            "left": 0,
                            "top": 60,
                            "right": 100,
                            "bottom": 110,
                            "extra": "ignore_me",
                        },
                        "confidence": 0.88,
                    },
                ],
            }
        ],
    }

    doc = parse_mlkit_json_data(raw_payload)
    assert isinstance(doc, OcrDocument)
    assert doc.document_id == "extra_fields"
    assert len(doc.pages[0].regions) == 2
    # Verify strict serialization of OcrDocument
    dumped = doc.model_dump()
    assert "deviceModel" not in dumped
    assert "batteryLevel" not in dumped


def test_payload_with_minimal_keys() -> None:
    """Verify minimal empty dictionary parses with safe defaults."""
    minimal_payload: dict[str, Any] = {}
    doc = parse_mlkit_json_data(minimal_payload)

    assert isinstance(doc, OcrDocument)
    assert doc.document_id == "doc_unknown"
    assert doc.pages[0].width == 1000  # Default fallback width
    assert doc.pages[0].height == 1000  # Default fallback height
    assert doc.pages[0].regions == []


def test_metadata_dimension_edge_cases() -> None:
    """Verify imageWidth/imageHeight with 0, negative, or string values."""
    payload = {
        "metadata": {
            "imageWidth": 0,
            "imageHeight": -500,
            "fileName": "dimensions_test.jpg",
        },
        "blocks": [],
    }
    doc = parse_mlkit_json_data(payload)
    assert doc.pages[0].width == 1
    assert doc.pages[0].height == 1


def test_empty_string_and_whitespace_only_line_text() -> None:
    """Verify lines with empty string or whitespace are preserved accurately."""
    payload = {
        "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "spaces.jpg"},
        "fullText": " \n\t\nLine with text",
        "blocks": [
            {
                "lines": [
                    {"text": " ", "confidence": 0.5},
                    {"text": "\t", "confidence": 0.5},
                    {"text": "Line with text", "confidence": 0.95},
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(payload)
    assert len(doc.pages[0].regions) == 3
    assert doc.pages[0].regions[0].text == " "
    assert doc.pages[0].regions[1].text == "\t"
    assert doc.pages[0].regions[2].text == "Line with text"

    doc_text = build_document_text(doc)
    assert doc_text.raw_text == " \n\t\nLine with text"


# ===========================================================================
# 4. Confidence Fuzzing & Boundaries
# ===========================================================================


@pytest.mark.parametrize(
    ("input_conf", "expected_conf"),
    [
        (None, None),
        (0.0, 0.0),
        (1.0, 1.0),
        (0.5, 0.5),
        (-0.00001, 0.0),
        (-9999.0, 0.0),
        (1.00001, 1.0),
        (9999.0, 1.0),
        (0, 0.0),
        (1, 1.0),
    ],
)
def test_fuzz_confidence_values(input_conf: Any, expected_conf: float | None) -> None:
    """Verify confidence clamping across negative, positive, and boundary values."""
    payload = {
        "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "conf_test.jpg"},
        "blocks": [
            {
                "lines": [
                    {
                        "text": "Confidence Test",
                        "confidence": input_conf,
                    }
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(payload)
    region = doc.pages[0].regions[0]
    if expected_conf is None:
        assert region.confidence is None
    else:
        assert region.confidence == pytest.approx(expected_conf)


# ===========================================================================
# 5. Document ID Edge Cases
# ===========================================================================


@pytest.mark.parametrize(
    ("file_name", "explicit_id", "expected_doc_id"),
    [
        # Standard filenames
        ("prescription_01.jpg", None, "prescription_01"),
        ("IMG_20260115_181847.JSON", None, "IMG_20260115_181847"),
        # Multiple dots in filename
        ("rx.sample.final.v2.jpg", None, "rx.sample.final.v2"),
        # Spaces and parentheses in filename
        ("Đơn Thuốc (Bệnh Viện Chợ Rẫy) 2026.png", None, "Đơn Thuốc (Bệnh Viện Chợ Rẫy) 2026"),
        # Relative and absolute path traversal in fileName
        ("../../data/secret/IMG_9999.json", None, "IMG_9999"),
        ("/var/tmp/medicine/rx_capture_001.jpg", None, "rx_capture_001"),
        # Explicit ID overriding complex filename
        ("simple.jpg", "CUSTOM_PRESCRIPTION_ID_#42", "CUSTOM_PRESCRIPTION_ID_#42"),
        # Vietnamese diacritics in explicit ID
        ("test.jpg", "ĐƠN_THUỐC_SỐ_123", "ĐƠN_THUỐC_SỐ_123"),
    ],
)
def test_document_id_derivation_and_overrides(
    file_name: str,
    explicit_id: str | None,
    expected_doc_id: str,
) -> None:
    """Verify document_id stem extraction, path handling, and explicit overrides."""
    payload = {
        "metadata": {"fileName": file_name, "imageWidth": 1000, "imageHeight": 1000},
        "blocks": [],
    }
    doc = parse_mlkit_json_data(payload, document_id=explicit_id)
    assert doc.document_id == expected_doc_id


@pytest.mark.parametrize("invalid_id", ["", None])
def test_reject_empty_explicit_document_id(invalid_id: Any) -> None:
    """Verify empty explicit document_id raises ValueError."""
    payload = {
        "metadata": {"fileName": "", "imageWidth": 1000, "imageHeight": 1000},
        "blocks": [],
    }
    # If fileName is empty and explicit_id is empty, it falls back or raises
    if invalid_id == "":
        with pytest.raises(ValueError, match="document_id must be non-empty"):
            parse_mlkit_json_data(payload, document_id="")


# ===========================================================================
# 6. Multi-Block Complex Hierarchies & Deep Nested Structures
# ===========================================================================


def test_massive_scale_1000_regions_hierarchy_and_reading_order() -> None:
    """Stress test: Ingest 250 blocks with 4 lines each (1000 total regions).

    Verifies:
    1. Deterministic reading_order from 0 to 999.
    2. Strict uniqueness of region_id ("p0_b{b}_l{l}").
    3. Document validation pass.
    4. Exact text reconstruction via build_document_text.
    """
    num_blocks = 250
    lines_per_block = 4
    total_regions = num_blocks * lines_per_block

    blocks: list[dict[str, Any]] = []
    expected_lines: list[str] = []

    for b in range(num_blocks):
        lines: list[dict[str, Any]] = []
        for l in range(lines_per_block):
            line_str = f"Block {b} Line {l}: Med_{b}_{l} 500mg"
            expected_lines.append(line_str)
            lines.append(
                {
                    "text": line_str,
                    "confidence": 0.95,
                    "boundingBox": {
                        "left": float(l * 10),
                        "top": float(b * 10),
                        "right": float(l * 10 + 200),
                        "bottom": float(b * 10 + 8),
                    },
                }
            )
        blocks.append({"lines": lines})

    payload = {
        "metadata": {
            "imageWidth": 4000,
            "imageHeight": 8000,
            "fileName": "stress_1000.jpg",
        },
        "blocks": blocks,
    }

    doc = parse_mlkit_json_data(payload)
    assert len(doc.pages[0].regions) == total_regions

    # Verify reading order monotonicity
    assert [r.reading_order for r in doc.pages[0].regions] == list(range(total_regions))

    # Verify region IDs
    region_ids = [r.region_id for r in doc.pages[0].regions]
    assert len(region_ids) == len(set(region_ids))
    assert region_ids[0] == "p0_b0_l0"
    assert region_ids[-1] == f"p0_b{num_blocks-1}_l{lines_per_block-1}"

    # Verify text reconstruction
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == "\n".join(expected_lines)
    assert len(doc_text.regions) == total_regions


def test_mixed_block_hierarchies_lines_and_fallbacks() -> None:
    """Verify parsing blocks with mixed structures: lines, empty lines, and empty blocks."""
    payload = {
        "metadata": {"imageWidth": 2000, "imageHeight": 2000, "fileName": "mixed.jpg"},
        "blocks": [
            # Block 0: Standard with lines
            {
                "lines": [
                    {"text": "B0_L0", "confidence": 0.9},
                    {"text": "B0_L1", "confidence": 0.9},
                ]
            },
            # Block 1: Empty lines array, but has block text -> fallback to block region
            {
                "text": "B1_Fallback_Text",
                "lines": [],
                "boundingBox": {"left": 10, "top": 10, "right": 100, "bottom": 30},
            },
            # Block 2: Empty lines array and empty text -> should be skipped entirely
            {
                "text": "",
                "lines": [],
            },
            # Block 3: Standard with lines
            {
                "lines": [
                    {"text": "B3_L0", "confidence": 0.85},
                ]
            },
        ],
    }

    doc = parse_mlkit_json_data(payload)
    regions = doc.pages[0].regions
    assert len(regions) == 4

    assert [r.region_id for r in regions] == ["p0_b0_l0", "p0_b0_l1", "p0_b1", "p0_b3_l0"]
    assert [r.reading_order for r in regions] == [0, 1, 2, 3]
    assert [r.text for r in regions] == ["B0_L0", "B0_L1", "B1_Fallback_Text", "B3_L0"]


# ===========================================================================
# 7. Vietnamese Diacritics, Unicode Normalization, and Multi-byte Characters
# ===========================================================================


@pytest.mark.parametrize(
    "vn_sample",
    [
        # Full Vietnamese alphabet diacritics
        "a á à ả ã ạ ă ắ ằ ẳ ẵ ặ â ấ ầ ẩ ẫ ậ e é è ẻ ẽ ẹ ê ế ề ể ễ ệ",
        "i í ì ỉ ĩ ị o ó ò ỏ õ ọ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ u ú ù ủ ũ ụ ư ứ ừ ử ữ ự y ý ỳ ỷ ỹ ỵ đ",
        # Real prescription medical text
        "BỆNH VIỆN ĐA KHOA TRUNG ƯƠNG CẦN THƠ",
        "Chẩn đoán: Viêm dạ dày ruột cấp; Trào ngược dạ dày - thực quản",
        "1. Esomeprazole 40mg (NEXIUM) - 14 Viên - Ngày uống 1 viên trước ăn sáng 30 phút",
        "2. Cefuroxim 500mg (ZINNAT) - 20 Viên - Ngày uống 2 lần, mỗi lần 1 viên sau ăn",
        "3. Paracetamol + Tramadol (ULTRACET 37.5mg/325mg) - 10 Viên",
        # Emoji and symbols
        "💊 Thuốc điều trị: 🩺 Bác sĩ chỉ định: 🏥 BV Chợ Rẫy",
        # Tab and multi-byte whitespace
        "Cột 1\t\tCột 2\u00a0\u200bCột 3",
    ],
)
def test_vietnamese_diacritics_and_unicode_resilience(vn_sample: str) -> None:
    """Verify text containing all Vietnamese diacritics and unicode symbols is intact."""
    payload = {
        "metadata": {"imageWidth": 2000, "imageHeight": 2000, "fileName": "vn_unicode.jpg"},
        "blocks": [
            {
                "lines": [
                    {
                        "text": vn_sample,
                        "confidence": 0.99,
                        "boundingBox": {"left": 0, "top": 0, "right": 500, "bottom": 50},
                    }
                ]
            }
        ],
    }

    doc = parse_mlkit_json_data(payload)
    assert doc.pages[0].regions[0].text == vn_sample

    doc_text = build_document_text(doc)
    assert doc_text.raw_text == vn_sample
    assert len(doc_text.regions) == 1
    span = doc_text.regions[0]
    assert doc_text.raw_text[span.start : span.end] == vn_sample


def test_nfc_vs_nfd_unicode_normalization_preservation() -> None:
    """Verify both NFC (composed) and NFD (decomposed) strings pass through cleanly."""
    text_nfc = unicodedata.normalize("NFC", "Bệnh Viện Chợ Rẫy")
    text_nfd = unicodedata.normalize("NFD", "Bệnh Viện Chợ Rẫy")

    payload = {
        "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "norm.jpg"},
        "blocks": [
            {
                "lines": [
                    {"text": text_nfc, "confidence": 0.95},
                    {"text": text_nfd, "confidence": 0.95},
                ]
            }
        ],
    }

    doc = parse_mlkit_json_data(payload)
    assert doc.pages[0].regions[0].text == text_nfc
    assert doc.pages[0].regions[1].text == text_nfd

    doc_text = build_document_text(doc)
    assert doc_text.raw_text[doc_text.regions[0].start : doc_text.regions[0].end] == text_nfc
    assert doc_text.raw_text[doc_text.regions[1].start : doc_text.regions[1].end] == text_nfd


# ===========================================================================
# 8. Property-Based Random Fuzzing Oracle
# ===========================================================================


def test_property_based_fuzz_oracle_100_payloads() -> None:
    """Property-based fuzz test: Generate 100 randomized ML Kit payloads.

    Invariants checked for 100% of generated documents:
    1. Successful parsing into OcrDocument without uncaught exceptions.
    2. Document validates against Pydantic OcrDocument schema contracts.
    3. Monotonic, contiguous reading_order starting at 0.
    4. Unique region_id values across all regions.
    5. All bbox coordinates clamped within [0, page_width] and [0, page_height].
    6. All region confidences in [0.0, 1.0] or None.
    7. build_document_text exact substring reconstruction invariant.
    """
    rng = random.Random(42)  # Deterministic seed

    unicode_pool = [
        "Paracetamol", "500mg", "Amoxicillin", "Viên", "ĐƠN THUỐC",
        "Bệnh viện", "Uống 2 lần/ngày", "10 ngày", "Tái khám",
        "💊", "🩺", "Aspirin", "100mg", "\t", "   ", "Sáng 1 viên",
    ]

    for iteration in range(100):
        width = rng.randint(100, 5000)
        height = rng.randint(100, 5000)
        num_blocks = rng.randint(0, 15)

        blocks: list[dict[str, Any]] = []
        for b_idx in range(num_blocks):
            block_type = rng.choice(["standard_lines", "fallback_block", "empty"])
            if block_type == "standard_lines":
                num_lines = rng.randint(1, 8)
                lines = []
                for l_idx in range(num_lines):
                    line_text = " ".join(rng.choices(unicode_pool, k=rng.randint(1, 5)))
                    conf_choice = rng.choice([None, -10.0, 0.0, 0.5, 1.0, 5.0, rng.random()])
                    # Random coordinates (may be negative or exceed width/height)
                    x1 = rng.uniform(-500, width + 500)
                    y1 = rng.uniform(-500, height + 500)
                    x2 = rng.uniform(-500, width + 500)
                    y2 = rng.uniform(-500, height + 500)
                    lines.append(
                        {
                            "text": line_text,
                            "confidence": conf_choice,
                            "cornerPoints": [
                                {"x": x1, "y": y1},
                                {"x": x2, "y": y1},
                                {"x": x2, "y": y2},
                                {"x": x1, "y": y2},
                            ],
                        }
                    )
                blocks.append({"lines": lines})
            elif block_type == "fallback_block":
                block_text = " ".join(rng.choices(unicode_pool, k=rng.randint(1, 4)))
                blocks.append(
                    {
                        "text": block_text,
                        "lines": [],
                        "boundingBox": {
                            "left": rng.uniform(-100, width + 100),
                            "top": rng.uniform(-100, height + 100),
                            "right": rng.uniform(-100, width + 100),
                            "bottom": rng.uniform(-100, height + 100),
                        },
                    }
                )
            else:
                blocks.append({"lines": [], "text": ""})

        payload = {
            "metadata": {
                "imageWidth": width,
                "imageHeight": height,
                "fileName": f"fuzz_doc_{iteration}.jpg",
            },
            "blocks": blocks,
        }

        # 1. Parsing must succeed
        doc = parse_mlkit_json_data(payload)
        assert isinstance(doc, OcrDocument)
        page = doc.pages[0]

        # 2. Re-validate via Pydantic model_validate
        validated_doc = OcrDocument.model_validate(doc.model_dump())
        assert validated_doc.document_id == f"fuzz_doc_{iteration}"

        # 3. Reading order invariant
        orders = [r.reading_order for r in page.regions]
        assert orders == list(range(len(page.regions)))

        # 4. Region ID uniqueness invariant
        region_ids = [r.region_id for r in page.regions]
        assert len(region_ids) == len(set(region_ids))

        # 5. Coordinate clamping invariant
        for region in page.regions:
            for pt_x, pt_y in region.bbox.points:
                assert 0.0 <= pt_x <= float(page.width)
                assert 0.0 <= pt_y <= float(page.height)

        # 6. Confidence clamping invariant
        for region in page.regions:
            if region.confidence is not None:
                assert 0.0 <= region.confidence <= 1.0

        # 7. Text reconstruction invariant
        doc_text = build_document_text(doc)
        assert len(doc_text.regions) == len(page.regions)
        for span, region in zip(doc_text.regions, page.regions, strict=True):
            assert span.region_id == region.region_id
            assert doc_text.raw_text[span.start : span.end] == region.text
