---
name: post-response-workflow
description: "**WORKFLOW SKILL** — Mandatory post-response workflow: run tests, git commit, git push, verify CI, deploy if frontend changed. USE FOR: every code change response. Ensures no code change goes untested or uncommitted."
---

# Post-Response Workflow

This skill MUST be invoked after EVERY response that changes code files.

## Steps (execute in order, never skip)

### 1. Run Tests
```bash
pytest backend/tests tests -v --tb=short
```
- If tests fail: **fix the code first**, then re-run
- Do NOT proceed to commit with failing tests

### 2. Git Commit
```bash
git add -A
git commit -m "<descriptive message summarizing changes>"
```
- Commit message should be specific (not "fix stuff")
- Include what was changed and why

### 3. Git Push
```bash
git push
```
- If push fails (e.g., rejected), pull and resolve before retrying

### 4. Verify CI
- Check GitHub Actions CI status after push
- If CI fails: diagnose the failure, fix it, and restart from step 1

### 5. Deploy (conditional)
Only if frontend files were changed (`frontend/` directory):
```bash
firebase deploy --only hosting
```
- Skip this step if only backend or data files changed

## Rules
- **Never skip steps** — even for "small" changes
- **Never commit with failing tests**
- **Never push without committing first**
- **If CI fails, fix immediately** — do not leave the repo broken
- Tests path: `backend/tests tests` (both directories)
