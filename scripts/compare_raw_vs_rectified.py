import glob
import json
import os
import statistics


def load_ocr_metrics(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    blocks = data.get("blocks", [])
    lines = []
    confidences = []
    angles = []
    total_words = 0
    full_text = data.get("fullText", "")

    for b in blocks:
        for l in b.get("lines", []):
            lines.append(l)
            text = l.get("text", "")
            total_words += len(text.split())
            if "confidence" in l and l["confidence"] is not None:
                confidences.append(l["confidence"])
            if "angle" in l and l["angle"] is not None:
                angles.append(l["angle"])

    mean_conf = statistics.mean(confidences) if confidences else 0.0
    median_conf = statistics.median(confidences) if confidences else 0.0
    med_angle = statistics.median(angles) if angles else 0.0

    return {
        "block_count": len(blocks),
        "line_count": len(lines),
        "word_count": total_words,
        "char_count": len(full_text),
        "mean_confidence": mean_conf,
        "median_confidence": median_conf,
        "median_angle": med_angle,
        "full_text": full_text,
    }


def run_comparison(raw_dir="data/output", rect_dir="data/output_rectified"):
    raw_index = {}
    for p in glob.glob(f"{raw_dir}/**/*.json", recursive=True):
        bname = os.path.splitext(os.path.basename(p))[0]
        raw_index[bname] = p

    rect_index = {}
    for p in glob.glob(f"{rect_dir}/**/*.json", recursive=True):
        bname = os.path.splitext(os.path.basename(p))[0]
        rect_index[bname] = p

    common_keys = sorted(set(raw_index.keys()) & set(rect_index.keys()))
    if not common_keys:
        print(f"No common OCR JSON files between {raw_dir} and {rect_dir}")
        return

    print(f"\n=======================================================")
    print(f"   PAIRED COMPARISON: OCR_RAW vs OCR_RECTIFIED ({len(common_keys)} images)")
    print(f"=======================================================\n")

    raw_confs, rect_confs = [], []
    raw_words, rect_words = [], []
    raw_lines, rect_lines = [], []

    improved_conf_count = 0
    degraded_conf_count = 0
    equal_conf_count = 0

    p6_selected_rectified = 0
    p6_selected_raw = 0

    # Load preprocessing summary to know which were rotated/deskewed
    prep_summary = {}
    if os.path.exists("data/rectified_200/preprocessing_summary.json"):
        with open("data/rectified_200/preprocessing_summary.json", "r", encoding="utf-8") as f:
            meta_data = json.load(f)
            for rec in meta_data.get("records", []):
                prep_summary[rec["image_id"]] = rec.get("preprocessing", {})

    rotated_improvements = []
    deskewed_angle_reductions = []

    for k in common_keys:
        raw_m = load_ocr_metrics(raw_index[k])
        rect_m = load_ocr_metrics(rect_index[k])

        raw_confs.append(raw_m["mean_confidence"])
        rect_confs.append(rect_m["mean_confidence"])
        raw_words.append(raw_m["word_count"])
        rect_words.append(rect_m["word_count"])
        raw_lines.append(raw_m["line_count"])
        rect_lines.append(rect_m["line_count"])

        d_conf = rect_m["mean_confidence"] - raw_m["mean_confidence"]
        if d_conf > 0.01:
            improved_conf_count += 1
        elif d_conf < -0.01:
            degraded_conf_count += 1
        else:
            equal_conf_count += 1

        # P6 Quality Selector logic:
        # Select rectified if confidence is better and token loss is negligible
        if rect_m["mean_confidence"] >= raw_m["mean_confidence"] - 0.02 and rect_m["word_count"] >= raw_m["word_count"] * 0.9:
            p6_selected_rectified += 1
        else:
            p6_selected_raw += 1

        # Track rotation impact
        prep_info = prep_summary.get(k, {})
        if prep_info.get("orientation_rotation", 0) != 0:
            rotated_improvements.append({
                "id": k,
                "rotation": prep_info["orientation_rotation"],
                "raw_words": raw_m["word_count"],
                "rect_words": rect_m["word_count"],
                "raw_conf": raw_m["mean_confidence"],
                "rect_conf": rect_m["mean_confidence"],
            })

    print(f"📊 [1. Tổng hợp Chỉ số Trung bình Toàn bộ]")
    print(f"   • Số lượng ảnh so sánh paired: {len(common_keys)}")
    print(f"   • Mean Confidence: RAW = {statistics.mean(raw_confs)*100:.2f}%  ──►  RECTIFIED = {statistics.mean(rect_confs)*100:.2f}% (Δ = +{(statistics.mean(rect_confs)-statistics.mean(raw_confs))*100:.2f}%)")
    print(f"   • Median Confidence: RAW = {statistics.median(raw_confs)*100:.2f}%  ──►  RECTIFIED = {statistics.median(rect_confs)*100:.2f}%")
    print(f"   • Trung bình Words/ảnh: RAW = {statistics.mean(raw_words):.1f}  ──►  RECTIFIED = {statistics.mean(rect_words):.1f}")
    print(f"   • Trung bình Lines/ảnh: RAW = {statistics.mean(raw_lines):.1f}  ──►  RECTIFIED = {statistics.mean(rect_lines):.1f}")

    print(f"\n📈 [2. Phân bố Chất lượng & Degradation Rate]")
    print(f"   • Ảnh cải thiện Confidence (>+1%)  : {improved_conf_count} ({improved_conf_count/len(common_keys)*100:.1f}%)")
    print(f"   • Ảnh giữ nguyên tương đương (±1%) : {equal_conf_count} ({equal_conf_count/len(common_keys)*100:.1f}%)")
    print(f"   • Degradation Rate (Bị giảm >-1%)  : {degraded_conf_count} ({degraded_conf_count/len(common_keys)*100:.1f}%)")

    print(f"\n🤖 [3. Quyết định của P6 Quality Selector]")
    print(f"   • Tự động chọn RECTIFIED           : {p6_selected_rectified} ({p6_selected_rectified/len(common_keys)*100:.1f}%)")
    print(f"   • Fallback về RAW an toàn          : {p6_selected_raw} ({p6_selected_raw/len(common_keys)*100:.1f}%)")

    if rotated_improvements:
        print(f"\n🔄 [4. Tác động của P1 Orientation trên {len(rotated_improvements)} ảnh bị xoay]")
        r_raw_w = statistics.mean([x["raw_words"] for x in rotated_improvements])
        r_rect_w = statistics.mean([x["rect_words"] for x in rotated_improvements])
        r_raw_c = statistics.mean([x["raw_conf"] for x in rotated_improvements])
        r_rect_c = statistics.mean([x["rect_conf"] for x in rotated_improvements])
        print(f"   • Số từ nhận diện: RAW = {r_raw_w:.1f} từ  ──►  RECTIFIED = {r_rect_w:.1f} từ (Phục hồi gấp {r_rect_w/max(r_raw_w, 1):.1f} lần)")
        print(f"   • Confidence     : RAW = {r_raw_c*100:.2f}% ──►  RECTIFIED = {r_rect_c*100:.2f}%")

    print(f"\n=======================================================\n")


if __name__ == "__main__":
    run_comparison()
