Run a full git push workflow for this repo with auto-generated log entries.

## Steps

1. Run `git status --short` and show the output.

2. Run `git diff HEAD` to read all unstaged + staged changes.

3. Based **only** on the actual diff content, write a plain-English `EXPLANATION` (1–4 sentences) describing what changed and why it matters. Be specific — name the files and what the code does differently. No generic filler.

4. Propose a short imperative commit message and show the user:
   - The files that will be committed
   - The proposed commit message
   - The generated explanation
   Then **wait for the user to confirm** before proceeding (a simple "yes", "ok", or "looks good" is enough).

5. If the working tree is clean (nothing to commit), set EXPLANATION to "No file changes — push only." and skip the commit step.

6. Capture PRE_PUSH_HEAD: `git rev-parse HEAD`

7. If there are changes: `git add -A && git commit -m "<message>"`

8. Get BRANCH: `git rev-parse --abbrev-ref HEAD`

9. Push: `git push origin <branch>` — capture full output and exit code.

10. Capture POST_PUSH_HEAD: `git rev-parse HEAD`

11. Collect:
    - `git diff --stat <PRE> HEAD`
    - `git log --oneline <PRE>..HEAD`

12. Write the per-push report to `_logs/push_YYYYMMDD_HHMMSS.md` (use actual current timestamp):

```
# Push Report — YYYY-MM-DD HH:MM:SS

| Field         | Value          |
|---------------|----------------|
| Branch        | <branch>       |
| Commit Before | <pre 7-char>   |
| Commit After  | <post 7-char>  |
| Message       | <commit msg>   |
| Status        | ✓ SUCCESS / ✗ FAILED |

## Summary

<EXPLANATION>

## Files Changed
```diff
<diff --stat output>
```

## Commits Pushed
- <oneline log>

## Push Output
```
<raw push output>
```
```

13. Append to `docs/push_log.md` (check size first — if ≥ 12,582,912 bytes, move it to `docs/push_log_archive/push_log_YYYYMMDD_HHMMSS.md` and start a fresh `docs/push_log.md`). If the file doesn't exist yet, create it with header `# Push Log`. Then append:

```
---

## YYYY-MM-DD HH:MM:SS · ✓ SUCCESS

**Branch:** <branch>
**Commit:** <pre 7-char> → <post 7-char>
**Message:** <commit msg>

**Summary:** <EXPLANATION>

**Files changed:**
- `filename` (+N / -N)

---

```

14. Print the paths of both written files.
