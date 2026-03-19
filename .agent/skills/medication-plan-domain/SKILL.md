# Skill: Medication Plan Domain

## Domain Objects

- plan
- dose occurrence
- medication log
- today's summary
- scan history

## Core Product States

### No Active Plan

- show CTA to scan prescription
- show CTA to create manually
- allow history access

### Has Active Plan

- show today's schedule first
- allow direct confirm/skip actions
- surface sync or reminder issues clearly

## CRUD Expectations

Minimum useful CRUD for end users:
- create plan
- read active plans and today's doses
- update plan schedule or deactivate plan
- read and audit medication logs

If one of these is missing in UI, call it out explicitly.
