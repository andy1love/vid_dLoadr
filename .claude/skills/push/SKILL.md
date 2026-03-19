---
name: push
description: Stage, commit, and push all changes to origin main
disable-model-invocation: true
---

Run the full push workflow for this project:

1. Run `git status` to show what's changed
2. Ask the user for a commit message (suggest `auto: <current timestamp>` as default if they just press enter)
3. Ask the user for an optional one-line explanation of what changed (for the push log)
4. Stage all changes with `git add -A`
5. Commit with the chosen message
6. Push to `origin main`
7. Append an entry to `docs/push_log.md` in this format:

```
---

## <YYYY-MM-DD HH:MM:SS> · ✓ SUCCESS  (or ✗ FAILED)

**Branch:** main
**Commit:** <short hash before> → <short hash after>
**Message:** <commit message>

**Summary:** <explanation if provided>

**Files changed:**
- `path/to/file` (+N / -N)

---
```

If `docs/push_log.md` doesn't exist, create it with a `# Push Log` header first.
