import glob
import json
import math
import os
import statistics


def analyze_ocr_results(output_dir="data/output"):
    json_files = glob.glob(f"{output_dir}/**/*.json", recursive=True)
    if not json_files:
        print(f"No OCR JSON files found in {output_dir}")
        return

    print(f"\n=======================================================")
    print(f"   RxIE Batch OCR Quality & Geometry Analysis ({len(json_files)} images)")
    print(f"=======================================================\n")

    confidences = []
    line_counts = []
    block_counts = []
    token_counts = []
    dominant_angles = []
    skew_angles = []

    rot_0 = 0
    rot_90 = 0
    rot_180 = 0
    rot_270 = 0
    skew_minor = 0  # 2° to 15°
    skew_negligible = 0  # < 2°
    skew_severe = 0  # > 15°

    for path in json_files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        blocks = data.get("blocks", [])
        block_counts.append(len(blocks))

        lines = []
        file_angles = []
        file_confidences = []
        words_count = 0

        for b in blocks:
            for l in b.get("lines", []):
                lines.append(l)
                text = l.get("text", "")
                words_count += len(text.split())
                conf = l.get("confidence")
                if conf is not None:
                    file_confidences.append(conf)
                    confidences.append(conf)
                angle = l.get("angle")
                if angle is not None:
                    file_angles.append(angle)

        line_counts.append(len(lines))
        token_counts.append(words_count)

        if file_angles:
            med_angle = statistics.median(file_angles)
            dominant_angles.append(med_angle)

            # Categorize orientation
            norm_angle = (med_angle % 360 + 360) % 360
            if 315 <= norm_angle or norm_angle < 45:
                rot_0 += 1
                skew = abs(med_angle if med_angle <= 180 else med_angle - 360)
            elif 45 <= norm_angle < 135:
                rot_90 += 1
                skew = abs(med_angle - 90)
            elif 135 <= norm_angle < 225:
                rot_180 += 1
                skew = abs(med_angle - 180)
            else:
                rot_270 += 1
                skew = abs(med_angle - 270)

            skew_angles.append(skew)
            if skew < 2.0:
                skew_negligible += 1
            elif 2.0 <= skew <= 15.0:
                skew_minor += 1
            else:
                skew_severe += 1

    print(f"📊 [1. Khối lượng & Nhận diện Văn bản]")
    print(f"   • Tổng số ảnh đã OCR      : {len(json_files)}")
    print(f"   • Trung bình blocks/ảnh   : {statistics.mean(block_counts):.1f}")
    print(f"   • Trung bình lines/ảnh    : {statistics.mean(line_counts):.1f}")
    print(f"   • Trung bình từ (words)/ảnh: {statistics.mean(token_counts):.1f}")

    if confidences:
        print(f"\n🎯 [2. Phân bố Độ tự tin (Confidence)]")
        print(f"   • Mean Confidence         : {statistics.mean(confidences)*100:.2f}%")
        print(f"   • Median Confidence       : {statistics.median(confidences)*100:.2f}%")
        print(f"   • Min / Max Confidence    : {min(confidences)*100:.2f}% / {max(confidences)*100:.2f}%")

    print(f"\n📐 [3. Phân bố Góc xoay & Skew (Geometry Analysis)]")
    print(f"   • Hướng xoay 0° (chuẩn)   : {rot_0} ảnh ({rot_0/len(json_files)*100:.1f}%)")
    print(f"   • Hướng xoay 90°          : {rot_90} ảnh ({rot_90/len(json_files)*100:.1f}%)")
    print(f"   • Hướng xoay 180°         : {rot_180} ảnh ({rot_180/len(json_files)*100:.1f}%)")
    print(f"   • Hướng xoay 270°         : {rot_270} ảnh ({rot_270/len(json_files)*100:.1f}%)")
    print(f"   ---")
    print(f"   • Độ lệch thẳng (<2°)     : {skew_negligible} ảnh ({skew_negligible/len(json_files)*100:.1f}%) -> Không cần deskew")
    print(f"   • Nghiêng nhỏ (2°-15°)    : {skew_minor} ảnh ({skew_minor/len(json_files)*100:.1f}%) -> ĐỀ XUẤT DESKEW")
    print(f"   • Nghiêng lớn (>15°)      : {skew_severe} ảnh ({skew_severe/len(json_files)*100:.1f}%) -> Nghi ngờ phối cảnh/chụp xiên")

    print(f"\n=======================================================\n")


if __name__ == "__main__":
    analyze_ocr_results()
