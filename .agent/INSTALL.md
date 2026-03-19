# Install And Use

## Local Install

This repo already contains the kit under `.agent/`.
No external installer is required.

## Recommended Editor Behavior

- keep `.agent/` visible to the AI assistant
- do not add `.agent/` to project `.gitignore` if your editor indexes prompt files from git-visible paths
- if you want it local-only, prefer `.git/info/exclude`

## First-Run Reading Order For Any Agent

1. `AGENTS.md`
2. `.agent/rules/00-precedence.md`
3. `.agent/rules/10-medicineapp-core.md`
4. relevant workflow file
5. relevant agent file
6. relevant skill file

## Human Quickstart

When asking for help, prefer prompts like:
- "Use the scan debug workflow to inspect why this image returns 0 drugs"
- "Plan the next medication reminder feature using the medicine planner workflow"
- "Redesign the Home screen using the med-ui-pro-max skill"
