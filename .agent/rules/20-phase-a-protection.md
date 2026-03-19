# Phase A Protection Rules

## Protected File

`scripts/run_pipeline.py` is the protected pipeline entry point.

## Allowed Change Pattern

- add only
- use option flags for experiments
- create isolated test files first
- verify no regression after integration

## Forbidden Defaults

- no broad refactor of pipeline orchestration
- no replacing current logic because a template suggests a cleaner design
- no restoring removed GCN/grouping approaches unless the user explicitly asks

## Required Reading Before Pipeline Work

- `AGENTS.md`
- relevant function in `scripts/run_pipeline.py`
- related skill: `.agent/skills/phase-a-pipeline-guardrails/SKILL.md`
