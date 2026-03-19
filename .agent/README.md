# Medicine Agent Kit

Project-specific AI operating kit for `medicineApp`.

This kit combines:
- an orchestration model inspired by `antigravity-kit`
- UI reasoning inspired by `ui-ux-pro-max-skill`
- strict domain rules from `AGENTS.md`

## Priority Order

1. Root `AGENTS.md`
2. `.agent/rules/00-precedence.md`
3. `.agent/rules/10-medicineapp-core.md`
4. `.agent/rules/20-phase-a-protection.md`
5. skill and workflow instructions

If anything conflicts with `AGENTS.md`, follow `AGENTS.md`.

## What This Kit Is For

- planning new product features
- debugging `UI -> Node -> FastAPI -> Phase A`
- building Flutter medication flows
- preserving the tested Phase A pipeline
- preparing demos and pilot runs

## What This Kit Is Not For

- generic web landing pages without project context
- freeform refactors of `scripts/run_pipeline.py`
- reviving Phase B unless the user explicitly asks

## Main Entry Points

- agents: `.agent/agents/`
- domain skills: `.agent/skills/`
- workflows: `.agent/workflows/`
- reusable checklists/templates: `.agent/templates/`

## Suggested Usage

- planning: read `.agent/workflows/plan-feature.md`
- scan debugging: read `.agent/workflows/scan-debug.md`
- demo prep: read `.agent/workflows/demo-ready.md`
- pilot readiness: read `.agent/workflows/pilot-check.md`
- UI redesign: read `.agent/skills/med-ui-pro-max/SKILL.md`

## Existing Legacy Skill Files

The older markdown files in `.agent/skills/*.md` are preserved for compatibility.
Use the new folder-based skills first.
