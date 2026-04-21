"""
Compute reproducible Phase A extraction metrics on real prescriptions.

Modes:
- proposed: preprocess + adaptive STT grouping + safe fallback + NER + lookup gating
- baseline_no_stt: preprocess + raw OCR blocks + NER + lookup gating
- forced_stt: preprocess + forced STT grouping + NER + lookup gating
- ablation_no_lookup: preprocess + adaptive STT selection + NER labels only
- ablation_no_preprocess: no preprocess + adaptive STT selection + NER + lookup gating

Artifacts are written to `data/output/eval/run_<timestamp>/`.

Usage:
    venv/bin/python scripts/tests/test_phase_a_eval_metrics.py
    venv/bin/python scripts/tests/test_phase_a_eval_metrics.py --limit 10
    venv/bin/python scripts/tests/test_phase_a_eval_metrics.py --modes proposed,baseline_no_stt
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

import cv2


os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_enable_pir_api", "0")


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
OUT_ROOT = ROOT / "data" / "output" / "eval"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


ALL_MODES = [
    "proposed",
    "baseline_no_stt",
    "forced_stt",
    "ablation_no_lookup",
    "ablation_no_preprocess",
]


@dataclass
class ImageEvalRow:
    mode: str
    image_id: str
    group_id: str
    relative_path: str
    elapsed_s: float
    gt_count: int
    pred_count: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    exact_match: bool
    gt_ids: list[str]
    pred_ids: list[str]
    pred_texts: list[str]


def load_manifest() -> list[dict]:
    rows = []
    with (EVAL_DIR / "phase_a_manifest.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("include_eval", "").strip().lower() == "yes":
                rows.append(row)
    return rows


def load_gt_by_image() -> dict[str, set[str]]:
    payload = json.loads((EVAL_DIR / "gt_drugs_by_image.json").read_text(encoding="utf-8"))
    result = {}
    for row in payload["images"]:
        result[row["image_id"]] = {x["canonical_id"] for x in row["expected_drugs"]}
    return result


def load_aliases() -> list[tuple[str, str]]:
    payload = json.loads((EVAL_DIR / "canonical_drug_aliases.json").read_text(encoding="utf-8"))
    aliases: list[tuple[str, str]] = []
    for row in payload["canonical_drugs"]:
        cid = row["canonical_id"]
        for a in row["aliases"]:
            aliases.append((cid, normalize_text(a)))

    # longer aliases first to reduce collisions
    aliases.sort(key=lambda x: len(x[1]), reverse=True)
    return aliases


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    cleaned = []
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return " ".join("".join(cleaned).split())


def canonicalize_prediction(pred_texts: list[str], alias_pairs: list[tuple[str, str]]) -> list[str]:
    cids: set[str] = set()
    for raw in pred_texts:
        norm = normalize_text(raw)
        best_cid = None
        best_len = -1
        for cid, alias in alias_pairs:
            if not alias:
                continue
            if alias in norm and len(alias) > best_len:
                best_cid = cid
                best_len = len(alias)
        if best_cid:
            cids.add(best_cid)
    return sorted(cids)


def build_ner_input_from_blocks(blocks) -> list[dict]:
    ner_input = []
    for b in blocks:
        text = b.text.strip()
        if not text:
            continue
        ner_input.append(
            {
                "text": text,
                "label": "other",
                "box": b.bbox,
                "bbox": b.bbox,
            }
        )
    return ner_input


def _medications_from_ner(pipe, ner_results: list[dict], *, use_lookup: bool) -> list[dict]:
    if use_lookup:
        medications, _ = pipe._extract_medications(ner_results)
        return medications

    medications = []
    for block in ner_results:
        if block.get("label") != "drugname":
            continue
        text = block.get("text", "")
        medications.append(
            {
                "ocr_text": text,
                "match_score": 0.0,
                "mapping_status": "ner_only",
            }
        )
    return medications


def run_scan_custom(pipe, image_path: str, *, use_preprocess: bool, use_stt: bool, use_lookup: bool) -> dict:
    from core.phase_a.s2_preprocess.orientation import preprocess_image
    from core.phase_a.s3_ocr.ocr_engine import group_by_stt

    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"cannot_read:{image_path}", "medications": []}

    try:
        cropped = pipe._crop_prescription(img)
        if cropped is not None:
            img = cropped
    except Exception:
        pass

    if use_preprocess:
        try:
            img, _ = preprocess_image(img, stem="eval")
        except Exception:
            pass

    ocr = pipe._get_ocr()
    result = ocr.extract(img)
    if not result.text_blocks:
        return {"medications": [], "ocr_blocks": []}

    blocks = result.text_blocks
    if use_stt:
        blocks = group_by_stt(blocks)

    ner_input = build_ner_input_from_blocks(blocks)
    if not ner_input:
        return {"medications": [], "ocr_blocks": []}

    ner_results = pipe._classify_blocks(ner_input)

    medications = _medications_from_ner(pipe, ner_results, use_lookup=use_lookup)

    return {
        "medications": medications,
        "ocr_blocks": ner_results,
    }


def run_scan_adaptive_custom(pipe, image_path: str, *, use_preprocess: bool, use_lookup: bool) -> dict:
    from core.phase_a.s2_preprocess.orientation import preprocess_image
    from core.phase_a.s3_ocr.ocr_engine import group_by_stt_with_meta

    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"cannot_read:{image_path}", "medications": []}

    try:
        cropped = pipe._crop_prescription(img)
        if cropped is not None:
            img = cropped
    except Exception:
        pass

    if use_preprocess:
        try:
            img, _ = preprocess_image(img, stem="eval")
        except Exception:
            pass

    ocr = pipe._get_ocr()
    result = ocr.extract(img)
    if not result.text_blocks:
        return {
            "medications": [],
            "ocr_blocks": [],
            "stats": {
                "selection_strategy": "raw_blocks",
                "selection_reason": "ocr_empty",
            },
        }

    raw_ner_input = pipe._build_ner_input_from_text_blocks(result.text_blocks)
    if not raw_ner_input:
        return {
            "medications": [],
            "ocr_blocks": [],
            "stats": {
                "selection_strategy": "raw_blocks",
                "selection_reason": "raw_empty",
            },
        }

    raw_ner_results = pipe._classify_blocks(raw_ner_input)
    raw_meds = _medications_from_ner(pipe, raw_ner_results, use_lookup=use_lookup)

    grouped_blocks_obj, grouping_meta = group_by_stt_with_meta(result.text_blocks)
    grouped_ner_input = pipe._build_ner_input_from_text_blocks(grouped_blocks_obj)
    if grouped_ner_input:
        grouped_ner_results = pipe._classify_blocks(grouped_ner_input)
        grouped_meds = _medications_from_ner(
            pipe,
            grouped_ner_results,
            use_lookup=use_lookup,
        )
    else:
        grouped_ner_results = []
        grouped_meds = []

    raw_summary = pipe._summarize_scan_branch(raw_ner_input, raw_ner_results, raw_meds)
    grouped_summary = pipe._summarize_scan_branch(
        grouped_ner_input,
        grouped_ner_results,
        grouped_meds,
    )
    selection_strategy, selection_reason = pipe._select_app_scan_branch(
        raw_summary,
        grouped_summary,
        grouping_meta,
    )

    if selection_strategy == "stt_grouped":
        medications = grouped_meds
        ner_results = grouped_ner_results
    else:
        medications = raw_meds
        ner_results = raw_ner_results

    return {
        "medications": medications,
        "ocr_blocks": ner_results,
        "stats": {
            "selection_strategy": selection_strategy,
            "selection_reason": selection_reason,
            "raw_branch": raw_summary,
            "grouped_branch": grouped_summary,
            "grouping_meta": grouping_meta,
        },
    }


def run_mode(pipe, mode: str, image_path: str) -> dict:
    if mode == "proposed":
        return pipe.scan_prescription_app(image_path)
    if mode == "baseline_no_stt":
        return run_scan_custom(
            pipe,
            image_path,
            use_preprocess=True,
            use_stt=False,
            use_lookup=True,
        )
    if mode == "forced_stt":
        return run_scan_custom(
            pipe,
            image_path,
            use_preprocess=True,
            use_stt=True,
            use_lookup=True,
        )
    if mode == "ablation_no_lookup":
        return run_scan_adaptive_custom(
            pipe,
            image_path,
            use_preprocess=True,
            use_lookup=False,
        )
    if mode == "ablation_no_preprocess":
        return run_scan_adaptive_custom(
            pipe,
            image_path,
            use_preprocess=False,
            use_lookup=True,
        )
    raise ValueError(f"Unknown mode: {mode}")


def evaluate_row(
    mode: str,
    image_row: dict,
    result: dict,
    elapsed_s: float,
    gt_ids: set[str],
    alias_pairs: list[tuple[str, str]],
) -> ImageEvalRow:
    meds = result.get("medications", []) if isinstance(result, dict) else []
    pred_texts = []
    for m in meds:
        if isinstance(m, dict):
            pred_texts.append(
                m.get("ocr_text")
                or m.get("drug_name")
                or m.get("matched_drug_name")
                or ""
            )

    pred_ids = set(canonicalize_prediction(pred_texts, alias_pairs))
    tp = len(gt_ids & pred_ids)
    fp = len(pred_ids - gt_ids)
    fn = len(gt_ids - pred_ids)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) else 0.0

    return ImageEvalRow(
        mode=mode,
        image_id=image_row["image_id"],
        group_id=image_row["group_id"],
        relative_path=image_row["relative_path"],
        elapsed_s=elapsed_s,
        gt_count=len(gt_ids),
        pred_count=len(pred_ids),
        tp=tp,
        fp=fp,
        fn=fn,
        precision=p,
        recall=r,
        f1=f1,
        exact_match=pred_ids == gt_ids,
        gt_ids=sorted(gt_ids),
        pred_ids=sorted(pred_ids),
        pred_texts=[t for t in pred_texts if t],
    )


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values = sorted(values)
    idx = (len(values) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[lo]
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def summarize_mode(rows: list[ImageEvalRow]) -> dict:
    tp = sum(r.tp for r in rows)
    fp = sum(r.fp for r in rows)
    fn = sum(r.fn for r in rows)
    micro_p = tp / (tp + fp) if (tp + fp) else 0.0
    micro_r = tp / (tp + fn) if (tp + fn) else 0.0
    micro_f1 = (2 * micro_p * micro_r) / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

    macro_p = mean([r.precision for r in rows]) if rows else 0.0
    macro_r = mean([r.recall for r in rows]) if rows else 0.0
    macro_f1 = mean([r.f1 for r in rows]) if rows else 0.0

    exact = sum(1 for r in rows if r.exact_match)

    times = [r.elapsed_s for r in rows]
    cold = times[0] if times else 0.0
    warm = times[1:] if len(times) > 1 else []

    return {
        "image_count": len(rows),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "micro_precision": micro_p,
        "micro_recall": micro_r,
        "micro_f1": micro_f1,
        "macro_precision": macro_p,
        "macro_recall": macro_r,
        "macro_f1": macro_f1,
        "exact_match_count": exact,
        "exact_match_rate": exact / len(rows) if rows else 0.0,
        "runtime_cold_s": cold,
        "runtime_warm_mean_s": mean(warm) if warm else cold,
        "runtime_p50_s": percentile(times, 0.50),
        "runtime_p90_s": percentile(times, 0.90),
    }


def write_per_image_csv(out_path: Path, rows: list[ImageEvalRow]) -> None:
    fields = [
        "mode",
        "image_id",
        "group_id",
        "relative_path",
        "elapsed_s",
        "gt_count",
        "pred_count",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "f1",
        "exact_match",
        "gt_ids",
        "pred_ids",
        "pred_texts",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "mode": r.mode,
                    "image_id": r.image_id,
                    "group_id": r.group_id,
                    "relative_path": r.relative_path,
                    "elapsed_s": f"{r.elapsed_s:.4f}",
                    "gt_count": r.gt_count,
                    "pred_count": r.pred_count,
                    "tp": r.tp,
                    "fp": r.fp,
                    "fn": r.fn,
                    "precision": f"{r.precision:.6f}",
                    "recall": f"{r.recall:.6f}",
                    "f1": f"{r.f1:.6f}",
                    "exact_match": int(r.exact_match),
                    "gt_ids": "|".join(r.gt_ids),
                    "pred_ids": "|".join(r.pred_ids),
                    "pred_texts": " || ".join(r.pred_texts),
                }
            )


def write_ablation_csv(out_path: Path, by_mode: dict[str, dict]) -> None:
    fields = [
        "mode",
        "image_count",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "fp",
        "fn",
        "exact_match_rate",
        "runtime_cold_s",
        "runtime_warm_mean_s",
        "runtime_p50_s",
        "runtime_p90_s",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for mode, s in by_mode.items():
            writer.writerow(
                {
                    "mode": mode,
                    "image_count": s["image_count"],
                    "micro_precision": f"{s['micro_precision']:.6f}",
                    "micro_recall": f"{s['micro_recall']:.6f}",
                    "micro_f1": f"{s['micro_f1']:.6f}",
                    "fp": s["fp"],
                    "fn": s["fn"],
                    "exact_match_rate": f"{s['exact_match_rate']:.6f}",
                    "runtime_cold_s": f"{s['runtime_cold_s']:.4f}",
                    "runtime_warm_mean_s": f"{s['runtime_warm_mean_s']:.4f}",
                    "runtime_p50_s": f"{s['runtime_p50_s']:.4f}",
                    "runtime_p90_s": f"{s['runtime_p90_s']:.4f}",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--modes",
        type=str,
        default=",".join(ALL_MODES),
        help="Comma-separated modes",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit image count")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in selected_modes:
        if m not in ALL_MODES:
            raise ValueError(f"Unsupported mode: {m}")

    manifest = load_manifest()
    if args.limit > 0:
        manifest = manifest[: args.limit]

    gt_by_image = load_gt_by_image()
    alias_pairs = load_aliases()

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = OUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    from core.pipeline import MedicinePipeline

    all_rows: list[ImageEvalRow] = []
    by_mode_rows: dict[str, list[ImageEvalRow]] = {m: [] for m in selected_modes}

    t_global_start = time.perf_counter()
    for mode in selected_modes:
        print(f"\n=== MODE: {mode} ===")
        pipe = MedicinePipeline()
        for idx, row in enumerate(manifest, start=1):
            image_id = row["image_id"]
            image_path = ROOT / row["relative_path"]
            gt_ids = gt_by_image[image_id]

            t0 = time.perf_counter()
            result = run_mode(pipe, mode, str(image_path))
            elapsed = time.perf_counter() - t0

            eval_row = evaluate_row(mode, row, result, elapsed, gt_ids, alias_pairs)
            by_mode_rows[mode].append(eval_row)
            all_rows.append(eval_row)

            print(
                f"[{idx:02d}/{len(manifest):02d}] {image_id} "
                f"tp={eval_row.tp} fp={eval_row.fp} fn={eval_row.fn} "
                f"f1={eval_row.f1:.3f} t={elapsed:.2f}s"
            )

    mode_summaries = {mode: summarize_mode(rows) for mode, rows in by_mode_rows.items()}
    total_elapsed = time.perf_counter() - t_global_start

    write_per_image_csv(out_dir / "per_image_metrics.csv", all_rows)
    write_ablation_csv(out_dir / "ablation_summary.csv", mode_summaries)

    detail_jsonl = out_dir / "per_image_detail.jsonl"
    with detail_jsonl.open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(
                json.dumps(
                    {
                        "mode": r.mode,
                        "image_id": r.image_id,
                        "group_id": r.group_id,
                        "relative_path": r.relative_path,
                        "elapsed_s": r.elapsed_s,
                        "gt_ids": r.gt_ids,
                        "pred_ids": r.pred_ids,
                        "pred_texts": r.pred_texts,
                        "tp": r.tp,
                        "fp": r.fp,
                        "fn": r.fn,
                        "precision": r.precision,
                        "recall": r.recall,
                        "f1": r.f1,
                        "exact_match": r.exact_match,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    report = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "image_count": len(manifest),
        "modes": selected_modes,
        "total_wall_time_s": total_elapsed,
        "summaries": mode_summaries,
        "files": {
            "per_image_metrics_csv": str((out_dir / "per_image_metrics.csv").relative_to(ROOT)),
            "ablation_summary_csv": str((out_dir / "ablation_summary.csv").relative_to(ROOT)),
            "per_image_detail_jsonl": str((out_dir / "per_image_detail.jsonl").relative_to(ROOT)),
        },
    }

    report_path = out_dir / "phase_a_eval_metrics.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_path = OUT_ROOT / "latest_eval_run.txt"
    latest_path.write_text(str(out_dir.relative_to(ROOT)), encoding="utf-8")

    print("\n=== SUMMARY ===")
    for mode, s in mode_summaries.items():
        print(
            f"{mode}: F1={s['micro_f1']:.4f} P={s['micro_precision']:.4f} "
            f"R={s['micro_recall']:.4f} FP={s['fp']} FN={s['fn']} "
            f"Exact={s['exact_match_rate']:.2%} WarmMean={s['runtime_warm_mean_s']:.2f}s"
        )

    print(f"\nSaved report: {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
