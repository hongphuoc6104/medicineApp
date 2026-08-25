# MedicineApp: Pipeline Technical Specification & Status

> **Document Status:** Active / Production-Ready  
> **Last Updated:** 2026-08-24  
> **Architecture Mode:** Edge-Cloud Hybrid (Mobile ML Kit + Cloud PhoBERT NER + DAV 9,284 Drug DB)

---

## 1. End-to-End Pipeline Architecture

The MedicineApp pipeline is designed with a **Fast-Path Progressive OCR** paradigm that offloads text detection and character recognition to client edge devices, reserving server compute for clinical semantic parsing, named entity recognition, and pharmaceutical database resolution.

```
[Mobile Device]
  1. Camera Capture / Gallery Picker
  2. Google Play Services ML Kit Document Scanner (Perspective Correction, Shadow Removal)
  3. Google ML Kit Latin Text Recognition (On-Device OCR -> Line BBoxes + Text)
  4. Multipart HTTP Upload -> POST /api/scan

[Node.js Express Gateway (Port 3000)]
  5. JWT Authentication & Rate Limiting
  6. Scan Session Initialization & PostgreSQL Persistence
  7. Proxy Request Forwarding -> POST http://python-ai:8000/api/scan-prescription

[FastAPI Python AI Proxy (Port 8000)]
  8. Geometry & STT Sequence Grouping (core/classify/stt_grouping.py)
  9. PhoBERT Token Classification NER (vinai/phobert-base-v2 BIO Tagger)
  10. Fuzzy Pharmaceutical Resolution against 9,284 DAV Records (core/drug_search/drug_lookup.py)
  11. Clinical Safety Classification (Confirmed / Candidate / Rejected)

[Client Application Tier]
  12. Verification & Safety Screen with Drug Interaction Checking
  13. Exact Local Alarm Scheduling (flutter_local_notifications + timezone)
```

---

## 2. Pipeline Stages & Module Breakdown

### Stage 1: Document Normalization & Edge OCR
- **Implementation:** `mobile/android/.../PrescriptionDocumentScannerBridge.kt` & `google_mlkit_text_recognition`.
- **Function:** Auto-detects paper corners, applies 4-point perspective warp, eliminates shadows, and runs on-device Latin OCR.
- **Latency:** $\approx 250 - 450\text{ ms}$ on mid-range ARM64 hardware.
- **Server Load:** $0\text{ MB}$ OCR memory overhead.

### Stage 2: Geometric STT Layout Grouping
- **Implementation:** `core/classify/stt_grouping.py` and `core/classify/mlkit_layout_adapter.py`.
- **Function:** Detects numbered item sequence anchors (e.g., `1.`, `2)`, `3 -`) and groups vertically separated multi-line tokens (drug name, strength, dosage form, frequency) into contiguous semantic medication strings.
- **Ablation Strategies:** Evaluated across $P0$ (raw text), $P1$ (sorted lines), $P2$ (row clusters), and $P3$ (medication bands).

### Stage 3: Domain-Specific Biomedical NER
- **Implementation:** `core/classify/ner_extractor.py` (`PhoBertNerExtractor`).
- **Base Architecture:** `vinai/phobert-base-v2` with a sequence classification token head.
- **Entity Labels:** `B-DRUG`, `I-DRUG`, `O`.
- **Fine-Tuning:** Trained on real clinical prescription syntaxes to distinguish drug names from numerical quantities, units, and dosage directions.

### Stage 4: Fuzzy Drug Database Resolution
- **Implementation:** `core/drug_search/drug_lookup.py` (`DrugLookup`).
- **Database:** `data/drug_db_vn_full.json` (9,284 products from the Drug Administration of Vietnam).
- **Match Indexing:** 24,753 search keys covering trade brand names (`tenThuoc`) and active pharmaceutical ingredients (`hoatChat`).
- **Scoring:** Normalized Levenshtein distance and token-sort similarity with adaptive thresholding ($0.80$ cut-off).
- **Resolution States:**
  - `confirmed`: High confidence match ($\ge 0.85$) against verified national registration code.
  - `unmapped_candidate`: NER detected a drug entity, but similarity to official DB is intermediate ($0.65 \le \text{score} < 0.85$).
  - `rejected_noise`: Low-confidence or non-pharmaceutical string.

---

## 3. Benchmark Metrics Summary

### Table ROI Intervention Study ($R0$ vs $R1$)
- **Test Dataset:** 30 difficult real-world smartphone camera captures with 137 physically visible drug entities.
- **Ground Truth:** Human-annotated visible-in-frame ground truth (`data/visible_in_frame_gt.json`) with audited provenance (`data/human_verification_provenance_log.json`).

| Metric Granularity | $R0$ (Full Page) | $R1$ (Table ROI) | Delta ($\Delta$) | Statistical Test |
| :--- | :---: | :---: | :---: | :---: |
| **Drug-Instance Micro $F_1$** | $76.75\%$ | **$80.15\%$** | $+3.40\%$ | McNemar $p=0.4049$ ($b=14, c=9$) |
| **Capture-Macro $F_1$** | $76.94\%$ | **$80.57\%$** | $+3.63\%$ | Bootstrap $95\%$ CI: $[-0.92\%, +8.47\%]$ |
| **Prescription-Macro $F_1$** | $86.20\%$ | **$88.42\%$** | $+2.22\%$ | Clustered $95\%$ CI: $[-3.22\%, +7.43\%]$ |
| **Visible OCR Coverage** | $90.51\%$ | **$92.70\%$** | $+2.19\%$ | - |

---

## 4. Hardware & Deployment Profile

| Metric | CPU Execution (Default) | GPU Execution (CUDA 12) |
| :--- | :--- | :--- |
| **FastAPI Startup / Warmup** | $\approx 2.5\text{ s}$ | $\approx 3.2\text{ s}$ |
| **PhoBERT Inference Latency** | $\approx 380 - 650\text{ ms}$ / scan | $\approx 45 - 80\text{ ms}$ / scan |
| **FastAPI Memory Footprint** | $\approx 480\text{ MB}$ RAM | $\approx 1.2\text{ GB}$ VRAM |
| **Database Query Latency** | $< 5\text{ ms}$ (in-memory hash index) | $< 5\text{ ms}$ |
