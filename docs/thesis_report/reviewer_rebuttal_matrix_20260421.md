# Reviewer Rebuttal Matrix (2026-04-21)

## Scope

- Thesis source: `docs/thesis_report/main.tex`
- Locked evaluation run: `data/output/eval/run_20260421_103453`
- Goal: align claims with evidence, strengthen evaluation rigor, and improve technical transparency.

## Matrix

| Reviewer concern | Risk if unresolved | Action taken | Evidence artifacts | Thesis location |
|---|---|---|---|---|
| STT grouping previously underperformed baseline | Central technical claim can be rejected | Replaced forced STT with adaptive STT plus fallback; kept forced STT as ablation | `data/output/eval/run_20260421_103453/phase_a_eval_metrics.json`, `scripts/tests/test_adaptive_stt_selection.py` | Abstract, Ch.2, Ch.5, Ch.6 |
| Metrics/protocol quality not rigorous enough | Claims can be rejected as non-scientific | Locked reproducible run id and standardized artifact set; updated Track A / Track B wording | `data/output/eval/run_20260421_103453/phase_a_eval_metrics.json`, `data/eval/annotation_protocol.md`, `data/eval_v2/annotation_protocol_v2.md` | Ch.5 data/protocol sections |
| OCR subset too small | OCR proxy metric looks weak | Expanded OCR reference set from 33 to 238 image-level entries | `data/eval/gt_ocr_subset.jsonl`, `data/output/eval/run_20260421_103453/ocr_metrics.json` | Ch.5 metrics section |
| Need stronger ablation interpretation | Missing causal insight | Added explicit comparison between adaptive STT, baseline without STT, and forced STT | `data/output/eval/run_20260421_103453/ablation_summary.csv` | Ch.5 ablation section |
| Need uncertainty quantification | Point estimates alone can mislead | Added bootstrap CI for precision, recall, F1, exact-match, and paired deltas vs baseline | `data/output/eval/run_20260421_103453/bootstrap_ci.json` | Ch.5 subsection "Khoảng tin cậy bootstrap 95%" |
| Error analysis insufficiently detailed | Weak technical depth | Updated error profile from 36/50 errors to 13/50 errors and identified remaining FP cluster in `prescription_4` | `data/output/eval/run_20260421_103453/error_analysis.json` | Ch.5 error analysis section |
| Related-work depth unclear | Weak positioning vs literature | Added camera-captured document OCR, medical-document OCR, prescription OCR, and medication IE references, plus a comparison table | bibliography in `docs/thesis_report/main.tex` | Ch.2 related work |
| Dataset split/reporting may mix operational and correctness claims | Invalid aggregate claim risk | Kept Track A for correctness claims and Track B for unlabeled stress testing only | `data/eval_v2/phase_a_manifest_v2.csv`, `data/output/eval/run_20260421_103453/track_b_operational.json` | Ch.5 data/protocol and Track B section |
| Application-level evidence too weak | Product claims can be challenged | Re-ran backend Node tests and reported AI-side verification scripts explicitly | `server-node` test output, `scripts/tests/test_phase_a_*.py` | Ch.5 system evaluation section |
| Reproducibility and auditability | Hard to verify independently | Updated thesis consistency checker to the new locked run id and artifact set | `scripts/tests/test_thesis_report_consistency.py` | QA artifact (outside thesis body) |

## Verification commands used

```bash
venv/bin/python scripts/tests/test_adaptive_stt_selection.py
venv/bin/python scripts/tests/test_phase_a_eval_metrics.py
venv/bin/python scripts/tests/test_phase_a_error_analysis.py
venv/bin/python scripts/tests/test_phase_a_ocr_metrics.py
venv/bin/python scripts/tests/test_phase_a_bootstrap_ci.py
venv/bin/python scripts/tests/test_phase_a_track_b_operational.py
cd server-node && npm test
```

## Current status

- Locked run `run_20260421_103453` is the only run referenced by the thesis body.
- Adaptive STT no longer underperforms the no-STT baseline on Track A.
- Claims are now constrained to evidence available in Track A and Track B artifacts.
