# Medicine Agent Kit Architecture

## Sources

- `antigravity-kit`: routing model for agents, skills, workflows
- `ui-ux-pro-max-skill`: design-system reasoning and UI anti-pattern control
- `medicineApp`: domain rules, artifacts, benchmark habits, and demo flows

## Layers

### 1. Governance Layer

- `AGENTS.md`
- `.agent/rules/*.md`

Purpose:
- protect the tested pipeline
- define repo-wide safety rules
- keep mobile/backend/AI changes coherent

### 2. Agent Layer

Specialists coordinate work by domain:
- product logic
- Flutter flow
- FastAPI/Node contracts
- Phase A pipeline
- demo QA

### 3. Skill Layer

Skills store reusable knowledge:
- contract shapes
- OCR quality heuristics
- medication scheduling rules
- offline sync rules
- VN drug DB notes
- healthcare accessibility and UI design system guidance

### 4. Workflow Layer

Workflows turn recurring work into repeatable procedures:
- plan a feature
- debug scan failures
- validate contracts
- check demo readiness
- check pilot readiness

## Design Choice

This kit does not attempt to fully vendor upstream projects.
Instead it uses a project-specific adapter model:
- adopt the useful concepts
- rewrite instructions around `medicineApp`
- avoid irrelevant defaults like Next.js/SEO/game workflows

## Required Mental Model

- `scripts/run_pipeline.py` is the protected CLI pipeline
- `server/main.py` is the Python AI bridge
- `server-node/` is the main backend
- `mobile/` is the user app
- `data/output/phase_a/` is the first place to inspect real scan artifacts
