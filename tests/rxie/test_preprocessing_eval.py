import json
import os
import tempfile
from rxie.preprocessing_eval import (
    calculate_cer,
    calculate_wer,
    compare_paired_ocr,
    edit_distance,
    evaluate_branch_with_benchmark_gt,
    exact_match_accuracy,
)


def test_edit_distance():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("", "test") == 4
    assert edit_distance(["losartan", "50mg"], ["losartan", "50mg"]) == 0
    assert edit_distance(["losartan", "50mg"], ["losartan", "100mg"]) == 1


def test_cer():
    ref = "Losartan 50mg"
    hyp = "Losartan 5Omg"  # 1 char diff (O vs 0)
    cer = calculate_cer(ref, hyp)
    assert abs(cer - (1 / len(ref))) < 1e-6
    assert calculate_cer("", "") == 0.0


def test_wer():
    ref = "Ngày uống 1 viên buổi sáng"
    hyp = "Ngày uống 2 viên buổi sáng"  # 1 word diff
    wer = calculate_wer(ref, hyp)
    assert abs(wer - (1 / 6)) < 1e-6


def test_exact_match_accuracy():
    gold = ["Losartan", "Paracetamol", "Amlodipine"]
    pred = ["Losartan", "Paracetamol", "Amlodipin"]
    acc = exact_match_accuracy(gold, pred)
    assert abs(acc - (2 / 3)) < 1e-6


def test_compare_paired_ocr():
    gold = "Paracetamol 500mg"
    raw_ocr = "Paracetam0l 5OOng"  # higher error
    proc_ocr = "Paracetamol 500mg"  # perfect

    comparison = compare_paired_ocr(gold, raw_ocr, proc_ocr)
    assert comparison.is_improved
    assert not comparison.is_degraded
    assert comparison.delta_cer < 0


def test_evaluate_branch_with_benchmark_gt():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock benchmark GT
        gt_file = os.path.join(tmpdir, "gt.json")
        with open(gt_file, "w", encoding="utf-8") as f:
            json.dump({
                "records": {
                    "IMG_001": {
                        "prescription_id": "RX_001",
                        "medication_region_transcription": "Losartan 50mg 28 Vien",
                        "medications": [
                            {"drug_normalized": "losartan", "strength_raw": "50mg", "quantity_value_raw": "28"}
                        ],
                        "split_role": "tuning",
                    }
                }
            }, f)

        # Create mock OCR branch output
        ocr_dir = os.path.join(tmpdir, "ocr")
        os.makedirs(ocr_dir)
        with open(os.path.join(ocr_dir, "IMG_001.json"), "w", encoding="utf-8") as f:
            json.dump({
                "blocks": [
                    {"lines": [{"text": "Losartan 50mg 28 Vien"}]}
                ]
            }, f)

        res = evaluate_branch_with_benchmark_gt(ocr_dir, gt_file)
        assert res["evaluated_images"] == 1
        assert res["mean_cer"] == 0.0
        assert res["drug_accuracy"] == 1.0
        assert res["strength_accuracy"] == 1.0
        assert res["quantity_accuracy"] == 1.0
