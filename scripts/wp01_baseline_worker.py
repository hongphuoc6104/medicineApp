#!/usr/bin/env python3
"""Deferred-import OCR worker for an already-approved WP-01 run."""

from __future__ import annotations

import argparse
import functools
import hashlib
import inspect
import json
import os
import random
import resource
import sys
import time
from pathlib import Path


PINNED_COMMIT = "a6810a392c97593f073a9c5e2b8dfc47027c1911"
PINNED_SOURCE_TREE = "a0e6a2feb2007cbec8016be775080f7a6cdfce60"
REQUIRED_TIMING_STAGES = (
    "yolo",
    "deskew",
    "orientation",
    "paddle_detection",
    "vietocr_recognition",
    "layout_grouping",
    "phobert_ner",
    "drug_lookup",
    "total",
)
REQUIRED_INITIALIZATION_STAGES = (
    "model_framework_imports",
    "yolo_initialization",
    "paddle_detection_recognition_initialization",
    "vietocr_initialization",
    "orientation_initialization",
    "phobert_initialization",
    "drug_lookup_initialization",
    "initialization_total",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resource_snapshot() -> resource.struct_rusage:
    return resource.getrusage(resource.RUSAGE_SELF)


def resource_delta(start: resource.struct_rusage, end: resource.struct_rusage) -> dict:
    user_cpu = max(0.0, end.ru_utime - start.ru_utime)
    system_cpu = max(0.0, end.ru_stime - start.ru_stime)
    return {
        "process_cpu_s": user_cpu + system_cpu,
        "user_cpu_s": user_cpu,
        "system_cpu_s": system_cpu,
        "max_rss_kb": max(0.0, float(end.ru_maxrss)),
        "voluntary_context_switches": max(0.0, float(end.ru_nvcsw - start.ru_nvcsw)),
        "involuntary_context_switches": max(0.0, float(end.ru_nivcsw - start.ru_nivcsw)),
    }


def measure_cold_observation(initialize, first_inference):
    resources_before = resource_snapshot()
    cold_started = time.perf_counter()
    runtime, initialization_timings = initialize()
    inference_output = first_inference(runtime)
    result, stage_timings = inference_output[:2]
    cold_total = time.perf_counter() - cold_started
    resources_after = resource_snapshot()
    return runtime, result, {
        "initialization_timings_s": initialization_timings,
        "stage_timings_s": stage_timings,
        "cold_total_s": cold_total,
        "resource_usage": resource_delta(resources_before, resources_after),
    }


def install_stage_instrumentation(pipe, ocr, orientation_module, ocr_module):
    active = {"timings": None}

    def wrap(target, attribute: str, stage: str) -> None:
        original = getattr(target, attribute)

        @functools.wraps(original)
        def measured(*args, **kwargs):
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                timings = active["timings"]
                if timings is not None:
                    timings[stage] += time.perf_counter() - started

        setattr(target, attribute, measured)

    wrap(pipe, "_crop_prescription", "yolo")
    wrap(orientation_module, "deskew", "deskew")
    wrap(orientation_module, "fix_orientation_ai", "orientation")
    wrap(ocr, "_detect_polys", "paddle_detection")
    wrap(ocr, "_recognize_batch", "vietocr_recognition")
    wrap(ocr_module, "group_by_stt_with_meta", "layout_grouping")
    wrap(pipe, "_classify_blocks", "phobert_ner")
    wrap(pipe, "_extract_medications", "drug_lookup")

    def run(image_path: str) -> tuple[dict, dict, dict]:
        timings = {stage: 0.0 for stage in REQUIRED_TIMING_STAGES}
        active["timings"] = timings
        resources_before = resource_snapshot()
        started = time.perf_counter()
        try:
            try:
                result = pipe.scan_prescription_app(image_path)
            except Exception as exc:
                result = {"error": f"pipeline_exception:{type(exc).__name__}"}
        finally:
            timings["total"] = time.perf_counter() - started
            active["timings"] = None
        resources_after = resource_snapshot()

        candidates = [
            result.get("stage_timings_s"),
            result.get("stage_timings"),
            result.get("timings"),
            result.get("timing"),
            (result.get("stats") or {}).get("stage_timings_s"),
            (result.get("stats") or {}).get("stage_timings"),
            (result.get("stats") or {}).get("timings"),
            (result.get("stats") or {}).get("timing"),
        ] if isinstance(result, dict) else []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for stage in REQUIRED_TIMING_STAGES:
                value = candidate.get(stage, candidate.get(f"{stage}_s"))
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                    timings[stage] = float(value)
        return result, timings, resource_delta(resources_before, resources_after)

    return run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, action="append", default=[])
    parser.add_argument("--device", choices=("cpu", "gpu"), required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt_env = os.environ.get("WP01_PREFLIGHT_RECEIPT", "")
    if not receipt_env or Path(receipt_env).resolve() != args.receipt.resolve():
        raise RuntimeError("Worker requires the harness preflight receipt")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if not receipt.get("passed") or receipt.get("baseline_commit") != PINNED_COMMIT:
        raise RuntimeError("Worker refused an invalid or failed preflight receipt")
    if receipt.get("worker_sha256") != sha256_file(Path(__file__)):
        raise RuntimeError("Worker source hash does not match the preflight receipt")
    tooling_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(tooling_root / "scripts"))
    import wp01_baseline_tooling as tooling

    if args.requirements.resolve() != tooling.DEFAULT_REQUIREMENTS.resolve():
        raise RuntimeError("Worker only accepts the tracked WP-01 asset requirements")
    if not tooling._is_within(args.approval, tooling.LOCAL_ROOT):
        raise RuntimeError("Worker approval record must be inside the ignored WP-01 local directory")

    # A fresh standard-library-only preflight is authoritative; the JSON receipt is not.
    fresh = tooling.run_preflight(
        args.requirements,
        args.approval,
        args.code_root,
        args.asset_root,
        args.device,
    )
    if (
        fresh.get("baseline_commit") != PINNED_COMMIT
        or fresh.get("code_state", {}).get("tree_digest") != PINNED_SOURCE_TREE
    ):
        raise RuntimeError("Fresh preflight is not pinned to the approved source tree")
    tooling.validate_fresh_preflight(receipt, fresh)
    receipt = {**fresh, "run_id": receipt["run_id"]}

    os.chdir(args.code_root.resolve())
    asset_roots = [path.resolve() for path in args.asset_root]
    safe_sys_path = []
    for entry in sys.path:
        resolved = Path(entry or ".").resolve()
        if (
            resolved == tooling_root.resolve()
            or tooling_root.resolve() in resolved.parents
            or resolved in asset_roots
        ):
            continue
        safe_sys_path.append(entry)
    sys.path = safe_sys_path
    sys.path.insert(0, str(args.code_root.resolve()))

    final_code_state = tooling.default_commit_resolver(args.code_root)
    final_code_errors = tooling.validate_code_state(
        final_code_state,
        PINNED_COMMIT,
        PINNED_SOURCE_TREE,
    )
    if final_code_errors:
        raise RuntimeError(f"Baseline code changed before import: {final_code_errors}")
    if fresh.get("worker_sha256") != sha256_file(Path(__file__)):
        raise RuntimeError("Worker source changed before model import")

    process = receipt["process_config"]
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    rows = list(receipt["input_rows"])
    random.Random(receipt["benchmark_policy"]["seed"]).shuffle(rows)

    def initialize_runtime():
        initialization_timings = {
            stage: 0.0 for stage in REQUIRED_INITIALIZATION_STAGES
        }
        initialization_started = time.perf_counter()

        imports_started = time.perf_counter()
        import paddle
        import torch
        from core.phase_a.s2_preprocess import orientation
        from core.phase_a.s3_ocr import ocr_engine as ocr_engine_module
        from core.phase_a.s3_ocr.ocr_engine import HybridOcrModule
        from core.phase_a.s5_classify.ner_extractor import NerExtractor
        from core.phase_a.s6_drug_search.drug_lookup import DrugLookup
        from core.pipeline import MedicinePipeline
        from paddleocr import DocImgOrientationClassification, PaddleOCR
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor

        if process["device"] == "cpu":
            if torch.cuda.is_available():
                raise RuntimeError("CPU-forced run still exposes CUDA to torch")
            paddle.set_device("cpu")
            paddle.device.is_compiled_with_cuda = lambda: False
        else:
            if not torch.cuda.is_available() or not paddle.device.is_compiled_with_cuda():
                raise RuntimeError("GPU run requested but CUDA is not available")
            paddle.set_device("gpu:0")
        initialization_timings["model_framework_imports"] = (
            time.perf_counter() - imports_started
        )

        def initialize_stage(stage, constructor):
            started = time.perf_counter()
            value = constructor()
            initialization_timings[stage] = time.perf_counter() - started
            return value

        def initialize_yolo():
            pipeline = MedicinePipeline(
                yolo_weights=receipt["resolved_assets"]["yolo_prescription"],
                device=process["device"],
            )
            pipeline._get_detector()
            return pipeline

        pipe = initialize_stage("yolo_initialization", initialize_yolo)
        pipe._drug_mapper = initialize_stage(
            "drug_lookup_initialization",
            lambda: DrugLookup(db_path=receipt["resolved_assets"]["drug_database"]),
        )
        pipe._classifier = initialize_stage(
            "phobert_initialization",
            lambda: NerExtractor(model_path=receipt["resolved_assets"]["phobert_ner"]),
        )

        paddle_parameters = inspect.signature(PaddleOCR).parameters
        required_paddle_parameters = {
            "text_detection_model_dir",
            "text_recognition_model_dir",
        }
        if not required_paddle_parameters.issubset(paddle_parameters):
            raise RuntimeError(
                "Pinned runtime cannot explicitly bind Paddle detection and recognition paths"
            )
        ocr = HybridOcrModule(device=process["device"])
        ocr._det_engine = initialize_stage(
            "paddle_detection_recognition_initialization",
            lambda: PaddleOCR(
                text_detection_model_dir=receipt["resolved_assets"]["paddle_text_detection"],
                text_recognition_model_dir=receipt["resolved_assets"]["paddle_loaded_recognizer"],
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device=ocr._paddle_device,
                enable_mkldnn=False,
            ),
        )

        def initialize_vietocr():
            config = Cfg.load_config_from_name("vgg_transformer")
            config["device"] = ocr._torch_device
            config["predictor"]["beamsearch"] = False
            config["weights"] = receipt["resolved_assets"]["vietocr_vgg_transformer"]
            return Predictor(config)

        ocr._rec_engine = initialize_stage(
            "vietocr_initialization",
            initialize_vietocr,
        )
        pipe._ocr = ocr
        orientation._classifier_cache = initialize_stage(
            "orientation_initialization",
            lambda: DocImgOrientationClassification(
                model_dir=receipt["resolved_assets"]["paddle_document_orientation"]
            ),
        )
        orientation.PADDLE_AVAILABLE = True

        runtime_bindings = {
            "yolo_prescription": "explicit:MedicinePipeline.yolo_weights",
            "phobert_ner": "explicit:NerExtractor.model_path",
            "vietocr_vgg_transformer": "explicit:VietOCR.config.weights",
            "paddle_text_detection": "explicit:PaddleOCR.text_detection_model_dir",
            "paddle_loaded_recognizer": "explicit:PaddleOCR.text_recognition_model_dir",
            "paddle_document_orientation": "explicit:DocImgOrientationClassification.model_dir",
            "drug_database": "explicit:DrugLookup.db_path",
        }
        tooling.validate_runtime_bindings(
            {item["id"] for item in receipt["runtime_inventory"]},
            runtime_bindings,
        )
        observed_scan = install_stage_instrumentation(
            pipe,
            ocr,
            orientation,
            ocr_engine_module,
        )
        initialization_timings["initialization_total"] = (
            time.perf_counter() - initialization_started
        )
        return {
            "observed_scan": observed_scan,
            "runtime_bindings": runtime_bindings,
        }, initialization_timings

    runtime, _, cold_observation = measure_cold_observation(
        initialize_runtime,
        lambda initialized: initialized["observed_scan"](rows[0]["path"]),
    )
    observed_scan = runtime["observed_scan"]
    runtime_bindings = runtime["runtime_bindings"]
    tooling.validate_observation_metrics([], cold_observation)
    (args.output.parent / "runtime_metadata.json").write_text(
        json.dumps(
            {
                "gate_fingerprint": receipt["gate_fingerprint"],
                "source_tree_digest": final_code_state["tree_digest"],
                "worker_sha256": fresh["worker_sha256"],
                "cold_total_s": cold_observation["cold_total_s"],
                "cold_observation": cold_observation,
                "runtime_bindings": runtime_bindings,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    repetitions = int(receipt["benchmark_policy"]["warm_repetitions_per_image"])
    with args.output.open("w", encoding="utf-8") as output:
        total = repetitions * len(rows)
        completed = 0
        for repetition in range(1, repetitions + 1):
            for row in rows:
                result, stage_timings, resource_usage = observed_scan(row["path"])
                elapsed = stage_timings["total"]
                tooling.validate_observation_metrics(
                    [
                        {
                            "stage_timings_s": stage_timings,
                            "resource_usage": resource_usage,
                        }
                    ],
                    cold_observation,
                )
                output.write(
                    json.dumps(
                        {
                            "record_id": row["record_id"],
                            "image_id": row["image_id"],
                            "split": row["split"],
                            "repetition": repetition,
                            "elapsed_s": elapsed,
                            "stage_timings_s": stage_timings,
                            "resource_usage": resource_usage,
                            "result": result,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                output.flush()
                completed += 1
                print(f"WP-01 progress {completed}/{total}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
