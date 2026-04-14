# Experimental Workspace Summary

This folder is a safe working copy of the original project.

## Paths

- Original repo: `/home/hongphuoc/Desktop/KHMT-2025-2026/createPrescription/medicineApp`
- Experimental copy: `/home/hongphuoc/Desktop/medicineApp-experimental-2026-04-14`

## Git

- Working branch: `feature/experimental-copy-2026-04-14`

## Purpose

- Use this copy to add or test new features without touching the original working project.
- Keep the original folder as the stable version.

## Isolated Runtime

- Node API: `http://127.0.0.1:3101`
- Python AI: `http://127.0.0.1:8100`
- PostgreSQL host port: `55432`
- Experimental database: `medicineapp_experimental`

## Recommended Safety Rules

- Open and edit only this experimental folder when developing new features.
- This copy is configured to use separate ports, a separate database, and separate Docker container names.
- Use `bash dev.sh` from this folder to start the isolated local dev stack.
- Avoid manually changing env values back to the original project's ports or database.

## Useful Commands

```bash
cd /home/hongphuoc/Desktop/medicineApp-experimental-2026-04-14
bash dev.sh
git branch --show-current
git status
git push -u origin feature/experimental-copy-2026-04-14
```

## Notes

- This file was added only to the experimental copy.
- The original project folder was left unchanged.
- This copy includes the current local worktree state from the moment it was copied, including any existing modified or untracked files.
- The experimental runtime was hardened to avoid sharing Node port, Python port, PostgreSQL port, or Docker container names with the original project.
