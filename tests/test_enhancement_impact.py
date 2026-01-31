#!/usr/bin/env python3
"""
Test Enhancement Impact - So sánh OCR với và không có bước S4 Enhancement

Mục đích:
- Đo lường tác động của bước S4 (Enhancement) lên chất lượng OCR
- So sánh: S3 → S5 vs S3 → S4 → S5

Usage:
    python tests/test_enhancement_impact.py
    python tests/test_enhancement_impact.py --verbose
"""

import sys
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from datetime import datetime

import cv2

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class ComparisonResult:
    """Kết quả so sánh cho một ảnh."""
    image_file: str
    
    # Không có Enhancement (S3 → S5)
    no_enhance_drug_accuracy: float = 0.0
    no_enhance_quantity_accuracy: float = 0.0
    no_enhance_dosage_accuracy: float = 0.0
    no_enhance_overall: float = 0.0
    no_enhance_text_blocks: int = 0
    
    # Có Enhancement (S3 → S4 → S5)
    with_enhance_drug_accuracy: float = 0.0
    with_enhance_quantity_accuracy: float = 0.0
    with_enhance_dosage_accuracy: float = 0.0
    with_enhance_overall: float = 0.0
    with_enhance_text_blocks: int = 0
    
    # Improvement
    drug_improvement: float = 0.0
    quantity_improvement: float = 0.0
    dosage_improvement: float = 0.0
    overall_improvement: float = 0.0


def normalize_text(text: str) -> str:
    """Chuẩn hóa text để so sánh."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF]', '', text)
    return text


def check_drug_in_text(drug_name: str, ocr_text: str) -> Tuple[bool, float]:
    """Kiểm tra tên thuốc có trong OCR text không."""
    parts = re.findall(r'[A-Za-z_]+|\d+mg|\d+ml', drug_name)
    ocr_lower = ocr_text.lower()
    
    found_parts = 0
    for part in parts:
        if part.lower() in ocr_lower:
            found_parts += 1
    
    if not parts:
        return False, 0.0
    
    similarity = found_parts / len(parts)
    return similarity >= 0.5, similarity


def check_quantity_in_text(quantity: int, ocr_text: str) -> bool:
    """Kiểm tra số lượng có trong OCR text không."""
    return str(quantity) in ocr_text


def check_dosage_in_text(dosage: str, ocr_text: str) -> Tuple[bool, float]:
    """Kiểm tra hướng dẫn sử dụng có trong OCR text không."""
    keywords = {
        'uong': ['uong', 'uống', 'ung'],
        'ngay': ['ngay', 'ngày'],
        'vien': ['vien', 'viên'],
        'sang': ['sang', 'sáng'],
        'toi': ['toi', 'tối'],
        'sau an': ['sau an', 'sau ăn', 'sau án'],
        'truoc': ['truoc', 'trước'],
        'tiem': ['tiem', 'tiêm'],
    }
    
    dosage_lower = dosage.lower()
    ocr_lower = ocr_text.lower()
    
    found_count = 0
    total_count = 0
    
    for key, variants in keywords.items():
        key_in_dosage = any(v in dosage_lower for v in variants)
        if key_in_dosage:
            total_count += 1
            key_in_ocr = any(v in ocr_lower for v in variants)
            if key_in_ocr:
                found_count += 1
    
    if total_count == 0:
        return False, 0.0
    
    similarity = found_count / total_count
    return similarity >= 0.5, similarity


def evaluate_ocr_result(ocr_text: str, ground_truth: Dict) -> Tuple[float, float, float, float]:
    """
    Đánh giá kết quả OCR so với ground truth.
    Returns: (drug_accuracy, quantity_accuracy, dosage_accuracy, overall)
    """
    medications = ground_truth.get("medications", [])
    drug_scores = []
    quantity_scores = []
    dosage_scores = []
    
    for med in medications:
        drug_name = med.get("drug_name", "")
        quantity = med.get("quantity", 0)
        dosage = med.get("dosage_instruction", "")
        
        # Check drug name
        _, drug_sim = check_drug_in_text(drug_name, ocr_text)
        drug_scores.append(drug_sim)
        
        # Check quantity
        qty_found = check_quantity_in_text(quantity, ocr_text)
        quantity_scores.append(1.0 if qty_found else 0.0)
        
        # Check dosage
        _, dosage_sim = check_dosage_in_text(dosage, ocr_text)
        dosage_scores.append(dosage_sim)
    
    avg_drug = sum(drug_scores) / len(drug_scores) if drug_scores else 0
    avg_qty = sum(quantity_scores) / len(quantity_scores) if quantity_scores else 0
    avg_dosage = sum(dosage_scores) / len(dosage_scores) if dosage_scores else 0
    overall = (avg_drug + avg_qty + avg_dosage) / 3
    
    return avg_drug, avg_qty, avg_dosage, overall


def run_comparison_test(verbose: bool = False):
    """Chạy test so sánh với và không có Enhancement."""
    
    print("=" * 70)
    print("🔬 TEST ENHANCEMENT IMPACT (S4)")
    print("=" * 70)
    print("So sánh: S3 → S5 (không Enhancement) vs S3 → S4 → S5 (có Enhancement)")
    print("-" * 70)
    
    # Import services
    from services import S4EnhancementService, S5OcrService
    import yaml
    
    # Load config
    config_path = ROOT / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Load ground truth
    gt_path = ROOT / "tests" / "ground_truth.json"
    if not gt_path.exists():
        print(f"❌ Ground truth file not found: {gt_path}")
        return
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        ground_truth_list = json.load(f)
    
    print(f"✅ Loaded {len(ground_truth_list)} ground truth entries")
    
    # Initialize services
    enhance_config = config.get("enhancement", {})
    brightness_config = enhance_config.get("brightness", {})
    sharpness_config = enhance_config.get("sharpness", {})
    
    s4_enhancement = S4EnhancementService(
        enabled=True,  # Luôn enabled để có thể so sánh
        brightnessEnabled=brightness_config.get("enabled", True),
        brightnessClipLimit=brightness_config.get("clip_limit", 2.5),
        brightnessTileSize=brightness_config.get("tile_size", 8),
        sharpnessEnabled=sharpness_config.get("enabled", True),
        sharpnessSigma=sharpness_config.get("sigma", 1.0),
        sharpnessAmount=sharpness_config.get("amount", 1.5),
    )
    
    ocr_config = config.get("ocr", {})
    s5_ocr = S5OcrService(
        enabled=True,
        lang=ocr_config.get("lang", "vi"),
        useGpu=ocr_config.get("use_gpu", False),
        confThreshold=ocr_config.get("confidence_threshold", 0.5),
    )
    
    # Đường dẫn ảnh cropped (output từ S3)
    cropped_dir = ROOT / "run" / "test_final2" / "step3_cropped"
    
    results: List[ComparisonResult] = []
    
    print(f"\n📁 Source: {cropped_dir}")
    print("=" * 70)
    
    for gt in ground_truth_list:
        image_file = gt.get("image_file", "")
        image_path = cropped_dir / image_file
        
        if not image_path.exists():
            print(f"⚠️  Image not found: {image_file}")
            continue
        
        print(f"\n📷 Testing: {image_file}")
        print("-" * 50)
        
        # Load image (output từ S3 - đã crop)
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"   ❌ Cannot load image")
            continue
        
        result = ComparisonResult(image_file=image_file)
        
        # ========== TEST 1: KHÔNG CÓ ENHANCEMENT (S3 → S5) ==========
        print("   🔴 Test 1: Không có S4 Enhancement...")
        ocr_result_no_enhance = s5_ocr.extractText(image, "test_no_enhance")
        
        if ocr_result_no_enhance.hasText:
            result.no_enhance_text_blocks = ocr_result_no_enhance.numBlocks
            (result.no_enhance_drug_accuracy, 
             result.no_enhance_quantity_accuracy,
             result.no_enhance_dosage_accuracy,
             result.no_enhance_overall) = evaluate_ocr_result(
                ocr_result_no_enhance.fullText, gt
            )
            
            if verbose:
                print(f"      Text blocks: {result.no_enhance_text_blocks}")
                print(f"      OCR Text (first 200 chars): {ocr_result_no_enhance.fullText[:200]}...")
        else:
            print("      ⚠️  No text extracted")
        
        # ========== TEST 2: CÓ ENHANCEMENT (S3 → S4 → S5) ==========
        print("   🟢 Test 2: Có S4 Enhancement...")
        enhance_result = s4_enhancement.enhance(image, "test_enhance")
        
        if enhance_result.hasEnhancedImage:
            enhanced_image = enhance_result.enhancedImage
            ocr_result_with_enhance = s5_ocr.extractText(enhanced_image, "test_with_enhance")
            
            if ocr_result_with_enhance.hasText:
                result.with_enhance_text_blocks = ocr_result_with_enhance.numBlocks
                (result.with_enhance_drug_accuracy,
                 result.with_enhance_quantity_accuracy,
                 result.with_enhance_dosage_accuracy,
                 result.with_enhance_overall) = evaluate_ocr_result(
                    ocr_result_with_enhance.fullText, gt
                )
                
                if verbose:
                    print(f"      Text blocks: {result.with_enhance_text_blocks}")
                    print(f"      OCR Text (first 200 chars): {ocr_result_with_enhance.fullText[:200]}...")
            else:
                print("      ⚠️  No text extracted")
        else:
            print("      ⚠️  Enhancement failed")
        
        # ========== TÍNH IMPROVEMENT ==========
        result.drug_improvement = result.with_enhance_drug_accuracy - result.no_enhance_drug_accuracy
        result.quantity_improvement = result.with_enhance_quantity_accuracy - result.no_enhance_quantity_accuracy
        result.dosage_improvement = result.with_enhance_dosage_accuracy - result.no_enhance_dosage_accuracy
        result.overall_improvement = result.with_enhance_overall - result.no_enhance_overall
        
        # Print comparison
        print(f"\n   📊 COMPARISON:")
        print(f"   {'Metric':<20} {'No S4':<12} {'With S4':<12} {'Change':<12}")
        print(f"   {'-' * 56}")
        print(f"   {'Drug Accuracy':<20} {result.no_enhance_drug_accuracy:>10.1%} {result.with_enhance_drug_accuracy:>10.1%} {result.drug_improvement:>+10.1%}")
        print(f"   {'Quantity Accuracy':<20} {result.no_enhance_quantity_accuracy:>10.1%} {result.with_enhance_quantity_accuracy:>10.1%} {result.quantity_improvement:>+10.1%}")
        print(f"   {'Dosage Accuracy':<20} {result.no_enhance_dosage_accuracy:>10.1%} {result.with_enhance_dosage_accuracy:>10.1%} {result.dosage_improvement:>+10.1%}")
        print(f"   {'OVERALL':<20} {result.no_enhance_overall:>10.1%} {result.with_enhance_overall:>10.1%} {result.overall_improvement:>+10.1%}")
        
        results.append(result)
    
    # ========== SUMMARY ==========
    if results:
        print("\n" + "=" * 70)
        print("📊 OVERALL SUMMARY - ENHANCEMENT IMPACT")
        print("=" * 70)
        
        # Calculate averages
        avg_no_enhance = sum(r.no_enhance_overall for r in results) / len(results)
        avg_with_enhance = sum(r.with_enhance_overall for r in results) / len(results)
        avg_improvement = sum(r.overall_improvement for r in results) / len(results)
        
        avg_drug_no = sum(r.no_enhance_drug_accuracy for r in results) / len(results)
        avg_drug_with = sum(r.with_enhance_drug_accuracy for r in results) / len(results)
        avg_drug_imp = sum(r.drug_improvement for r in results) / len(results)
        
        avg_qty_no = sum(r.no_enhance_quantity_accuracy for r in results) / len(results)
        avg_qty_with = sum(r.with_enhance_quantity_accuracy for r in results) / len(results)
        avg_qty_imp = sum(r.quantity_improvement for r in results) / len(results)
        
        avg_dosage_no = sum(r.no_enhance_dosage_accuracy for r in results) / len(results)
        avg_dosage_with = sum(r.with_enhance_dosage_accuracy for r in results) / len(results)
        avg_dosage_imp = sum(r.dosage_improvement for r in results) / len(results)
        
        print(f"\n{'Metric':<25} {'No S4 (avg)':<15} {'With S4 (avg)':<15} {'Improvement':<15}")
        print(f"{'-' * 70}")
        print(f"{'🏷️  Drug Name Accuracy':<25} {avg_drug_no:>12.1%} {avg_drug_with:>12.1%} {avg_drug_imp:>+12.1%}")
        print(f"{'🔢 Quantity Accuracy':<25} {avg_qty_no:>12.1%} {avg_qty_with:>12.1%} {avg_qty_imp:>+12.1%}")
        print(f"{'💊 Dosage Accuracy':<25} {avg_dosage_no:>12.1%} {avg_dosage_with:>12.1%} {avg_dosage_imp:>+12.1%}")
        print(f"{'⭐ OVERALL':<25} {avg_no_enhance:>12.1%} {avg_with_enhance:>12.1%} {avg_improvement:>+12.1%}")
        
        print("\n" + "-" * 70)
        
        # Verdict
        if avg_improvement > 0.01:  # > 1% improvement
            print(f"✅ VERDICT: Bước S4 Enhancement CÓ CẢI THIỆN kết quả OCR (+{avg_improvement:.1%})")
            print("   → Nên giữ bước S4 trong pipeline")
        elif avg_improvement < -0.01:  # < -1% improvement
            print(f"❌ VERDICT: Bước S4 Enhancement LÀM GIẢM kết quả OCR ({avg_improvement:.1%})")
            print("   → Nên bỏ bước S4 hoặc điều chỉnh tham số")
        else:
            print(f"⚖️  VERDICT: Bước S4 Enhancement KHÔNG CÓ TÁC ĐỘNG đáng kể ({avg_improvement:+.1%})")
            print("   → Có thể bỏ S4 để tăng tốc pipeline")
        
        print("=" * 70)
        
        # Count improvements vs degradations
        improved = sum(1 for r in results if r.overall_improvement > 0.01)
        degraded = sum(1 for r in results if r.overall_improvement < -0.01)
        unchanged = len(results) - improved - degraded
        
        print(f"\n📈 Per-image breakdown:")
        print(f"   Improved:  {improved}/{len(results)} ({improved/len(results):.0%})")
        print(f"   Degraded:  {degraded}/{len(results)} ({degraded/len(results):.0%})")
        print(f"   Unchanged: {unchanged}/{len(results)} ({unchanged/len(results):.0%})")
        
        # Save detailed report
        report_path = ROOT / "run" / "test_final2" / "enhancement_impact_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("ENHANCEMENT IMPACT REPORT\n")
            f.write("=" * 70 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Images tested: {len(results)}\n\n")
            
            f.write(f"{'Metric':<25} {'No S4':<15} {'With S4':<15} {'Change':<15}\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Drug Accuracy':<25} {avg_drug_no:>12.1%} {avg_drug_with:>12.1%} {avg_drug_imp:>+12.1%}\n")
            f.write(f"{'Quantity Accuracy':<25} {avg_qty_no:>12.1%} {avg_qty_with:>12.1%} {avg_qty_imp:>+12.1%}\n")
            f.write(f"{'Dosage Accuracy':<25} {avg_dosage_no:>12.1%} {avg_dosage_with:>12.1%} {avg_dosage_imp:>+12.1%}\n")
            f.write(f"{'OVERALL':<25} {avg_no_enhance:>12.1%} {avg_with_enhance:>12.1%} {avg_improvement:>+12.1%}\n")
            
            f.write("\n\nPER-IMAGE DETAILS:\n")
            f.write("=" * 70 + "\n")
            for r in results:
                f.write(f"\n{r.image_file}\n")
                f.write(f"  No S4:   Drug={r.no_enhance_drug_accuracy:.0%}, Qty={r.no_enhance_quantity_accuracy:.0%}, Dosage={r.no_enhance_dosage_accuracy:.0%}, Overall={r.no_enhance_overall:.0%}\n")
                f.write(f"  With S4: Drug={r.with_enhance_drug_accuracy:.0%}, Qty={r.with_enhance_quantity_accuracy:.0%}, Dosage={r.with_enhance_dosage_accuracy:.0%}, Overall={r.with_enhance_overall:.0%}\n")
                f.write(f"  Change:  {r.overall_improvement:+.1%}\n")
        
        print(f"\n📄 Report saved: {report_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test S4 Enhancement impact on OCR accuracy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed OCR output")
    args = parser.parse_args()
    
    run_comparison_test(verbose=args.verbose)
