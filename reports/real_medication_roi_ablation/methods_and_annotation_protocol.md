# Methods and Annotation Protocol: Real-World Medication ROI Intervention Study

## 1. Data Selection and Human Annotation Protocol

### 1.1 Dataset Selection
The evaluation subset comprises **30 challenging smartphone camera captures** sampled from clinical prescription encounters in our benchmark repository:
- `RX_001` (20 captures): A complex, multi-section 15-medication prescription captured under diverse camera perspectives, close-ups, and lighting conditions.
- `RX_002` (6 captures): 115 hospital prescription table captures.
- `RX_016` (2 captures): Ambulatory prescription captures.
- `RX_019` (1 capture): 8-medication polypharmacy prescription.
- `RX_023` (1 capture): Pediatric prescription.

### 1.2 Human-Annotated Visible-in-Frame Ground Truth
To eliminate denominator distortion caused by partial-view captures (where only a subset of medications is physically framed in the camera viewfinder):
- An independent human annotator visually inspected all 30 high-resolution camera images.
- For each image, the exact list of medication names physically legible in the camera frame was documented into `data/visible_in_frame_gt.json`.
- **Zero OCR Prediction Leakage:** The ground truth was established strictly by direct visual examination of the original image pixels, without referencing any OCR predictions from Google ML Kit, PaddleOCR, or VietOCR.
- Across the 30 captures, exactly **137 visible drug instances** were identified (mean: 4.57 medications/capture).

---

## 2. Experimental Conditions

- **R0 (Full-Page Smartphone Capture):** The full uncropped camera image processed via on-device Google ML Kit Text Recognition $\rightarrow$ P0 linear text sequencing $\rightarrow$ PhoBERT NER (`models/phobert_ner_model`) $\rightarrow$ DrugLookup (`data/drug_db_vn_full.json`).
- **R1 (User-Guided Medication Table ROI Re-OCR):** The tight bounding box containing the medication table is cropped from the original high-resolution bitmap and passed to on-device Google ML Kit Text Recognition for Pass-2 Re-OCR $\rightarrow$ P0 linear text sequencing $\rightarrow$ PhoBERT NER $\rightarrow$ DrugLookup.

---

## 3. Multi-Granularity Experimental Results

| Granularity | Condition | Visible OCR Coverage | Precision | Recall | F1 Score | Sample Size |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Drug-Instance Micro** | R0 (Full-page) | 90.51% | 77.61% | 75.91% | 76.75% | $N = 137$ drug instances |
| **Drug-Instance Micro** | **R1 (ROI Re-OCR)** | **92.70%** | **80.74%** | **79.56%** | **80.15%** | $N = 137$ drug instances |
| **Capture-Macro** | R0 (Full-page) | 90.67% | 77.83% | 77.00% | 76.94% | $N = 30$ captures |
| **Capture-Macro** | **R1 (ROI Re-OCR)** | **93.00%** | **81.00%** | **81.00%** | **80.57%** | $N = 30$ captures |
| **Prescription-Macro** | R0 (Full-page) | 97.37% | 82.13% | 92.07% | 86.20% | $K = 5$ prescriptions |
| **Prescription-Macro** | **R1 (ROI Re-OCR)** | **97.98%** | **84.28%** | **94.34%** | **88.42%** | $K = 5$ prescriptions |

---

## 4. Paired Transition Matrix & Statistical Significance

### 4.1 Paired Transition Matrix ($N = 137$)
- **Both Succeeded ($R0 \text{ Correct} \rightarrow R1 \text{ Correct}$):** $95$ instances ($69.34\%$)
- **R1 Recovery Gain ($R0 \text{ Wrong} \rightarrow R1 \text{ Correct}$):** $14$ instances ($10.22\%$)
- **R1 Regression Loss ($R0 \text{ Correct} \rightarrow R1 \text{ Wrong}$):** $9$ instances ($6.57\%$)
- **Both Failed ($R0 \text{ Wrong} \rightarrow R1 \text{ Wrong}$):** $19$ instances ($13.87\%$)
- **Net Recovery Gain ($b - c$):** $+5$ drug instances

### 4.2 Statistical Significance Testing
- **Exact McNemar / Binomial 2-sided Test ($b=14, c=9$):** $p = 0.4049$ (non-significant at $\alpha = 0.05$).
- **Capture-Level Bootstrap 95% Confidence Interval ($10,000$ iterations):**
  - $\Delta \text{F1}$: $[-3.18\%, +10.18\%]$ (Point estimate: $+3.39$ pp)
  - $\Delta \text{Coverage}$: $[-0.80\%, +6.29\%]$ (Point estimate: $+2.19$ pp)
  - $\Delta \text{Recall}$: $[-3.79\%, +11.35\%]$ (Point estimate: $+3.65$ pp)
  - $\Delta \text{Precision}$: $[-2.86\%, +9.48\%]$ (Point estimate: $+3.13$ pp)
- **Prescription-Clustered Bootstrap 95% Confidence Interval ($10,000$ iterations):**
  - $\Delta \text{F1}$: $[+0.00\%, +7.21\%]$ (Point estimate: $+3.39$ pp)

---

## 5. Paper-Ready 3-Tier Research Narrative

### Tier A: Clean In-Domain Diagnostic Reference (VAIPE Benchmark)
*Evaluated on 30 clear, flat prescription scans from VAIPE `public_train` on mobile hardware:*
- **OCR Drug Coverage:** $100.00\%$ ($71/71$ gold drugs)
- **PhoBERT NER (P0 Layout):** Precision $= 98.25\%$, Recall $= 78.87\%$, F1 $= 87.50\%$
- **DrugLookup Mapping:** $100.00\%$ resolution ($0$ lookup misses)

### Tier B: Challenging Real-World Full-Page Condition (R0)
*Evaluated on 30 difficult smartphone captures with perspective distortion, glare, and partial framing:*
- **Visible OCR Drug Coverage:** $90.51\%$
- **End-to-End Extraction:** Precision $= 77.61\%$, Recall $= 75.91\%$, F1 $= 76.75\%$
- **Residual Error Profile:** $13$ `OCR_MISS` ($9.49\%$), $20$ `NER_MISS` ($14.60\%$)

### Tier C: User-Guided Medication Table ROI Re-OCR (R1)
*Re-scanning cropped bitmap regions on the same hard captures:*
- **Visible OCR Drug Coverage:** $92.70\%$ ($+2.19$ pp)
- **End-to-End Extraction:** Precision $= 80.74\%$, Recall $= 79.56\%$, F1 $= 80.15\%$ ($+3.40$ pp numerical gain)
- **Residual Error Profile:** $10$ `OCR_MISS` ($7.30\%$), $18$ `NER_MISS` ($13.14\%$)
- **Clinical Utility:** Recovers $14$ previously corrupted drug tokens (*Cozaar, Celebrex, Tanakan, Upsa C, Panadol, Refresh*) without requiring model retraining.
