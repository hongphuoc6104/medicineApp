"""Regression tests for unmatched Phase A evaluator predictions."""

from scripts.tests.test_phase_a_eval_metrics import evaluate_row, resolve_predictions


ALIASES = [
    ("paracetamol", "paracetamol"),
    ("paracetamol", "panadol"),
]
IMAGE_ROW = {
    "image_id": "image-1",
    "group_id": "group-1",
    "relative_path": "data/input/image-1.jpg",
}


def test_unknown_prediction_is_explicit_fp_and_breaks_exact_match() -> None:
    result = {
        "medications": [
            {"ocr_text": "Paracetamol 500 mg"},
            {"ocr_text": "Thuoc la 10 mg"},
        ]
    }

    row = evaluate_row(
        "proposed",
        IMAGE_ROW,
        result,
        0.1,
        {"paracetamol"},
        ALIASES,
    )

    assert row.pred_ids == ["paracetamol"]
    assert row.pred_count == 2
    assert (row.tp, row.fp, row.fn) == (1, 1, 0)
    assert row.exact_match is False
    assert row.unmatched_predictions == [
        {
            "raw_text": "Thuoc la 10 mg",
            "normalized_text": "thuoc la 10 mg",
        }
    ]
    assert row.prediction_resolutions == [
        {
            "raw_text": "Paracetamol 500 mg",
            "normalized_text": "paracetamol 500 mg",
            "status": "matched",
            "canonical_id": "paracetamol",
        },
        {
            "raw_text": "Thuoc la 10 mg",
            "normalized_text": "thuoc la 10 mg",
            "status": "unmatched",
            "canonical_id": None,
        },
    ]


def test_duplicate_unknown_normalized_text_has_set_semantics() -> None:
    predictions = ["Thuốc lạ!", "  THUOC LA  ", "Thuốc khác"]

    resolutions = resolve_predictions(predictions, ALIASES)
    row = evaluate_row(
        "proposed",
        IMAGE_ROW,
        {"medications": [{"ocr_text": text} for text in predictions]},
        0.1,
        set(),
        ALIASES,
    )

    assert len(resolutions) == 3
    assert all(record["status"] == "unmatched" for record in resolutions)
    assert row.pred_count == 2
    assert row.fp == 2
    assert row.unmatched_predictions == [
        {"raw_text": "Thuốc khác", "normalized_text": "thuoc khac"},
        {"raw_text": "Thuốc lạ!", "normalized_text": "thuoc la"},
    ]


def test_empty_predictions_are_ignored_but_nonempty_normalized_empty_is_unmatched() -> None:
    resolutions = resolve_predictions(["", "   ", "!!!"], ALIASES)

    assert resolutions == [
        {
            "raw_text": "!!!",
            "normalized_text": "",
            "status": "unmatched",
            "canonical_id": None,
        }
    ]

    row = evaluate_row(
        "proposed",
        IMAGE_ROW,
        {"medications": [{"ocr_text": text} for text in ["", "   ", "!!!"]]},
        0.1,
        set(),
        ALIASES,
    )
    assert row.pred_texts == ["!!!"]
    assert row.pred_count == 1
    assert row.fp == 1


def test_duplicate_aliases_count_as_one_canonical_prediction() -> None:
    row = evaluate_row(
        "proposed",
        IMAGE_ROW,
        {"medications": [{"ocr_text": "Panadol"}, {"ocr_text": "Paracetamol"}]},
        0.1,
        {"paracetamol"},
        ALIASES,
    )

    assert len(row.prediction_resolutions) == 2
    assert row.pred_count == 1
    assert row.fp == 0
    assert row.exact_match is True
