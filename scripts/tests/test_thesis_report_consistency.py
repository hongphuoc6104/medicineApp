"""
Validate thesis report consistency against locked evaluation artifacts.

Checks:
- Required artifact files exist.
- Thesis run id matches locked run id.
- Key reported metrics match artifact values after deterministic rounding.
- Citation keys are resolvable (\\cite keys must have \\bibitem).
- Basic over-claim phrases are not present.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
THESIS_PATH = ROOT / "docs" / "thesis_report" / "main.tex"
LOCKED_RUN_ID = "run_20260421_103453"
RUN_DIR = ROOT / "data" / "output" / "eval" / LOCKED_RUN_ID


def fmt_vi(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for blob in re.findall(r"\\cite\{([^}]+)\}", tex):
        for key in blob.split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def extract_bib_keys(tex: str) -> list[str]:
    return re.findall(r"\\bibitem\{([^}]+)\}", tex)


def main() -> None:
    errors: list[str] = []

    required_paths = [
        THESIS_PATH,
        RUN_DIR / "phase_a_eval_metrics.json",
        RUN_DIR / "ablation_summary.csv",
        RUN_DIR / "ocr_metrics.json",
        RUN_DIR / "error_analysis.json",
        RUN_DIR / "bootstrap_ci.json",
        RUN_DIR / "track_b_operational.json",
        ROOT / "data" / "eval" / "phase_a_manifest.csv",
        ROOT / "data" / "eval" / "annotation_protocol.md",
        ROOT / "data" / "eval" / "exclusion_log.md",
        ROOT / "data" / "eval" / "gt_drugs_by_image.json",
        ROOT / "data" / "eval" / "gt_ocr_subset.jsonl",
        ROOT / "data" / "eval_v2" / "phase_a_manifest_v2.csv",
        ROOT / "data" / "eval_v2" / "annotation_protocol_v2.md",
        ROOT / "data" / "eval_v2" / "sampling_log.json",
        ROOT / "data" / "eval_v2" / "exclusion_log_v2.md",
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing required artifact: {path.relative_to(ROOT)}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        raise SystemExit(1)

    tex = THESIS_PATH.read_text(encoding="utf-8")
    metrics = load_json(RUN_DIR / "phase_a_eval_metrics.json")
    ocr = load_json(RUN_DIR / "ocr_metrics.json")
    err = load_json(RUN_DIR / "error_analysis.json")
    ci = load_json(RUN_DIR / "bootstrap_ci.json")
    track_b = load_json(RUN_DIR / "track_b_operational.json")

    run_ids_in_text = set(re.findall(r"run_\d{8}_\d{6}", tex))
    if run_ids_in_text != {LOCKED_RUN_ID}:
        errors.append(
            "Run id mismatch in thesis text: "
            f"found {sorted(run_ids_in_text)}, expected only {LOCKED_RUN_ID}"
        )

    proposed = metrics["summaries"]["proposed"]
    baseline = metrics["summaries"]["baseline_no_stt"]
    forced = metrics["summaries"]["forced_stt"]
    proposed_ci = ci["modes"]["proposed"]["bootstrap"]
    baseline_ci = ci["modes"]["baseline_no_stt"]["bootstrap"]
    delta_ci = ci["paired_deltas"]["proposed_minus_baseline_no_stt"]["bootstrap"]

    expected_fragments = [
        f"TP / FP / FN & {proposed['tp']} / {proposed['fp']} / {proposed['fn']}",
        f"Micro precision & {fmt_vi(proposed['micro_precision'], 3)}",
        f"Micro recall & {fmt_vi(proposed['micro_recall'], 3)}",
        f"Micro F1 & {fmt_vi(proposed['micro_f1'], 3)}",
        f"Cold-start latency & {fmt_vi(proposed['runtime_cold_s'], 2)}",
        f"Warm latency trung bình & {fmt_vi(proposed['runtime_warm_mean_s'], 2)}",
        (
            "Độ trễ p50 / p90 & "
            f"{fmt_vi(proposed['runtime_p50_s'], 2)} / {fmt_vi(proposed['runtime_p90_s'], 2)}"
        ),
        f"Baseline (không STT) & {fmt_vi(baseline['micro_precision'], 3)} & {fmt_vi(baseline['micro_recall'], 3)} & {fmt_vi(baseline['micro_f1'], 3)}",
        f"Ablation (STT cưỡng bức) & {fmt_vi(forced['micro_precision'], 3)} & {fmt_vi(forced['micro_recall'], 3)} & {fmt_vi(forced['micro_f1'], 3)}",
        f"Tỉ lệ match được tham chiếu OCR & {ocr['matched_count']}/{ocr['sample_count']} ({fmt_vi(ocr['matched_ratio'] * 100.0, 2)}\\%)",
        f"CER / WER (phạt mục bị bỏ sót) & {fmt_vi(ocr['avg_cer'], 3)} / {fmt_vi(ocr['avg_wer'], 3)}",
        f"{err['error_images']}/{err['total_images']} ảnh có sai số",
        f"[" + fmt_vi(proposed_ci['precision']['ci95'][0], 3) + "; " + fmt_vi(proposed_ci['precision']['ci95'][1], 3) + "]",
        f"[" + fmt_vi(proposed_ci['recall']['ci95'][0], 3) + "; " + fmt_vi(proposed_ci['recall']['ci95'][1], 3) + "]",
        f"[" + fmt_vi(proposed_ci['f1']['ci95'][0], 3) + "; " + fmt_vi(proposed_ci['f1']['ci95'][1], 3) + "]",
        f"[" + fmt_vi(baseline_ci['f1']['ci95'][0], 3) + "; " + fmt_vi(baseline_ci['f1']['ci95'][1], 3) + "]",
        f"[" + fmt_vi(delta_ci['f1']['ci95'][0], 3) + "; " + fmt_vi(delta_ci['f1']['ci95'][1], 3) + "]",
        "Track A",
        "Track B",
        f"{fmt_vi(track_b['non_empty_output_rate'] * 100.0, 2)}\\%",
        "90/90 test pass",
    ]

    for frag in expected_fragments:
        if frag not in tex:
            errors.append(f"Missing expected thesis fragment: {frag}")

    cite_keys = extract_cite_keys(tex)
    bib_keys = extract_bib_keys(tex)
    bib_key_set = set(bib_keys)

    unresolved = sorted(cite_keys - bib_key_set)
    duplicate_bib = sorted({k for k in bib_keys if bib_keys.count(k) > 1})

    if unresolved:
        errors.append("Unresolved citation keys: " + ", ".join(unresolved))
    if duplicate_bib:
        errors.append("Duplicate bibliography keys: " + ", ".join(duplicate_bib))

    overclaim_phrases = [
        "chinh xac tuyet doi",
        "hoan hao",
        "khong loi",
        "zero loi",
        "vuot troi hoan toan",
    ]
    normalized = tex.lower()
    normalized = normalized.replace("đ", "d")
    normalized = re.sub(r"[^a-z0-9\\s]", " ", normalized)
    normalized = " ".join(normalized.split())

    for phrase in overclaim_phrases:
        if phrase in normalized:
            errors.append(f"Potential over-claim phrase found: {phrase}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        raise SystemExit(1)

    print("PASS: thesis report consistency checks succeeded")
    print(f"- run_id: {LOCKED_RUN_ID}")
    print(f"- citations resolved: {len(cite_keys)} keys")
    print("- metrics and artifact references are consistent")


if __name__ == "__main__":
    main()
