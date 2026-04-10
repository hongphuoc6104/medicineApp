"""Phase B tests for dose-centric reference matcher flow."""

from __future__ import annotations

import numpy as np

from core.phase_b.s2_match.reference_matcher import ReferenceMatcher


def _make_image(seed: int, size: int = 96) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(size, size, 3), dtype=np.uint8)


def test_reference_matcher_returns_uncertain_when_similarity_not_strong():
    matcher = ReferenceMatcher(assigned_threshold=0.99, uncertain_threshold=0.5)
    image = _make_image(1)

    detections = [{"bbox": [0, 0, 96, 96], "score": 0.92, "label": 1}]
    expected = [{"planId": "plan-a", "drugName": "Paracetamol", "pillsPerDose": 1}]
    references = [
        {
            "planId": "plan-a",
            "drugName": "Paracetamol",
            "images": [{"imageBase64": ""}],
        }
    ]

    result = matcher.verify(image, detections, expected_medications=expected, reference_profiles=references)

    assert result["detections"][0]["status"] in ("uncertain", "unknown")
    assert "summary" in result


def test_reference_matcher_detects_missing_reference_coverage():
    matcher = ReferenceMatcher()
    image = _make_image(2)
    detections = [{"bbox": [0, 0, 48, 48], "score": 0.88, "label": 1}]

    expected = [
        {"planId": "plan-a", "drugName": "A", "pillsPerDose": 1},
        {"planId": "plan-b", "drugName": "B", "pillsPerDose": 1},
    ]
    references = [
        {
            "planId": "plan-a",
            "drugName": "A",
            "images": [{"imagePath": "/tmp/not-exists.jpg"}],
        }
    ]

    result = matcher.verify(image, detections, expected_medications=expected, reference_profiles=references)

    coverage = result["referenceCoverage"]
    assert coverage["totalExpected"] == 2
    assert coverage["withoutReference"] >= 1
    assert "B" in coverage["missingDrugNames"]


def test_reference_matcher_counts_extra_when_assigned_exceeds_expected():
    matcher = ReferenceMatcher(assigned_threshold=0.0, uncertain_threshold=0.0)
    image = _make_image(3)

    detections = [
        {"bbox": [0, 0, 40, 40], "score": 0.9, "label": 1},
        {"bbox": [41, 0, 80, 40], "score": 0.88, "label": 1},
    ]
    expected = [{"planId": "plan-a", "drugName": "A", "pillsPerDose": 1}]

    # Use same image as reference through temp file-free path via base64 invalid,
    # then fallback to no refs means unknown. For deterministic "assigned",
    # patch bank by passing valid decoded image from helper.
    emb_img = _make_image(3)
    matcher._build_reference_bank = lambda *_args, **_kwargs: {
        "plan-a": [matcher._build_embedding(emb_img)]
    }

    result = matcher.verify(image, detections, expected_medications=expected, reference_profiles=[])

    assert result["summary"]["extra"] >= 1


def test_reference_matcher_uses_metadata_to_rerank_similar_candidates():
    matcher = ReferenceMatcher(assigned_threshold=0.0, uncertain_threshold=0.0)
    image = np.zeros((96, 96, 3), dtype=np.uint8)
    image[:, :] = (0, 0, 255)  # red pill-like crop in BGR

    detections = [{"bbox": [0, 0, 96, 96], "score": 0.95, "label": 1}]
    expected = [
        {
            "planId": "plan-red",
            "drugName": "Thuốc đỏ",
            "pillsPerDose": 1,
            "metadata": {
                "dosageForm": "Viên nén",
                "visual": {"colors": ["red"], "shapeText": "round"},
            },
        },
        {
            "planId": "plan-white",
            "drugName": "Thuốc trắng",
            "pillsPerDose": 1,
            "metadata": {
                "dosageForm": "Viên nang",
                "visual": {"colors": ["white"], "shapeText": "capsule"},
            },
        },
    ]

    emb = matcher._build_embedding(image)
    matcher._build_reference_bank = lambda *_args, **_kwargs: {
        "plan-red": [emb],
        "plan-white": [emb],
    }

    result = matcher.verify(image, detections, expected_medications=expected, reference_profiles=[])

    top = result["detections"][0]["suggestions"][0]
    assert top["planId"] == "plan-red"
    assert top["metadataAdjustment"] > 0
