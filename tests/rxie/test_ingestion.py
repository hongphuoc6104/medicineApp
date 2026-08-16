"""Unit and integration tests for ML Kit OCR ingestion pipeline.

Milestone M0 / A0.
"""

from __future__ import annotations

import json
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

# ---------------------------------------------------------------------------
# Fixtures and Sample Payloads
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_mlkit_payload() -> dict[str, Any]:
    """Standard multi-block, multi-line ML Kit OCR JSON dictionary."""
    return {
        "metadata": {
            "fileName": "IMG_20260115_181847.jpg",
            "filePath": (
                "/data/data/com.medicineapp.medicine_app/files/input/Data/"
                "IMG_20260115_181847.jpg"
            ),
            "fileSizeBytes": 5670841,
            "imageWidth": 3000,
            "imageHeight": 4000,
            "processedAt": "2026-08-15T17:11:51.643386Z",
            "recognizerScript": "latin",
        },
        "fullText": "ĐƠN THUỐC\nParacetamol 500mg\nNgày uống 2 viên",
        "blocks": [
            {
                "text": "ĐƠN THUỐC",
                "boundingBox": {
                    "left": 1000.0,
                    "top": 200.0,
                    "right": 2000.0,
                    "bottom": 300.0,
                    "width": 1000.0,
                    "height": 100.0,
                },
                "cornerPoints": [
                    {"x": 1000, "y": 200},
                    {"x": 2000, "y": 200},
                    {"x": 2000, "y": 300},
                    {"x": 1000, "y": 300},
                ],
                "lines": [
                    {
                        "text": "ĐƠN THUỐC",
                        "boundingBox": {
                            "left": 1000.0,
                            "top": 200.0,
                            "right": 2000.0,
                            "bottom": 300.0,
                            "width": 1000.0,
                            "height": 100.0,
                        },
                        "confidence": 0.95,
                        "cornerPoints": [
                            {"x": 1000, "y": 200},
                            {"x": 2000, "y": 200},
                            {"x": 2000, "y": 300},
                            {"x": 1000, "y": 300},
                        ],
                    }
                ],
            },
            {
                "text": "Paracetamol 500mg\nNgày uống 2 viên",
                "boundingBox": {
                    "left": 500.0,
                    "top": 600.0,
                    "right": 2500.0,
                    "bottom": 900.0,
                    "width": 2000.0,
                    "height": 300.0,
                },
                "cornerPoints": [
                    {"x": 500, "y": 600},
                    {"x": 2500, "y": 600},
                    {"x": 2500, "y": 900},
                    {"x": 500, "y": 900},
                ],
                "lines": [
                    {
                        "text": "Paracetamol 500mg",
                        "boundingBox": {
                            "left": 500.0,
                            "top": 600.0,
                            "right": 2200.0,
                            "bottom": 720.0,
                            "width": 1700.0,
                            "height": 120.0,
                        },
                        "confidence": 0.98,
                        "cornerPoints": [
                            {"x": 500, "y": 600},
                            {"x": 2200, "y": 600},
                            {"x": 2200, "y": 720},
                            {"x": 500, "y": 720},
                        ],
                    },
                    {
                        "text": "Ngày uống 2 viên",
                        "boundingBox": {
                            "left": 500.0,
                            "top": 750.0,
                            "right": 1800.0,
                            "bottom": 870.0,
                            "width": 1300.0,
                            "height": 120.0,
                        },
                        "confidence": 0.92,
                        "cornerPoints": [
                            {"x": 500, "y": 750},
                            {"x": 1800, "y": 750},
                            {"x": 1800, "y": 870},
                            {"x": 500, "y": 870},
                        ],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def empty_mlkit_payload() -> dict[str, Any]:
    """Empty capture dictionary matching captures with 0 detected text blocks."""
    return {
        "metadata": {
            "fileName": "IMG_20260209_003018.jpg",
            "filePath": (
                "/data/data/com.medicineapp.medicine_app/files/input/Data/"
                "IMG_20260209_003018.jpg"
            ),
            "fileSizeBytes": 12345,
            "imageWidth": 3000,
            "imageHeight": 4000,
            "processedAt": "2026-08-15T17:11:51.000000Z",
            "recognizerScript": "latin",
        },
        "fullText": "",
        "blocks": [],
    }


# ---------------------------------------------------------------------------
# Unit Tests: Helper Functions & Clamping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("val", "min_v", "max_v", "expected"),
    [
        (-10.5, 0.0, 100.0, 0.0),
        (0.0, 0.0, 100.0, 0.0),
        (50.0, 0.0, 100.0, 50.0),
        (100.0, 0.0, 100.0, 100.0),
        (120.0, 0.0, 100.0, 100.0),
        (0.85, 0.0, 1.0, 0.85),
        (-0.05, 0.0, 1.0, 0.0),
        (1.05, 0.0, 1.0, 1.0),
    ],
)
def test_clamp_boundary_values(
    val: float, min_v: float, max_v: float, expected: float
) -> None:
    """Verify _clamp strictly bounds coordinates and confidences."""
    assert _clamp(val, min_v, max_v) == pytest.approx(expected)


def test_extract_bbox_with_4_corner_points() -> None:
    """Verify _extract_bbox correctly parses and clamps 4 corner points."""
    item = {
        "cornerPoints": [
            {"x": -5, "y": 10},
            {"x": 3005, "y": 10},
            {"x": 3005, "y": 4005},
            {"x": -5, "y": 4005},
        ]
    }
    bbox = _extract_bbox(item, width=3000.0, height=4000.0)
    assert isinstance(bbox, BoundingBox)
    assert bbox.points == (
        (0.0, 10.0),
        (3000.0, 10.0),
        (3000.0, 4000.0),
        (0.0, 4000.0),
    )


def test_extract_bbox_fallback_missing_corner_points() -> None:
    """Verify _extract_bbox fallback when cornerPoints is missing."""
    item = {
        "boundingBox": {
            "left": -10.0,
            "top": -5.0,
            "right": 1050.0,
            "bottom": 550.0,
        }
    }
    bbox = _extract_bbox(item, width=1000.0, height=500.0)
    assert bbox.points == (
        (0.0, 0.0),
        (1000.0, 0.0),
        (1000.0, 500.0),
        (0.0, 500.0),
    )


@pytest.mark.parametrize(
    "corner_points",
    [
        [],
        [{"x": 10, "y": 10}],
        [{"x": 10, "y": 10}, {"x": 20, "y": 20}, {"x": 30, "y": 30}],
        [
            {"x": 1, "y": 1},
            {"x": 2, "y": 2},
            {"x": 3, "y": 3},
            {"x": 4, "y": 4},
            {"x": 5, "y": 5},
        ],
    ],
)
def test_extract_bbox_fallback_non_4_corner_points(
    corner_points: list[dict[str, Any]],
) -> None:
    """Verify _extract_bbox fallback when cornerPoints has != 4 points."""
    item = {
        "cornerPoints": corner_points,
        "boundingBox": {"left": 10.0, "top": 20.0, "right": 100.0, "bottom": 200.0},
    }
    bbox = _extract_bbox(item, width=500.0, height=500.0)
    assert bbox.points == (
        (10.0, 20.0),
        (100.0, 20.0),
        (100.0, 200.0),
        (10.0, 200.0),
    )


def test_extract_bbox_degenerate_empty_fallback() -> None:
    """Verify _extract_bbox produces zero box when bbox data is absent."""
    bbox = _extract_bbox({}, width=1000.0, height=1000.0)
    assert bbox.points == (
        (0.0, 0.0),
        (0.0, 0.0),
        (0.0, 0.0),
        (0.0, 0.0),
    )


# ---------------------------------------------------------------------------
# Unit Tests: parse_mlkit_json_data & OcrDocument Contract
# ---------------------------------------------------------------------------


def test_parse_standard_mlkit_json_happy_path(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify parsing standard ML Kit JSON into a valid canonical OcrDocument."""
    doc = parse_mlkit_json_data(sample_mlkit_payload)

    assert isinstance(doc, OcrDocument)
    assert doc.schema_version == "rxie.ocr.v1"
    assert doc.document_id == "IMG_20260115_181847"
    assert doc.ocr_engine.name == DEFAULT_OCR_ENGINE_NAME
    assert doc.ocr_engine.version == DEFAULT_OCR_ENGINE_VERSION

    assert len(doc.pages) == 1
    page = doc.pages[0]
    assert page.page_index == 0
    assert page.width == 3000
    assert page.height == 4000
    assert len(page.regions) == 3

    # Check region IDs and sequential reading order
    assert [r.region_id for r in page.regions] == ["p0_b0_l0", "p0_b1_l0", "p0_b1_l1"]
    assert [r.reading_order for r in page.regions] == [0, 1, 2]
    assert [r.text for r in page.regions] == [
        "ĐƠN THUỐC",
        "Paracetamol 500mg",
        "Ngày uống 2 viên",
    ]
    assert page.regions[0].confidence == pytest.approx(0.95)
    assert page.regions[1].confidence == pytest.approx(0.98)
    assert page.regions[2].confidence == pytest.approx(0.92)


def test_parse_document_id_explicit_argument(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify explicit document_id overrides metadata.fileName."""
    doc = parse_mlkit_json_data(sample_mlkit_payload, document_id="CUSTOM_DOC_999")
    assert doc.document_id == "CUSTOM_DOC_999"


def test_parse_document_id_from_metadata_filename(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify document_id is derived from metadata.fileName stem."""
    sample_mlkit_payload["metadata"]["fileName"] = "prescription_sample_01.json"
    doc = parse_mlkit_json_data(sample_mlkit_payload)
    assert doc.document_id == "prescription_sample_01"


def test_parse_document_id_fallback_when_missing(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify fallback document_id when metadata has no fileName."""
    sample_mlkit_payload["metadata"].pop("fileName", None)
    doc = parse_mlkit_json_data(sample_mlkit_payload)
    assert doc.document_id == "doc_unknown"


def test_parse_coordinate_clamping_negative_and_overflow(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify coordinates outside page bounds are clamped and pass validation."""
    # Set coordinates well outside bounds (-25 and 3050 for width=3000, height=4000)
    sample_mlkit_payload["blocks"][0]["lines"][0]["cornerPoints"] = [
        {"x": -25, "y": -10},
        {"x": 3050, "y": -10},
        {"x": 3050, "y": 4050},
        {"x": -25, "y": 4050},
    ]
    doc = parse_mlkit_json_data(sample_mlkit_payload)
    clamped_pts = doc.pages[0].regions[0].bbox.points
    assert clamped_pts == (
        (0.0, 0.0),
        (3000.0, 0.0),
        (3000.0, 4000.0),
        (0.0, 4000.0),
    )


def test_parse_confidence_handling(sample_mlkit_payload: dict[str, Any]) -> None:
    """Verify confidence None preservation and boundary clamping."""
    sample_mlkit_payload["blocks"][0]["lines"][0]["confidence"] = None
    sample_mlkit_payload["blocks"][1]["lines"][0]["confidence"] = 1.05
    sample_mlkit_payload["blocks"][1]["lines"][1]["confidence"] = -0.05

    doc = parse_mlkit_json_data(sample_mlkit_payload)
    assert doc.pages[0].regions[0].confidence is None
    assert doc.pages[0].regions[1].confidence == pytest.approx(1.0)
    assert doc.pages[0].regions[2].confidence == pytest.approx(0.0)


def test_parse_empty_ocr_capture_zero_blocks(
    empty_mlkit_payload: dict[str, Any],
) -> None:
    """Verify empty capture produces valid OcrDocument with empty regions."""
    doc = parse_mlkit_json_data(empty_mlkit_payload)
    assert isinstance(doc, OcrDocument)
    assert doc.document_id == "IMG_20260209_003018"
    assert len(doc.pages) == 1
    assert doc.pages[0].regions == []

    # Verify text reconstruction produces empty document
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == ""
    assert doc_text.regions == ()


def test_parse_block_with_zero_lines() -> None:
    """Verify block with empty lines array falls back to block-level region."""
    payload = {
        "metadata": {
            "imageWidth": 1000,
            "imageHeight": 1000,
            "fileName": "block_fallback.jpg",
        },
        "fullText": "Standalone Block Text",
        "blocks": [
            {
                "text": "Standalone Block Text",
                "boundingBox": {
                    "left": 10.0,
                    "top": 10.0,
                    "right": 200.0,
                    "bottom": 50.0,
                },
                "lines": [],
            }
        ],
    }
    doc = parse_mlkit_json_data(payload)
    assert len(doc.pages[0].regions) == 1
    region = doc.pages[0].regions[0]
    assert region.region_id == "p0_b0"
    assert region.text == "Standalone Block Text"
    assert region.reading_order == 0


def test_parse_vietnamese_unicode_preserved() -> None:
    """Verify complex Vietnamese medical text and diacritics are preserved intact."""
    vn_text = "Huyết áp vô căn; Thoái hóa khớp gối; Rối loạn giấc ngủ"
    payload = {
        "metadata": {
            "imageWidth": 2000,
            "imageHeight": 2000,
            "fileName": "vn_test.jpg",
        },
        "fullText": vn_text,
        "blocks": [
            {
                "lines": [
                    {
                        "text": vn_text,
                        "boundingBox": {
                            "left": 10,
                            "top": 10,
                            "right": 500,
                            "bottom": 50,
                        },
                        "confidence": 0.99,
                    }
                ]
            }
        ],
    }
    doc = parse_mlkit_json_data(payload)
    assert doc.pages[0].regions[0].text == vn_text
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == vn_text


# ---------------------------------------------------------------------------
# Unit Tests: File Ingestion (load_mlkit_ocr_document)
# ---------------------------------------------------------------------------


def test_load_mlkit_ocr_document_from_path(
    tmp_path: Path, sample_mlkit_payload: dict[str, Any]
) -> None:
    """Verify loading from Path and str arguments on disk."""
    json_path = tmp_path / "IMG_20260115_181847.json"
    json_path.write_text(json.dumps(sample_mlkit_payload), encoding="utf-8")

    # Load via Path
    doc_path = load_mlkit_ocr_document(json_path)
    assert doc_path.document_id == "IMG_20260115_181847"
    assert len(doc_path.pages[0].regions) == 3

    # Load via string
    doc_str = load_mlkit_ocr_document(str(json_path))
    assert doc_str.document_id == "IMG_20260115_181847"

    # Explicit override
    doc_explicit = load_mlkit_ocr_document(json_path, document_id="OVERRIDDEN_ID")
    assert doc_explicit.document_id == "OVERRIDDEN_ID"


def test_load_mlkit_ocr_document_file_not_found() -> None:
    """Verify FileNotFoundError when target file does not exist."""
    with pytest.raises(FileNotFoundError, match="not found"):
        load_mlkit_ocr_document("non_existent_ocr_capture_12345.json")


def test_load_mlkit_ocr_document_invalid_json(tmp_path: Path) -> None:
    """Verify error raised when file contains corrupt JSON."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{malformed: json...", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_mlkit_ocr_document(corrupt_file)


# ---------------------------------------------------------------------------
# Unit Tests: Text Offset Reconstruction via build_document_text
# ---------------------------------------------------------------------------


def test_build_document_text_reconstruction_and_offsets(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify build_document_text produces exact raw_text and slice offsets."""
    doc = parse_mlkit_json_data(sample_mlkit_payload)
    doc_text = build_document_text(doc)

    assert doc_text.raw_text == sample_mlkit_payload["fullText"]
    assert len(doc_text.regions) == 3

    # Verify character slice offsets for each region
    for span, region in zip(doc_text.regions, doc.pages[0].regions, strict=True):
        assert span.region_id == region.region_id
        assert doc_text.raw_text[span.start : span.end] == region.text

    # Verify source_regions lookup across span
    first_region_len = len("ĐƠN THUỐC")
    assert doc_text.source_regions(0, first_region_len) == ["p0_b0_l0"]
    # Span crossing boundary of region 1 and region 2
    assert doc_text.source_regions(5, first_region_len + 5) == [
        "p0_b0_l0",
        "p0_b1_l0",
    ]


def test_build_document_text_empty_document() -> None:
    """Verify empty document produces empty raw_text and empty regions."""
    doc = OcrDocument(
        schema_version="rxie.ocr.v1",
        document_id="empty_doc",
        ocr_engine=OcrEngine(
            name=DEFAULT_OCR_ENGINE_NAME,
            version=DEFAULT_OCR_ENGINE_VERSION,
        ),
        pages=[OcrPage(width=1000, height=1000, page_index=0, regions=[])],
    )
    doc_text = build_document_text(doc)
    assert doc_text.raw_text == ""
    assert doc_text.regions == ()


# ---------------------------------------------------------------------------
# Unit Tests: Negative / Validation Error Handling
# ---------------------------------------------------------------------------


def test_parse_rejects_empty_document_id(
    sample_mlkit_payload: dict[str, Any],
) -> None:
    """Verify ValueError is raised if document_id is explicitly empty."""
    with pytest.raises(ValueError, match="document_id"):
        parse_mlkit_json_data(sample_mlkit_payload, document_id="")


def test_pydantic_schema_validation_rejects_unclamped_coordinates() -> None:
    """Verify that Pydantic OcrPage enforces page dimensions strictly."""
    with pytest.raises(ValidationError, match="within page dimensions"):
        OcrPage(
            width=100,
            height=100,
            page_index=0,
            regions=[
                OcrRegion(
                    region_id="r1",
                    text="Out of bounds",
                    confidence=0.9,
                    reading_order=0,
                    bbox=BoundingBox(
                        points=((0, 0), (105, 0), (105, 50), (0, 50))
                    ),
                )
            ],
        )


# ---------------------------------------------------------------------------
# Integration Tests: Batch Ingestion across 437 Real Files (data/ocr_final/)
# ---------------------------------------------------------------------------


def test_batch_ingest_all_437_real_captures() -> None:
    """Integration Test: Parse all 437 real ML Kit captures in data/ocr_final.

    Verifies:
    1. Exactly 437 files are parsed without error.
    2. Every parsed document is a valid OcrDocument.
    3. Exactly 100% of documents match data['fullText'] via build_document_text.
    4. Reading order is strictly unique and monotonic [0, 1, 2, ...].
    5. Region IDs are strictly unique within every document.
    6. All coordinates are bounded by [0.0, page_width] and [0.0, page_height].
    7. Known empty captures produce 0 regions and empty raw_text.
    """
    ocr_dir = Path("data/ocr_final")
    if not ocr_dir.exists():
        pytest.skip("data/ocr_final directory not found")

    docs = ingest_all_mlkit_captures(ocr_dir)
    assert len(docs) == 437, f"Expected 437 ingested documents, found {len(docs)}"

    known_empty_ids = {
        "IMG_20260209_003018",
        "IMG_20260209_180838",
        "IMG_20260209_181121",
    }

    for doc_id, doc in docs.items():
        assert isinstance(doc, OcrDocument)
        assert doc.schema_version == "rxie.ocr.v1"
        assert doc.document_id == doc_id
        assert len(doc.pages) == 1

        page = doc.pages[0]
        assert page.width > 0
        assert page.height > 0
        assert page.page_index == 0

        # Check unique and monotonic reading order
        reading_orders = [r.reading_order for r in page.regions]
        assert reading_orders == list(range(len(page.regions)))

        # Check unique region IDs
        region_ids = [r.region_id for r in page.regions]
        assert len(region_ids) == len(set(region_ids))

        # Check coordinate bounds
        for region in page.regions:
            for x, y in region.bbox.points:
                assert 0.0 <= x <= float(page.width)
                assert 0.0 <= y <= float(page.height)

        # Check text reconstruction against original file fullText
        raw_file = ocr_dir / f"{doc_id}.json"
        with raw_file.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        expected_full_text = raw_data.get("fullText", "")
        doc_text = build_document_text(doc)
        assert doc_text.raw_text == expected_full_text

        # Verify known empty captures
        if doc_id in known_empty_ids:
            assert len(page.regions) == 0
            assert doc_text.raw_text == ""


def test_batch_ingest_source_dir_not_found() -> None:
    """Verify FileNotFoundError when batch ingesting non-existent directory."""
    with pytest.raises(FileNotFoundError, match="not found"):
        ingest_all_mlkit_captures("non_existent_ocr_directory_xyz")


def test_batch_ingest_empty_directory(tmp_path: Path) -> None:
    """Verify batch ingestion of an empty directory returns empty dictionary."""
    empty_dir = tmp_path / "empty_ocr"
    empty_dir.mkdir()
    docs = ingest_all_mlkit_captures(empty_dir)
    assert docs == {}
