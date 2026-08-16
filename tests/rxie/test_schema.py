import pytest
from pydantic import ValidationError

from rxie.schemas import OcrDocument
from rxie.text import build_document_text


def payload():
    return {
        "schema_version": "rxie.ocr.v1",
        "document_id": "rx-1",
        "ocr_engine": {"name": "mobile-ocr", "version": "1.2.0"},
        "pages": [
            {
                "width": 200,
                "height": 100,
                "page_index": 0,
                "regions": [
                    {
                        "region_id": "r2",
                        "text": "500 mg",
                        "confidence": None,
                        "reading_order": 1,
                        "bbox": {
                            "points": [[0, 20], [50, 20], [50, 40], [0, 40]]
                        },
                    },
                    {
                        "region_id": "r1",
                        "text": "Paracetamol",
                        "confidence": 0.9,
                        "reading_order": 0,
                        "bbox": {
                            "points": [[0, 0], [100, 0], [100, 20], [0, 20]]
                        },
                    },
                ],
            }
        ],
    }


def test_builds_deterministic_raw_text_and_offsets():
    text = build_document_text(OcrDocument.model_validate(payload()))

    assert text.raw_text == "Paracetamol\n500 mg"
    assert [(span.region_id, span.start, span.end) for span in text.regions] == [
        ("r1", 0, 11),
        ("r2", 12, 18),
    ]
    assert text.source_regions(6, 15) == ["r1", "r2"]


def test_rejects_duplicate_region_ids():
    value = payload()
    value["pages"][0]["regions"][1]["region_id"] = "r2"

    with pytest.raises(ValidationError, match="region_id must be unique"):
        OcrDocument.model_validate(value)


def test_rejects_bbox_outside_page():
    value = payload()
    value["pages"][0]["regions"][0]["bbox"]["points"][1][0] = 201

    with pytest.raises(ValidationError, match="within page dimensions"):
        OcrDocument.model_validate(value)
