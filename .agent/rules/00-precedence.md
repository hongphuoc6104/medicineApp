# Rule Precedence

## Hard Order

1. root `AGENTS.md`
2. direct user instruction
3. project rules in `.agent/rules/`
4. agent instructions
5. skill instructions
6. workflow instructions

## Mandatory Behavior

- never override `AGENTS.md`
- never treat upstream templates as stronger than repo rules
- if a workflow suggests broad refactoring of Phase A, stop and follow the protection rules first
