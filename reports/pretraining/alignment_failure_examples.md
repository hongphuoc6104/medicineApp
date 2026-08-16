# RxIE Pre-Training Sprint: Root-Cause Alignment Failure Audit Report

## Executive Summary
- **Total Entity Checks:** 23767
- **Total Unresolved Instances:** 19136
- **Primary Identified Causes:**
  1. `TABLE_COLUMN_SEPARATED`: Explains almost all failures of composite `QUANTITY` (e.g. "30" on line A, "Viên" on line B).
  2. `OCR_CORRUPTED`: Vietnamese diacritic variations and optical recognition character substitutions (e.g., "buối" vs "buổi", "uông" vs "uống").
  3. `CANDIDATE_WINDOW_ERROR`: Occurs when OCR reading order places dosage instructions far away from the drug brand name (> 250 characters).
  4. `OCR_TEXT_MISSING` / `CROPPED_OUT`: Text was cut off or not captured in extreme camera angles/crops.

## Failure Distribution by Class & Cause

| Class | CANDIDATE_WINDOW_ERROR | CROPPED_OUT | DRUG_ANCHOR_MISSING | OCR_CORRUPTED | OCR_TEXT_MISSING | TABLE_COLUMN_SEPARATED | Total Unresolved |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| DRUG        |    0 |    1 |    0 |  139 | 1469 |  569 |   2178 |
| STRENGTH    |    3 |    1 |  851 |   16 | 1367 |    0 |   2238 |
| QUANTITY    |    4 |    1 |    0 |    0 |  565 | 2452 |   3022 |
| ROUTE       |    3 |    1 | 1989 |  142 |  100 |   11 |   2246 |
| DOSAGE      |    5 |    1 | 1698 |    4 |   70 |  338 |   2116 |
| FREQUENCY   |    0 |    1 |  351 |  117 | 1527 |  787 |   2783 |
| INSTRUCTION |    3 |    1 |  681 |  651 |  976 |  176 |   2488 |
| FORM        |   10 |    1 | 2008 |    4 |   38 |    4 |   2065 |

## Concrete Failure Examples & Trace Diagnostics

### Failure Cause: `OCR_TEXT_MISSING`

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `DRUG`
  - **Canonical Text:** "Nitroglycerin (Nitromint)"
  - **Diagnosis:** Target text was not found anywhere in OCR document (OCR skipped or absent).

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `STRENGTH`
  - **Canonical Text:** "2.6mg"
  - **Diagnosis:** Target text was not found anywhere in OCR document (OCR skipped or absent).

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `QUANTITY`
  - **Canonical Text:** "60 Viên"
  - **Diagnosis:** Target text was not found anywhere in OCR document (OCR skipped or absent).


### Failure Cause: `DRUG_ANCHOR_MISSING`

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `ROUTE`
  - **Canonical Text:** "uống"
  - **Diagnosis:** Target string exists in document, but parent DRUG entity was not matched.

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `FORM`
  - **Canonical Text:** "viên"
  - **Diagnosis:** Target string exists in document, but parent DRUG entity was not matched.

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M02`)
  - **Entity Type:** `ROUTE`
  - **Canonical Text:** "uống"
  - **Diagnosis:** Target string exists in document, but parent DRUG entity was not matched.


### Failure Cause: `TABLE_COLUMN_SEPARATED`

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M01`)
  - **Entity Type:** `DOSAGE`
  - **Canonical Text:** "2 viên"
  - **Diagnosis:** Individual tokens ['2', 'viên'] exist in document but are separated across columns/lines.

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M02`)
  - **Entity Type:** `FREQUENCY`
  - **Canonical Text:** "Ngày trưa"
  - **Diagnosis:** Individual tokens ['Ngày', 'trưa'] exist in document but are separated across columns/lines.

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M03`)
  - **Entity Type:** `FREQUENCY`
  - **Canonical Text:** "Ngày sáng"
  - **Diagnosis:** Individual tokens ['Ngày', 'sáng'] exist in document but are separated across columns/lines.


### Failure Cause: `OCR_CORRUPTED`

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M05`)
  - **Entity Type:** `INSTRUCTION`
  - **Canonical Text:** "buổi sáng"
  - **Diagnosis:** Accent/diacritic corrupted match in OCR text: target 'buổi sáng' matches unaccented form.

- **Doc:** `IMG_20260115_181847` (RX_002, Med: `RX_002_M06`)
  - **Entity Type:** `INSTRUCTION`
  - **Canonical Text:** "buổi sáng"
  - **Diagnosis:** Accent/diacritic corrupted match in OCR text: target 'buổi sáng' matches unaccented form.

- **Doc:** `IMG_20260115_181852` (RX_002, Med: `RX_002_M05`)
  - **Entity Type:** `INSTRUCTION`
  - **Canonical Text:** "buổi sáng"
  - **Diagnosis:** Accent/diacritic corrupted match in OCR text: target 'buổi sáng' matches unaccented form.


### Failure Cause: `CANDIDATE_WINDOW_ERROR`

- **Doc:** `IMG_20260122_005931` (RX_004, Med: `RX_004_M01`)
  - **Entity Type:** `QUANTITY`
  - **Canonical Text:** "28 Viên"
  - **Diagnosis:** Target string exists at offset 820, but is outside parent window [0, 503].

- **Doc:** `IMG_20260122_005931` (RX_004, Med: `RX_004_M01`)
  - **Entity Type:** `DOSAGE`
  - **Canonical Text:** "1 viên"
  - **Diagnosis:** Target string exists at offset 509, but is outside parent window [0, 502].

- **Doc:** `IMG_20260122_005931` (RX_004, Med: `RX_004_M01`)
  - **Entity Type:** `FORM`
  - **Canonical Text:** "viên"
  - **Diagnosis:** Target string exists at offset 511, but is outside parent window [0, 500].


### Failure Cause: `CROPPED_OUT`

- **Doc:** `IMG_20260209_181227` (RX_005, Med: `RX_005_M01`)
  - **Entity Type:** `DRUG`
  - **Canonical Text:** "Silymarin (Silygamma)"
  - **Diagnosis:** Document capture has very few words (4 words), image likely cropped.

- **Doc:** `IMG_20260209_181227` (RX_005, Med: `RX_005_M01`)
  - **Entity Type:** `STRENGTH`
  - **Canonical Text:** "140mg"
  - **Diagnosis:** Document capture has very few words (4 words), image likely cropped.

- **Doc:** `IMG_20260209_181227` (RX_005, Med: `RX_005_M01`)
  - **Entity Type:** `QUANTITY`
  - **Canonical Text:** "60 Viên"
  - **Diagnosis:** Document capture has very few words (4 words), image likely cropped.


---
*Generated by `scripts/audit_alignment_failure_causes.py`.*
