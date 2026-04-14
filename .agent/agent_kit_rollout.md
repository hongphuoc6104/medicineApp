# Medicine Agent Kit Rollout

## A-Z Build Plan

### A. Governance
- root `AGENTS.md` remains the top rule source
- `.agent/rules/` refines repo behavior without overriding root rules

### B. Agent Set
- retained generic specialists: backend, mobile, debugger, planner, test, docs, DB, orchestrator
- added repo-native specialists: product architect, Phase A specialist, bridge specialist, demo QA

### C. Skill Set
- retained upstream concepts where relevant
- added domain skills for scan, OCR quality, VN drug DB, scheduling, sync, privacy, and accessibility

### D. Workflow Set
- feature planning
- scan debugging
- contract audit
- UX review
- demo readiness
- pilot readiness

### E. Templates
- feature plan
- demo runbook
- design system

### F. Validation Hooks
- lightweight starter scripts added under `.agent/scripts/`
- can later be expanded into automated verification

## Retained Vs New Matrix

### Retained Upstream Concepts

| Type | Upstream Idea | How Used Here |
|---|---|---|
| Agent | planner/debugger/mobile/backend | kept as roles and repo-specific references |
| Skill | api, python, mobile, testing patterns | used as supporting knowledge |
| Workflow | plan, debug, test, orchestrate | adapted into repo-native workflows |

### New Domain Components

| Type | Name | Why It Exists |
|---|---|---|
| Agent | `phase-a-pipeline-specialist` | Phase A is protected and benchmark-sensitive |
| Agent | `fastapi-node-bridge-specialist` | project has two backend layers with contract risk |
| Agent | `flutter-medication-flow-specialist` | Flutter app is central to the user product |
| Skill | `medication-plan-domain` | user flow and CRUD logic are app-specific |
| Skill | `reminder-offline-sync` | local reminder plus sync is core product behavior |
| Skill | `med-ui-pro-max` | healthcare UI adapter for `ui-ux-pro-max` ideas |
| Workflow | `demo-ready` | real-phone demo is a recurring requirement |

## Suggested Usage Order For The Team

1. read `.agent/README.md`
2. read relevant workflow
3. read relevant agent
4. read relevant domain skill
5. execute work
6. validate with repo commands

## Immediate Next Recommended Improvements

- add page-specific design-system files under `design-system/pages/`
- vendor or mirror selected upstream skills only if the team needs local ownership
- add automated `demo-ready` and `pilot-check` scripts tied to real commands
