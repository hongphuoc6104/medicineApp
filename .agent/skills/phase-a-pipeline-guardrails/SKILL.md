# Skill: Phase A Pipeline Guardrails

## Purpose

Protect the tested Phase A pipeline while still allowing controlled enhancements.

## Always Enforce

- `scripts/run_pipeline.py` is protected
- read the related function before editing
- new experiments must use option flags
- create separate tests first when introducing new behavior
- benchmark or smoke-test after integration

## Never Assume

- that API pipeline and CLI pipeline are perfectly aligned
- that old grouping/GCN approaches should be revived
- that output keys are stable without checking artifacts

## Preferred Validation

- inspect `data/output/phase_a/<image>/summary.json`
- inspect `step-3_ocr.json`, `step-4_ner_classify.json`, `step-5_drug_search.json`
- run the smallest relevant pipeline execution first
