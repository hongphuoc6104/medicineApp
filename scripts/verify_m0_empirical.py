"""Independent empirical verification and benchmark suite for Milestone M0 (ML Kit Ingestion A0)."""

from __future__ import annotations

import json
import os
import resource
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

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
from rxie.text import DocumentText, build_document_text


def run_full_empirical_verification() -> dict[str, Any]:
    ocr_dir = Path("data/ocr_final")
    if not ocr_dir.exists():
        raise FileNotFoundError(f"Directory not found: {ocr_dir}")

    files = sorted(ocr_dir.glob("*.json"))
    total_files = len(files)
    print(f"[*] Found {total_files} JSON files in {ocr_dir}")

    results: dict[str, Any] = {
        "total_files": total_files,
        "files_checked": 0,
        "exact_raw_text_matches": 0,
        "raw_text_mismatches": [],
        "span_slice_matches": 0,
        "span_slice_mismatches": [],
        "reading_order_monotonic_valid": 0,
        "reading_order_failures": [],
        "region_id_unique_valid": 0,
        "region_id_failures": [],
        "bbox_bounds_valid": 0,
        "bbox_bounds_failures": [],
        "total_regions": 0,
        "total_characters": 0,
        "empty_files": [],
        "file_latencies_ms": [],
    }

    # Start memory tracing
    tracemalloc.start()
    t0_wall = time.perf_counter()
    t0_cpu = time.process_time()

    documents: dict[str, OcrDocument] = {}

    for fpath in files:
        doc_id = fpath.stem
        t_start = time.perf_counter()

        # Load raw file
        with open(fpath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        expected_full_text = raw_data.get("fullText", "")

        # Ingest document
        doc = load_mlkit_ocr_document(fpath)
        t_end = time.perf_counter()
        results["file_latencies_ms"].append((t_end - t_start) * 1000.0)
        documents[doc_id] = doc
        results["files_checked"] += 1

        # Check 1: Document metadata & schema
        if doc.schema_version != "rxie.ocr.v1":
            results["raw_text_mismatches"].append(
                (doc_id, "schema_version mismatch", doc.schema_version)
            )
        if doc.document_id != doc_id:
            results["raw_text_mismatches"].append(
                (doc_id, "document_id mismatch", doc.document_id)
            )
        if len(doc.pages) != 1:
            results["raw_text_mismatches"].append(
                (doc_id, "pages count != 1", len(doc.pages))
            )

        page = doc.pages[0]
        w, h = page.width, page.height
        regions = page.regions
        num_regions = len(regions)
        results["total_regions"] += num_regions

        if num_regions == 0:
            results["empty_files"].append(doc_id)

        # Check 2: Exact character-for-character raw_text equality
        doc_text = build_document_text(doc)
        results["total_characters"] += len(doc_text.raw_text)

        if doc_text.raw_text == expected_full_text:
            results["exact_raw_text_matches"] += 1
        else:
            results["raw_text_mismatches"].append(
                {
                    "doc_id": doc_id,
                    "expected_len": len(expected_full_text),
                    "actual_len": len(doc_text.raw_text),
                    "expected_preview": repr(expected_full_text[:100]),
                    "actual_preview": repr(doc_text.raw_text[:100]),
                }
            )

        # Check 3: Region character slice matching
        doc_span_failures = []
        if len(doc_text.regions) != len(regions):
            doc_span_failures.append(
                f"doc_text.regions len ({len(doc_text.regions)}) != page.regions len ({len(regions)})"
            )

        for span, region in zip(doc_text.regions, regions):
            if span.region_id != region.region_id:
                doc_span_failures.append(
                    f"region_id mismatch: {span.region_id} vs {region.region_id}"
                )
            sliced = doc_text.raw_text[span.start : span.end]
            if sliced != region.text:
                doc_span_failures.append(
                    f"slice mismatch at [{span.start}:{span.end}]: expected {repr(region.text)}, got {repr(sliced)}"
                )

        if not doc_span_failures:
            results["span_slice_matches"] += 1
        else:
            results["span_slice_mismatches"].append((doc_id, doc_span_failures))

        # Check 4: Reading order strictly monotonic 0..N-1 with 0 duplicates
        reading_orders = [r.reading_order for r in regions]
        expected_orders = list(range(num_regions))
        if reading_orders == expected_orders:
            results["reading_order_monotonic_valid"] += 1
        else:
            results["reading_order_failures"].append(
                (doc_id, reading_orders[:10], expected_orders[:10])
            )

        # Check 5: Unique region_ids across doc
        region_ids = [r.region_id for r in regions]
        if len(region_ids) == len(set(region_ids)):
            results["region_id_unique_valid"] += 1
        else:
            results["region_id_failures"].append((doc_id, len(region_ids), len(set(region_ids))))

        # Check 6: Bounding box points within [0, w] and [0, h]
        bbox_failures = []
        for r in regions:
            if len(r.bbox.points) != 4:
                bbox_failures.append((r.region_id, "point_count != 4", len(r.bbox.points)))
            for pt_idx, (x, y) in enumerate(r.bbox.points):
                if not (0.0 <= x <= float(w) and 0.0 <= y <= float(h)):
                    bbox_failures.append(
                        (r.region_id, pt_idx, (x, y), (w, h))
                    )
        if not bbox_failures:
            results["bbox_bounds_valid"] += 1
        else:
            results["bbox_bounds_failures"].append((doc_id, bbox_failures))

    t1_wall = time.perf_counter()
    t1_cpu = time.process_time()
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rusage = resource.getrusage(resource.RUSAGE_SELF)
    peak_rss_mb = rusage.ru_maxrss / 1024.0  # Linux: ru_maxrss is in KiB

    total_wall_time = t1_wall - t0_wall
    total_cpu_time = t1_cpu - t0_cpu
    throughput_fps = total_files / total_wall_time if total_wall_time > 0 else 0.0

    latencies = sorted(results["file_latencies_ms"])
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    min_latency = latencies[0] if latencies else 0.0
    max_latency = latencies[-1] if latencies else 0.0
    p50_latency = latencies[int(0.50 * len(latencies))] if latencies else 0.0
    p95_latency = latencies[int(0.95 * len(latencies))] if latencies else 0.0
    p99_latency = latencies[int(0.99 * len(latencies))] if latencies else 0.0

    results["benchmark"] = {
        "total_wall_time_sec": total_wall_time,
        "total_cpu_time_sec": total_cpu_time,
        "throughput_files_per_sec": throughput_fps,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "p50_latency_ms": p50_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "traced_peak_mem_mb": peak_mem / (1024 * 1024),
        "traced_final_mem_mb": current_mem / (1024 * 1024),
        "peak_rss_mb": peak_rss_mb,
    }

    # Also test batch ingestion function directly
    t_batch_start = time.perf_counter()
    batch_docs = ingest_all_mlkit_captures(ocr_dir)
    t_batch_end = time.perf_counter()
    results["batch_ingest_count"] = len(batch_docs)
    results["batch_ingest_time_sec"] = t_batch_end - t_batch_start
    results["batch_ingest_fps"] = len(batch_docs) / (t_batch_end - t_batch_start)

    return results


def run_adversarial_stress_tests() -> dict[str, Any]:
    """Execute adversarial edge cases against ingestion functions."""
    adv_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failures": [],
    }

    def record_test(name: str, passed: bool, detail: str = ""):
        adv_results["total_tests"] += 1
        if passed:
            adv_results["passed_tests"] += 1
        else:
            adv_results["failures"].append({"name": name, "detail": detail})

    # Test 1: Corrupt / Extreme Coordinates
    try:
        payload = {
            "metadata": {"imageWidth": 1000, "imageHeight": 2000, "fileName": "extreme_coords.jpg"},
            "blocks": [
                {
                    "lines": [
                        {
                            "text": "Extreme Coordinates",
                            "cornerPoints": [
                                {"x": -999999.0, "y": -999999.0},
                                {"x": 999999.0, "y": -999999.0},
                                {"x": 999999.0, "y": 999999.0},
                                {"x": -999999.0, "y": 999999.0},
                            ],
                        }
                    ]
                }
            ],
        }
        doc = parse_mlkit_json_data(payload)
        pts = doc.pages[0].regions[0].bbox.points
        expected = ((0.0, 0.0), (1000.0, 0.0), (1000.0, 2000.0), (0.0, 2000.0))
        record_test("extreme_coordinate_clamping", pts == expected, f"pts={pts}")
    except Exception as e:
        record_test("extreme_coordinate_clamping", False, str(e))

    # Test 2: Bounding box fallback from boundingBox rect
    try:
        payload = {
            "metadata": {"imageWidth": 500, "imageHeight": 500},
            "blocks": [
                {
                    "lines": [
                        {
                            "text": "Rect BBox",
                            "boundingBox": {"left": 10.0, "top": 20.0, "right": 80.0, "bottom": 60.0},
                        }
                    ]
                }
            ],
        }
        doc = parse_mlkit_json_data(payload)
        pts = doc.pages[0].regions[0].bbox.points
        expected = ((10.0, 20.0), (80.0, 20.0), (80.0, 60.0), (10.0, 60.0))
        record_test("bbox_rect_fallback", pts == expected, f"pts={pts}")
    except Exception as e:
        record_test("bbox_rect_fallback", False, str(e))

    # Test 3: Completely empty blocks array
    try:
        payload = {
            "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "empty.jpg"},
            "fullText": "",
            "blocks": [],
        }
        doc = parse_mlkit_json_data(payload)
        doc_text = build_document_text(doc)
        record_test("empty_blocks", doc_text.raw_text == "" and len(doc.pages[0].regions) == 0)
    except Exception as e:
        record_test("empty_blocks", False, str(e))

    # Test 4: Block with missing lines array falls back to block text
    try:
        payload = {
            "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "no_lines.jpg"},
            "blocks": [
                {
                    "text": "Block Level Only",
                    "cornerPoints": [{"x": 10, "y": 10}, {"x": 50, "y": 10}, {"x": 50, "y": 30}, {"x": 10, "y": 30}],
                }
            ],
        }
        doc = parse_mlkit_json_data(payload)
        record_test("block_level_text_fallback", len(doc.pages[0].regions) == 1 and doc.pages[0].regions[0].text == "Block Level Only")
    except Exception as e:
        record_test("block_level_text_fallback", False, str(e))

    # Test 5: Unicode Diacritics and Combining Characters
    try:
        complex_vn = "ĐƠN THUỐC: Cefuroxim 500mg (20 Viên) - Uống 1 viên x 2 lần/ngày (sáng - chiều) sau ăn"
        payload = {
            "metadata": {"imageWidth": 1000, "imageHeight": 1000, "fileName": "vn.jpg"},
            "fullText": complex_vn,
            "blocks": [{"lines": [{"text": complex_vn}]}],
        }
        doc = parse_mlkit_json_data(payload)
        doc_text = build_document_text(doc)
        record_test("unicode_diacritics_reconstruction", doc_text.raw_text == complex_vn)
    except Exception as e:
        record_test("unicode_diacritics_reconstruction", False, str(e))

    # Test 6: Huge Document Scaling (5000 lines)
    try:
        t_scale_0 = time.perf_counter()
        lines = [{"text": f"Line {i} - Paracetamol 500mg - 2 vien"} for i in range(5000)]
        payload = {
            "metadata": {"imageWidth": 2000, "imageHeight": 50000, "fileName": "huge_doc.jpg"},
            "blocks": [{"lines": lines}],
        }
        doc = parse_mlkit_json_data(payload)
        doc_text = build_document_text(doc)
        t_scale_1 = time.perf_counter()
        elapsed = t_scale_1 - t_scale_0
        record_test("scale_5000_lines", len(doc.pages[0].regions) == 5000 and len(doc_text.regions) == 5000, f"elapsed={elapsed:.4f}s")
    except Exception as e:
        record_test("scale_5000_lines", False, str(e))

    # Test 7: None / missing metadata handling
    try:
        payload = {
            "blocks": [{"lines": [{"text": "Hello"}]}]
        }
        doc = parse_mlkit_json_data(payload)
        record_test("missing_metadata_defaults", doc.document_id == "doc_unknown" and doc.pages[0].width == 1000 and doc.pages[0].height == 1000)
    except Exception as e:
        record_test("missing_metadata_defaults", False, str(e))

    # Test 8: Empty document ID rejection
    try:
        parse_mlkit_json_data({}, document_id="")
        record_test("reject_empty_doc_id", False, "Failed to raise ValueError on empty doc_id")
    except ValueError:
        record_test("reject_empty_doc_id", True)
    except Exception as e:
        record_test("reject_empty_doc_id", False, str(e))

    return adv_results


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING EMPIRICAL VERIFICATION ACROSS ALL 437 OCR CAPTURES")
    print("=" * 70)
    emp_results = run_full_empirical_verification()

    print("\n" + "=" * 70)
    print("EMPIRICAL VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total Captures Checked:        {emp_results['files_checked']} / {emp_results['total_files']}")
    print(f"Exact FullText Matches:        {emp_results['exact_raw_text_matches']} / {emp_results['total_files']} ({(emp_results['exact_raw_text_matches']/emp_results['total_files'])*100:.2f}%)")
    print(f"Span Slice Matches:            {emp_results['span_slice_matches']} / {emp_results['total_files']} ({(emp_results['span_slice_matches']/emp_results['total_files'])*100:.2f}%)")
    print(f"Reading Order Monotonic Valid: {emp_results['reading_order_monotonic_valid']} / {emp_results['total_files']} ({(emp_results['reading_order_monotonic_valid']/emp_results['total_files'])*100:.2f}%)")
    print(f"Region ID Unique Valid:        {emp_results['region_id_unique_valid']} / {emp_results['total_files']} ({(emp_results['region_id_unique_valid']/emp_results['total_files'])*100:.2f}%)")
    print(f"BBox Bounds Valid:             {emp_results['bbox_bounds_valid']} / {emp_results['total_files']} ({(emp_results['bbox_bounds_valid']/emp_results['total_files'])*100:.2f}%)")
    print(f"Total Regions Processed:       {emp_results['total_regions']}")
    print(f"Total Characters Reconstructed:{emp_results['total_characters']}")
    print(f"Known Empty Captures (0 regions): {len(emp_results['empty_files'])} -> {emp_results['empty_files']}")

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    bench = emp_results["benchmark"]
    print(f"Total Wall Time:               {bench['total_wall_time_sec']:.4f} s")
    print(f"Total CPU Time:                {bench['total_cpu_time_sec']:.4f} s")
    print(f"Throughput:                    {bench['throughput_files_per_sec']:.2f} captures/sec")
    print(f"Average Latency:               {bench['avg_latency_ms']:.2f} ms/capture")
    print(f"Min Latency:                   {bench['min_latency_ms']:.2f} ms")
    print(f"Max Latency:                   {bench['max_latency_ms']:.2f} ms")
    print(f"P50 Latency:                   {bench['p50_latency_ms']:.2f} ms")
    print(f"P95 Latency:                   {bench['p95_latency_ms']:.2f} ms")
    print(f"P99 Latency:                   {bench['p99_latency_ms']:.2f} ms")
    print(f"Peak Traced Memory:            {bench['traced_peak_mem_mb']:.2f} MB")
    print(f"Final Traced Memory:           {bench['traced_final_mem_mb']:.2f} MB")
    print(f"Peak Process RSS:              {bench['peak_rss_mb']:.2f} MB")
    print(f"Batch Function Throughput:     {emp_results['batch_ingest_fps']:.2f} captures/sec ({emp_results['batch_ingest_count']} in {emp_results['batch_ingest_time_sec']:.4f} s)")

    print("\n" + "=" * 70)
    print("RUNNING ADVERSARIAL STRESS TESTS")
    print("=" * 70)
    adv_results = run_adversarial_stress_tests()
    print(f"Adversarial Tests Passed:      {adv_results['passed_tests']} / {adv_results['total_tests']}")
    if adv_results["failures"]:
        print(f"Adversarial Failures:          {adv_results['failures']}")

    # Dump detailed JSON results for handoff report
    output_json = Path(".agents/challenger_m0_2/empirical_results.json")
    with open(output_json, "w", encoding="utf-8") as f:
        # remove raw latencies list to keep file concise
        emp_results.pop("file_latencies_ms", None)
        json.dump({"empirical": emp_results, "adversarial": adv_results}, f, indent=2)
    print(f"\n[+] Saved detailed verification dump to {output_json}")
