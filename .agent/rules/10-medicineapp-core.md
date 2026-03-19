# MedicineApp Core Rules

## Active Product Scope

- primary focus: Phase A prescription scan and medication reminder product flow
- Phase B is hold by default

## System Boundaries

- `mobile/`: Flutter UX and device-side reminders
- `server-node/`: main authenticated backend, plan/log/search/session APIs
- `server/`: Python AI proxy
- `core/`: AI pipeline internals
- `scripts/`: canonical CLI and benchmark scripts

## Debugging Order

Always debug from outside to inside:
1. mobile symptom
2. Node route/service contract
3. Python API payload/result
4. Phase A output artifacts
5. underlying model or data issue

## Product Truths

- if user has no active plan, guide to scan/manual/history
- if user has active plan, show today's doses first
- reminders must remain useful offline
- logs must dedupe by `occurrenceId`
- scan quality feedback must be actionable, not generic
