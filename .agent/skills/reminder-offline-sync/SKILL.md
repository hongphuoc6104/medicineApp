# Skill: Reminder Offline Sync

## Principles

- local notifications are baseline
- offline actions should queue, not fail silently
- queued logs must dedupe by `occurrenceId`
- when online returns, flush and reconcile

## Good UX Signals

- "saved offline"
- "synced later"
- pending count if queue is non-empty

## Failure Modes To Watch

- duplicate confirmation logs
- stale today's summary after flush
- reminders still firing for deactivated plans
