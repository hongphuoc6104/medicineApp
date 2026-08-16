import glob
import json
import os
import statistics


def load_branch_metrics(branch_dir):
    json_files = glob.glob(f"{branch_dir}/**/*.json", recursive=True)
    if not json_files:
        return None

    by_image = {}
    confidences = []
    word_counts = []
    line_counts = []
    residual_angles = []

    for p in json_files:
        bname = os.path.splitext(os.path.basename(p))[0]
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        blocks = data.get("blocks", [])
        lines = []
        file_confs = []
        file_angles = []
        total_words = 0

        for b in blocks:
            for l in b.get("lines", []):
                lines.append(l)
                t = l.get("text", "")
                total_words += len(t.split())
                if "confidence" in l and l["confidence"] is not None:
                    file_confs.append(l["confidence"])
                    confidences.append(l["confidence"])
                if "angle" in l and l["angle"] is not None:
                    # compute residual angle from closest 0/90/180/270
                    raw_a = l["angle"]
                    res_a = min(abs(raw_a), abs(raw_a - 90), abs(raw_a - 180), abs(raw_a - 270), abs(raw_a - 360))
                    file_angles.append(res_a)
                    residual_angles.append(res_a)

        m_conf = statistics.mean(file_confs) if file_confs else 0.0
        m_angle = statistics.mean(file_angles) if file_angles else 0.0

        by_image[bname] = {
            "mean_confidence": m_conf,
            "word_count": total_words,
            "line_count": len(lines),
            "mean_residual_angle": m_angle,
        }

    return {
        "count": len(by_image),
        "mean_confidence": statistics.mean(confidences) if confidences else 0.0,
        "median_confidence": statistics.median(confidences) if confidences else 0.0,
        "mean_residual_angle": statistics.mean(residual_angles) if residual_angles else 0.0,
        "median_residual_angle": statistics.median(residual_angles) if residual_angles else 0.0,
        "mean_words": statistics.mean(word_counts) if word_counts else (sum(x["word_count"] for x in by_image.values()) / len(by_image)),
        "mean_lines": statistics.mean(line_counts) if line_counts else (sum(x["line_count"] for x in by_image.values()) / len(by_image)),
        "by_image": by_image,
    }


def generate_ablation_report():
    branches = {
        "P0 RAW": "data/output",
        "P1 Rotation": "data/output_p1",
        "P2 Perspective": "data/output_p2",
        "P3 Deskew": "data/output_p3",
        "P4 Full Geometry": "data/output_rectified",
    }

    results = {}
    for name, path in branches.items():
        res = load_branch_metrics(path)
        if res:
            results[name] = res

    print("\n" + "=" * 90)
    print("                    RxIE PREPROCESSING ABLATION STUDY (200 PAIRED IMAGES)")
    print("=" * 90)

    header = f"{'Pipeline ID & Description':<25} | {'Mean Conf':<10} | {'Median Conf':<11} | {'Mean Angle':<11} | {'Med Angle':<10} | {'Mean Words':<10} | {'Status'}"
    print(header)
    print("-" * 90)

    for name, path in branches.items():
        if name in results:
            r = results[name]
            print(
                f"{name:<25} | "
                f"{r['mean_confidence']*100:>8.2f}% | "
                f"{r['median_confidence']*100:>9.2f}% | "
                f"{r['mean_residual_angle']:>9.2f}° | "
                f"{r['median_residual_angle']:>8.2f}° | "
                f"{r['mean_words']:>10.1f} | "
                f"✅ Done ({r['count']}/200)"
            )
        else:
            print(f"{name:<25} | {'--':>9} | {'--':>10} | {'--':>10} | {'--':>9} | {'--':>10} | ⏳ In Progress")

    print("=" * 90 + "\n")


if __name__ == "__main__":
    generate_ablation_report()
