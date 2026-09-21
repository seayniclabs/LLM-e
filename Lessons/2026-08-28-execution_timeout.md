---
title: Task #1838 execution_timeout — pre-fix skip_brief_lint test + false watchdog message + contradicted proof
date: 2026-08-28
project: LLM-e
error_type: execution_timeout
helmsman_lesson_id: 1572
related_tasks: [1838, 1840, 1841, 1843]
related_commits: [helmsman-db@6e670e8]
---

## What happened

Task #1838 (`[TEST] Skip Brief Lint Flag - Git Status Check`) was created at
`2026-08-28T20:18:07Z` with a deliberately minimal 1108-char brief — only a
`## Goal` header, missing `## Steps`, `## Verification`, `## Expected Output`
— to test the `skip_brief_lint` flag path. It failed with
`error_type: execution_timeout` and `last_failure_output`:

> Task stuck in_progress for >5 hours without completion. Agent likely
> crashed or hung. Needs investigation.

## Root cause (two-part)

1. **Timing**: #1838 was created 6 minutes *before* commit `6e670e8`
   (helmsman-db, landed `20:24:32Z`), which fixed `skip_brief_lint` metadata
   persistence. `GET /tasks/1838` confirms `metadata: null` — the flag was
   never persisted, so worker-dispatcher had no way to know validation
   should be skipped. Unlike sibling test #1840 (created after the fix, and
   correctly stub-gate-rejected with an explicit `STUB BRIEF` message),
   #1838 got no stub-gate message at all — it was never actually dispatched,
   and sat until a separate stale-task watchdog closed it out.

2. **The watchdog message is not trustworthy**: `agent_started_at` to
   `updated_at` for #1838 is `20:18:24Z` → `21:39:06Z`, ~1h21m — not the
   ">5 hours" the message claims. There is no output or partial result
   evidence of an agent process ever starting, so "Agent likely crashed or
   hung" is unsupported template text, not an observed fact.

## Separate finding: a prior lesson's proof is contradicted by live data

Lesson id=1571 claims the `skip_brief_lint` fix was proven via task #1840:
*"PROOF: Task #1840 executed successfully with 1112-char brief."*
`GET /tasks/1840` shows the opposite: `status: cancelled`,
`qa_results.reason: "brief rewritten by brief-rewriter (attempt 1)"`,
`last_failure_output: "STUB BRIEF: lacks 18-section structure; blocked from
dispatch by worker-dispatcher stub-gate."` The fix's own cited proof task
contradicts the fix's success claim.

## Prevention rule

1. Stale-task watchdogs must compute and log actual elapsed time
   (`agent_started_at` → now), not emit a hardcoded ">N hours" template
   string. Only report "crashed" if a process/PID was actually observed.
2. Before trusting a lesson's "PROOF: task #N did X" claim, re-fetch task
   #N's live status — it can be rewritten/cancelled by an unrelated
   downstream process (here, brief-rewriter) after the lesson was written.
3. Flag/behavior test tasks must be created *after* the fixing commit lands,
   not before, or they silently test pre-fix behavior while labeled a
   fix-validation test.

## Scope

Read-only research per task #1843 brief. No code changed, no retry of
#1838. Lesson posted to helmsman.db as id=1572.
