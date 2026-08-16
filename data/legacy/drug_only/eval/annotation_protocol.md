# Phase A Annotation Protocol (Drug Extraction)

## 1) Evaluation objective

The benchmark evaluates **drug-name extraction quality** from real prescription images,
not full-document information extraction.

## 2) Unit of analysis

- Primary unit: one prescription image.
- Ground truth target per image: set of canonical drug labels.

## 3) Ground-truth construction strategy

- The dataset contains seven prescription groups (`prescription_1..7`).
- The evaluation file used for scoring is `gt_drugs_by_image.json`, which stores one canonical drug set per image.
- Repeated-capture groups are retained only as provenance metadata because many images come from the same underlying prescription template.
- In the current 50-image benchmark, images within the same repeated-capture group still share the same canonical drug set; this reduces label ambiguity but does not remove the limitation of low template diversity.

## 4) Canonicalization rules

- Match by active ingredient or stable trade-name aliases.
- Ignore punctuation, casing, and dosage formatting differences.
- Do not count quantity/instruction text as drug entities.

## 5) Metrics

- Precision / Recall / F1 (micro) for extracted drug entities.
- False positive (FP) and false negative (FN) counts.
- Image exact-match rate (predicted set == reference set).
- Runtime: cold-start latency, warm latency mean, P50, P90.
- Drug-text CER/WER on the image-level OCR proxy reference set (`gt_ocr_subset.jsonl`).

## 6) Scope and limitations

- This protocol is designed for Phase A medication-list extraction.
- It does not claim full prescription OCR accuracy for administrative fields.
- Although scoring is performed at image level, the benchmark still contains repeated captures of only seven underlying prescriptions.
- Because of that repeated-capture structure, the benchmark is suitable for controlled comparison between configurations but should not be interpreted as a population-level estimate across all prescription layouts.
