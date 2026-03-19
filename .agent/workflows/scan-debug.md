# Workflow: Scan Debug

## Goal

Debug scan issues systematically from symptom to artifact.

## Route

1. mobile symptom
2. Node route/service
3. Python API response
4. Phase A artifacts under `data/output/phase_a/`
5. protected pipeline code if necessary

## Specialist Stack

- `debugger`
- `fastapi-node-bridge-specialist`
- `phase-a-pipeline-specialist`

## Required Output

- root cause hypothesis
- smallest fix location
- regression risk note
