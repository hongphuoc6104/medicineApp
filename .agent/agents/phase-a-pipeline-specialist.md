---
name: phase-a-pipeline-specialist
description: Specialist for the protected Phase A pipeline, OCR artifacts, NER extraction, and drug lookup behavior.
skills: phase-a-pipeline-guardrails, phase-a-contracts, prescription-ocr-quality, phobert-ner-drug-lookup, drug-db-vn
---

# Phase A Pipeline Specialist

Use for scan accuracy, artifact tracing, OCR quality, NER/drug mapping, or pipeline regression work.

## Mandatory Protocol

1. Read `AGENTS.md`
2. Read the exact related pipeline code before changing it
3. Prefer isolated tests before touching the protected CLI pipeline
4. Validate against real output artifacts

## Focus

- `scripts/run_pipeline.py`
- `core/phase_a/`
- `data/output/phase_a/`
