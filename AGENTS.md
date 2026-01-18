# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Session Startup (Pre-flight Check)

Before starting work, run `bd doctor` to catch issues early:

```bash
bd doctor              # Check for sync problems, repo mismatches
bd ready               # Find available work
```

If `bd doctor` reports issues, resolve them before proceeding.

## Troubleshooting

### DATABASE MISMATCH DETECTED

**Symptom:** Beads commands show warnings about repository ID mismatch:
```
DATABASE MISMATCH DETECTED!
  Database repo ID:  xxxxxxxx
  Current repo ID:   yyyyyyyy
```

**Cause:** This typically happens after:
- `bd` was upgraded and URL canonicalization changed
- Git remote URL changed (HTTPS ↔ SSH)
- `.beads/` directory was copied from another repo

**Fix:** If you're the only clone (or coordinating with other users):
```bash
echo "y" | bd migrate --update-repo-id
```

**Prevention:**
- Run `bd doctor` at session start
- Pin beads version during active sprints (`bd version` to check)
- Don't copy `.beads/` directories between repos

### Daemon Errors

**Symptom:** `.beads/daemon-error` file appears, commands show daemon warnings.

**Fix:**
```bash
rm .beads/daemon-error
bd sync  # Restart daemon
```

### Sync Conflicts

**Symptom:** `bd sync` fails with merge conflicts.

**Fix:**
```bash
bd sync --status       # Check what's out of sync
git pull --rebase      # Get latest changes
bd sync                # Retry sync
```

