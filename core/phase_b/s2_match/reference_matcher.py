"""Reference-based matcher for dose-centric Phase B verification."""

from __future__ import annotations

import base64
import logging
import math
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _normalize_bbox(bbox: Any) -> List[int]:
    """Convert bbox input to [x1, y1, x2, y2] int format."""
    if not bbox:
        return [0, 0, 0, 0]

    if isinstance(bbox, list) and len(bbox) == 4:
        if isinstance(bbox[0], list):
            xs = [int(p[0]) for p in bbox]
            ys = [int(p[1]) for p in bbox]
            return [min(xs), min(ys), max(xs), max(ys)]
        return [int(v) for v in bbox]

    return [0, 0, 0, 0]


class ReferenceMatcher:
    """Match pill detections against user reference images per dose."""

    def __init__(
        self,
        assigned_threshold: float = 0.8,
        uncertain_threshold: float = 0.62,
        top_k: int = 3,
    ):
        self.assigned_threshold = assigned_threshold
        self.uncertain_threshold = uncertain_threshold
        self.top_k = max(1, top_k)

    def verify(
        self,
        pill_image: np.ndarray,
        detections: List[Dict[str, Any]],
        expected_medications: Optional[List[Dict[str, Any]]] = None,
        reference_profiles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run dose-centric matching for one verification session."""
        expected = self._normalize_expected(expected_medications or [])
        reference_bank = self._build_reference_bank(
            reference_profiles or [],
            expected,
        )

        items: List[Dict[str, Any]] = []
        for idx, det in enumerate(detections):
            bbox = _normalize_bbox(det.get("bbox"))
            crop = self._crop_detection(pill_image, bbox)
            embedding = self._build_embedding(crop)
            visual_features = self._extract_visual_features(crop)
            suggestions = self._score_candidates(
                embedding,
                visual_features,
                expected,
                reference_bank,
            )

            best = suggestions[0] if suggestions else None
            status = "unknown"
            assigned_plan_id = None
            assigned_drug_name = None
            confidence = 0.0

            if best is not None:
                confidence = float(best["score"])
                if confidence >= self.assigned_threshold:
                    status = "assigned"
                    assigned_plan_id = best["planId"]
                    assigned_drug_name = best["drugName"]
                elif confidence >= self.uncertain_threshold:
                    status = "uncertain"

            items.append(
                {
                    "detectionIdx": idx,
                    "bbox": bbox,
                    "score": round(float(det.get("score", 0.0)), 4),
                    "label": int(det.get("label", 1)),
                    "status": status,
                    "assignedPlanId": assigned_plan_id,
                    "assignedDrugName": assigned_drug_name,
                    "confidence": round(confidence, 4),
                    "suggestions": suggestions,
                    "visualFeatures": visual_features,
                    "note": None,
                }
            )

        self._apply_extra_rule(items, expected)
        summary = self._build_summary(items, expected)
        coverage = self._build_reference_coverage(expected, reference_bank)

        return {
            "detections": items,
            "summary": summary,
            "referenceCoverage": coverage,
            "expectedMedications": expected,
            "missingReferences": coverage["missingDrugNames"],
        }

    def _normalize_expected(
        self,
        expected_medications: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for idx, med in enumerate(expected_medications):
            plan_id = str(med.get("planId") or med.get("plan_id") or f"expected-{idx}")
            drug_name = str(med.get("drugName") or med.get("name") or f"Thuoc {idx + 1}")
            raw_qty = med.get("pillsPerDose") or med.get("expectedCount") or 1
            try:
                expected_count = max(1, int(raw_qty))
            except (TypeError, ValueError):
                expected_count = 1

            normalized.append(
                {
                    "planId": plan_id,
                    "drugName": drug_name,
                    "expectedCount": expected_count,
                    "dosage": med.get("dosage"),
                    "metadata": med.get("metadata") or {},
                    "metadataHints": self._metadata_hints(med.get("metadata") or {}, med),
                }
            )
        return normalized

    def _metadata_hints(
        self,
        metadata: Dict[str, Any],
        med: Dict[str, Any],
    ) -> Dict[str, Any]:
        visual = metadata.get("visual") or {}
        raw_colors = visual.get("colors") or []
        colors = [str(color).strip().lower() for color in raw_colors if str(color).strip()]

        shape_hints: List[str] = []
        shape_text = str(visual.get("shapeText") or "").strip().lower()
        dosage_form = str(
            metadata.get("dosageForm") or med.get("dosageForm") or med.get("dosage") or ""
        ).strip().lower()

        for text in [shape_text, dosage_form]:
            if not text:
                continue
            if "capsule" in text or "viên nang" in text:
                self._append_unique(shape_hints, "capsule")
            if "oblong" in text or "oval" in text or "caplet" in text:
                self._append_unique(shape_hints, "oblong")
            if "round" in text or "tròn" in text:
                self._append_unique(shape_hints, "round")
            if "tablet" in text or "viên nén" in text or "coated" in text:
                self._append_unique(shape_hints, "tablet")

        dosage_hint = None
        if "capsule" in dosage_form or "viên nang" in dosage_form:
            dosage_hint = "capsule"
        elif "tablet" in dosage_form or "viên nén" in dosage_form or "coated" in dosage_form:
            dosage_hint = "tablet"

        return {
            "colors": colors,
            "shapeHints": shape_hints,
            "dosageHint": dosage_hint,
            "imprint": [
                str(item).strip().lower()
                for item in (visual.get("imprint") or [])
                if str(item).strip()
            ],
        }

    def _build_reference_bank(
        self,
        reference_profiles: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
    ) -> Dict[str, List[np.ndarray]]:
        by_plan: Dict[str, List[np.ndarray]] = {}
        by_name: Dict[str, List[np.ndarray]] = {}

        for profile in reference_profiles:
            plan_id = str(profile.get("planId") or profile.get("plan_id") or "")
            drug_name = str(profile.get("drugName") or profile.get("drug_name") or "").strip().lower()

            image_items: List[Any] = []
            if isinstance(profile.get("images"), list):
                image_items.extend(profile.get("images"))
            if profile.get("imagePath") or profile.get("image_path"):
                image_items.append(profile)
            if profile.get("imageBase64") or profile.get("image_base64"):
                image_items.append(profile)

            embeddings: List[np.ndarray] = []
            for image_item in image_items:
                img = self._load_reference_image(image_item)
                emb = self._build_embedding(img)
                if emb is not None:
                    embeddings.append(emb)

            if not embeddings:
                continue

            if plan_id:
                by_plan.setdefault(plan_id, []).extend(embeddings)
            if drug_name:
                by_name.setdefault(drug_name, []).extend(embeddings)

        final_bank: Dict[str, List[np.ndarray]] = {}
        for med in expected:
            plan_id = med["planId"]
            drug_name_key = str(med["drugName"]).strip().lower()
            refs = list(by_plan.get(plan_id, []))
            if not refs and drug_name_key:
                refs = list(by_name.get(drug_name_key, []))
            if refs:
                final_bank[plan_id] = refs

        return final_bank

    def _load_reference_image(self, image_item: Any) -> Optional[np.ndarray]:
        if isinstance(image_item, str):
            image = cv2.imread(image_item)
            return image if image is not None else None

        if not isinstance(image_item, dict):
            return None

        image_path = (
            image_item.get("imagePath")
            or image_item.get("image_path")
            or image_item.get("path")
        )
        if image_path:
            image = cv2.imread(str(image_path))
            if image is not None:
                return image

        image_base64 = image_item.get("imageBase64") or image_item.get("image_base64")
        if image_base64:
            try:
                raw = base64.b64decode(image_base64)
                arr = np.frombuffer(raw, dtype=np.uint8)
                image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                return image if image is not None else None
            except Exception as exc:
                logger.warning("Cannot decode reference base64: %s", exc)

        return None

    def _crop_detection(
        self,
        image: np.ndarray,
        bbox: List[int],
    ) -> Optional[np.ndarray]:
        if image is None or image.size == 0:
            return None
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))
        if x2 <= x1 or y2 <= y1:
            return None
        return image[y1:y2, x1:x2]

    def _build_embedding(self, image: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if image is None or image.size == 0:
            return None

        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        resized = cv2.resize(image, (96, 96), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

        hist_gray = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten()
        hist_h = cv2.calcHist([hsv], [0], None, [18], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()

        edges = cv2.Canny(gray, 80, 160)
        edge_density = np.array([float(edges.mean() / 255.0)], dtype=np.float32)

        hu = cv2.HuMoments(cv2.moments(gray)).flatten()
        hu = -np.sign(hu) * np.log10(np.abs(hu) + 1e-12)

        vector = np.concatenate(
            [hist_gray, hist_h, hist_s, edge_density, hu],
            axis=0,
        ).astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm <= 1e-9:
            return None
        return vector / norm

    def _extract_visual_features(
        self,
        image: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        if image is None or image.size == 0:
            return {
                "dominantColor": None,
                "shapeGuess": None,
                "dosageGuess": None,
                "aspectRatio": None,
                "twoTone": False,
            }

        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        resized = cv2.resize(image, (96, 96), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        mean_h = float(hsv[:, :, 0].mean())
        mean_s = float(hsv[:, :, 1].mean())
        mean_v = float(hsv[:, :, 2].mean())

        dominant_color = self._classify_color(mean_h, mean_s, mean_v)
        mask = self._foreground_mask(resized)
        shape_guess, aspect_ratio = self._classify_shape(mask)
        two_tone = self._is_two_tone(resized, mask)

        dosage_guess = None
        if shape_guess == "capsule" or (shape_guess == "oblong" and two_tone):
            dosage_guess = "capsule"
        elif shape_guess in {"round", "oblong"}:
            dosage_guess = "tablet"

        return {
            "dominantColor": dominant_color,
            "shapeGuess": shape_guess,
            "dosageGuess": dosage_guess,
            "aspectRatio": round(aspect_ratio, 3) if aspect_ratio else None,
            "twoTone": two_tone,
        }

    def _foreground_mask(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        white_ratio = float(np.mean(mask > 0))
        if white_ratio < 0.15 or white_ratio > 0.85:
            mask = cv2.bitwise_not(mask)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _classify_shape(self, mask: np.ndarray) -> tuple[str | None, float | None]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None
        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        if area <= 20:
            return None, None

        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = max(w, h) / max(1.0, min(w, h))
        perimeter = cv2.arcLength(contour, True)
        circularity = 0.0
        if perimeter > 1e-9:
            circularity = 4.0 * math.pi * area / (perimeter * perimeter)

        if aspect_ratio >= 1.85 and circularity >= 0.65:
            return "capsule", aspect_ratio
        if circularity >= 0.82 and aspect_ratio <= 1.2:
            return "round", aspect_ratio
        if aspect_ratio >= 1.35:
            return "oblong", aspect_ratio
        return "tablet", aspect_ratio

    def _is_two_tone(self, image: np.ndarray, mask: np.ndarray) -> bool:
        h, w = image.shape[:2]
        left = image[:, : w // 2]
        right = image[:, w // 2 :]
        left_mask = mask[:, : w // 2] > 0
        right_mask = mask[:, w // 2 :] > 0
        if left_mask.sum() < 20 or right_mask.sum() < 20:
            return False
        left_mean = left[left_mask].mean(axis=0)
        right_mean = right[right_mask].mean(axis=0)
        return float(np.linalg.norm(left_mean - right_mean)) >= 35.0

    def _classify_color(self, hue: float, sat: float, val: float) -> str:
        if val >= 210 and sat <= 35:
            return "white"
        if val <= 70:
            return "brown"
        if sat <= 35:
            return "gray"
        if hue < 8 or hue >= 172:
            return "red"
        if hue < 18:
            return "orange"
        if hue < 35:
            return "yellow"
        if hue < 78:
            return "green"
        if hue < 120:
            return "blue"
        if hue < 150:
            return "purple"
        return "pink"

    def _metadata_adjustment(
        self,
        med: Dict[str, Any],
        visual_features: Dict[str, Any],
    ) -> tuple[float, List[str]]:
        hints = med.get("metadataHints") or {}
        adjustment = 0.0
        reasons: List[str] = []

        detected_color = visual_features.get("dominantColor")
        colors = hints.get("colors") or []
        if colors and detected_color:
            if detected_color in colors:
                adjustment += 0.08
                reasons.append(f"màu khớp: {detected_color}")
            elif detected_color not in {"gray", "white"}:
                adjustment -= 0.04
                reasons.append(f"màu lệch: {detected_color}")

        shape_guess = visual_features.get("shapeGuess")
        shape_hints = hints.get("shapeHints") or []
        if shape_guess and shape_hints:
            if shape_guess in shape_hints:
                adjustment += 0.06
                reasons.append(f"dáng khớp: {shape_guess}")
            elif shape_guess == "oblong" and "capsule" in shape_hints:
                adjustment += 0.02
                reasons.append("dáng gần giống capsule")
            elif shape_guess == "tablet" and "round" in shape_hints:
                adjustment += 0.01
                reasons.append("dáng gần giống viên nén")
            else:
                adjustment -= 0.03
                reasons.append(f"dáng lệch: {shape_guess}")

        dosage_guess = visual_features.get("dosageGuess")
        dosage_hint = hints.get("dosageHint")
        if dosage_guess and dosage_hint:
            if dosage_guess == dosage_hint:
                adjustment += 0.05
                reasons.append(f"dạng bào chế khớp: {dosage_guess}")
            else:
                adjustment -= 0.05
                reasons.append(f"dạng bào chế lệch: {dosage_guess}")

        return adjustment, reasons

    def _score_candidates(
        self,
        embedding: Optional[np.ndarray],
        visual_features: Dict[str, Any],
        expected: List[Dict[str, Any]],
        reference_bank: Dict[str, List[np.ndarray]],
    ) -> List[Dict[str, Any]]:
        if embedding is None:
            return []

        scores: List[Dict[str, Any]] = []
        for med in expected:
            refs = reference_bank.get(med["planId"], [])
            if not refs:
                continue
            base_score = max(float(np.dot(embedding, ref)) for ref in refs)
            metadata_adjustment, reasons = self._metadata_adjustment(med, visual_features)
            best_score = min(max(base_score + metadata_adjustment, 0.0), 1.0)
            scores.append(
                {
                    "planId": med["planId"],
                    "drugName": med["drugName"],
                    "score": round(best_score, 4),
                    "baseScore": round(base_score, 4),
                    "metadataAdjustment": round(metadata_adjustment, 4),
                    "reasons": reasons,
                }
            )

        scores.sort(key=lambda item: item["score"], reverse=True)
        return scores[: self.top_k]

    def _apply_extra_rule(
        self,
        detections: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
    ) -> None:
        expected_counts = {
            med["planId"]: med["expectedCount"]
            for med in expected
        }

        for plan_id, expected_count in expected_counts.items():
            assigned = [
                item
                for item in detections
                if item["status"] == "assigned"
                and item.get("assignedPlanId") == plan_id
            ]
            if len(assigned) <= expected_count:
                continue

            assigned.sort(key=lambda item: item.get("confidence", 0.0), reverse=True)
            for item in assigned[expected_count:]:
                item["status"] = "extra"
                item["note"] = "So luong vuot qua lieu mong doi"

    def _build_summary(
        self,
        detections: List[Dict[str, Any]],
        expected: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        per_medication: List[Dict[str, Any]] = []
        missing_expected_total = 0

        for med in expected:
            assigned_count = sum(
                1
                for item in detections
                if item["status"] == "assigned"
                and item.get("assignedPlanId") == med["planId"]
            )
            extra_count = sum(
                1
                for item in detections
                if item["status"] == "extra"
                and item.get("assignedPlanId") == med["planId"]
            )
            missing_count = max(int(med["expectedCount"]) - assigned_count, 0)
            missing_expected_total += missing_count

            per_medication.append(
                {
                    "planId": med["planId"],
                    "drugName": med["drugName"],
                    "expectedCount": med["expectedCount"],
                    "assignedCount": assigned_count,
                    "missingCount": missing_count,
                    "extraCount": extra_count,
                }
            )

        return {
            "totalDetections": len(detections),
            "assigned": sum(1 for item in detections if item["status"] == "assigned"),
            "uncertain": sum(1 for item in detections if item["status"] == "uncertain"),
            "unknown": sum(1 for item in detections if item["status"] == "unknown"),
            "extra": sum(1 for item in detections if item["status"] == "extra"),
            "missingExpected": missing_expected_total,
            "perMedication": per_medication,
        }

    def _build_reference_coverage(
        self,
        expected: List[Dict[str, Any]],
        reference_bank: Dict[str, List[np.ndarray]],
    ) -> Dict[str, Any]:
        missing = [
            med
            for med in expected
            if med["planId"] not in reference_bank
        ]

        return {
            "totalExpected": len(expected),
            "withReference": len(expected) - len(missing),
            "withoutReference": len(missing),
            "missingPlanIds": [med["planId"] for med in missing],
            "missingDrugNames": [med["drugName"] for med in missing],
        }

    @staticmethod
    def _append_unique(target: List[str], value: str) -> None:
        if value and value not in target:
            target.append(value)
