---
description: "Use when planning or running git/file-system commands. Enforces a hard safety rule: never run clean/reset/rm/move/checkout restore unless the user has explicitly typed APPROVE DESTRUCTIVE in the current conversation."
name: "Destructive Ops Approval"
applyTo: "**"
---

# Destructive Operations Approval Policy

- Hard rule: Never run destructive operations unless the user has explicitly typed `APPROVE DESTRUCTIVE` in the current conversation.
- Treat this as mandatory, not a preference.

## Blocked Operations Without Approval

- Git: `git clean`, `git reset` (any mode), `git checkout --`, `git restore --source ...` when it can overwrite local content, force-push or history-rewriting flows.
- File system: `rm`/`rmdir`, `mv`/rename operations that can overwrite, bulk delete scripts, recursive delete commands.

## Required Safe Workflow

- Default to read-only checks first.
- Propose exactly one non-destructive command at a time.
- Explain risk briefly before any command that mutates files, index, or history.
- For any potentially destructive request, stop and ask for the exact phrase `APPROVE DESTRUCTIVE`.
- If the phrase is not present, refuse destructive execution and provide a safe alternative.

## Recovery-First Preference

- Prefer reversible commands and backups/snapshots before mutation.
- When possible, provide a verification command after each step.
