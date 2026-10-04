# Verification and usability evidence

Date: 2026-10-04. Environment: Windows, PowerShell, Node 24.19.0/npm 11.2.0, uv 0.12.2, Python 3.13.14, SQLite 3.53.1. Application version 0.1.0. Exact dependency pins and integrity hashes are in `pyproject.toml`, `uv.lock`, `frontend/package.json`, and `frontend/package-lock.json`.

## Reproduction

```powershell
./scripts/setup.ps1
./scripts/verify.ps1 -IncludeDev
```

The verification script fails at the first failed command. Browser runs use a new file-backed test database and test-only analysts on every server invocation. Transaction tests use a separate file-backed SQLite database with independent connections; they do not touch the ordinary application database. No CI/CD service is involved.

## Observed checks

| Check | Evidence |
|---|---|
| Django system/migration checks | No issues; no migration drift. |
| Numerical and parser checks | Independent hand-worked examples; irregular spacing/interpolation; full window and zero region; bounds, overflow, encoding, strict order, underflow, shape/size rejection; 2,000 points and exact 256 KiB accepted. |
| API and persistence | Source BOM/CRLF/bytes/hash preserved; preview has no writes; two revisions and exact completion; historical/report contents; real CSRF enforcement; owner isolation; unsupported operations/fields rejected. |
| Atomicity and concurrency | Forced audit insertion failures roll back import/save/complete. Two simultaneous saves produce one commit and one conflict. Competing save/complete cannot review an unintended revision. Parallel identical operation IDs replay one commit. Real SQLite IMMEDIATE reservation and busy-to-503 mapping checked. |
| Retry safety | Import/save/complete receipts replay without extra revisions, versions or events. Changed content with reused ID conflicts. Browser tests drop the response after actual commit and recover by retrying the same intent. |
| Reviewed exports | Byte-identical repeated JSON, exact base64 source and source download; patched calculation failure does not affect saved reports. Changed account display names do not change actor snapshots. |
| Database recovery | SQLite backup restored into a new location and loaded in two independent Python processes; report bytes match the original exactly. Existing backup targets reject. Account setup preserves existing password hashes. |
| Frontend static checks | ESLint, TypeScript strict check, and Vite production build pass. Chart code is lazy-loaded in a separate basic Plotly chunk. |
| Browser workflow | Import → preview → reasoned save → second revision → read-only earlier revision → complete → reload → report → JSON/source downloads. Direct API writes after completion fail. |
| Browser failure paths | Bad CSV keeps the file; invalid/edited bounds hide old results; late preview cannot overwrite newer input; non-JSON 500 and post-commit response loss retain work; stale tabs, expired sessions, changed accounts and rotated CSRF tokens recover explicitly. |
| Navigation and viewport | Browser Back and trace/history/logout guards retain edits until confirmed. Zoom/reset leave bounds/result/version unchanged. Returning to a stale tab compares versions without replacing the draft. |
| Accessibility automation | Axe WCAG 2 A/AA and 2.1 AA scan reports no violations on the saved workspace at 1440×900 and 390×844. Keyboard input/preview/save sequence and modal Escape/focus return verified in Chromium. No full screen-reader validation claimed. |
| Runtime internet independence | Browser blocks external HTTP(S) while allowing loopback. Complete import-to-report workflow succeeds and records zero external requests. |

Detailed checks are in `backend/review/tests/` and `frontend/e2e/workspace.spec.ts`. Local browser reports/traces are written to `output/playwright/`; selected synthetic-only screenshots are committed under `docs/images/`. Test counts and final setup/restart observations are recorded in the delivery record below.

## Problems found and corrected

- Test discovery originally found no backend tests from the repository root. A package marker now makes the documented invocation discover the suite.
- A CSRF test originally sent the wrong media type and observed parser rejection before the intended CSRF check. It now uses real multipart upload and CSRF enforcement.
- A simultaneous identical revision retry could observe a committed version between the initial receipt lookup and draft-state check. A second receipt lookup resolves this race before reporting a conflict.
- The initial chart retained desktop dimensions after narrowing the viewport. Container-based ResizeObserver sizing now changes the actual Plotly dimensions; mobile overflow and screenshot checks pass.
- Failed chart loading could obstruct the workspace. A React error boundary and plot-level fallback retain boundary inputs and the Data alternative.
- Cross-tab CSRF token rotation needed a recoverable sign-in path. The browser now requests reauthentication, retains the draft, and requires explicit latest-state reconciliation.
- A browser navigation test used a non-exact button name and matched both “Close discard changes?” and “Discard changes.” The test now uses the exact action name; the navigation guard itself passed.

## Implementer-led cognitive walkthrough

This is an agent-led review of the actual rendered screens and interaction checks, not a study with human participants. No quotes, timings, scientific endorsement, or independent participant results are asserted.

| Task | Observed behavior / assessment |
|---|---|
| Identify the interval behind a saved result | Start/end fields, selected region, explicit saved revision, and fixed total-window caption place the necessary information together. The source is accessible without extra navigation. |
| Explain two different revision fractions | History puts interval, percentage, reason, actor/time in one table. Opening a row shows its exact read-only record. The test fixture demonstrates why adding a neighboring feature changes the numerator. |
| Revise and complete without losing work | Preview and saved states have distinct text. Old selected results disappear after edits; failed writes retain entries. Completion names the exact saved revision and is disabled while work is unresolved. |

The concrete usability improvement from the walkthrough/viewport check was the chart resizing fix: at 390 pixels, the first version overflowed and obscured controls. The revised chart fits the viewport, followed by the boundary controls and result, with no horizontal page scrolling. Repeat visual inspection and the automated narrow-width check confirmed the improvement. Recovery text was also confined to actual errors, preserving the normal screen’s low text density.

Desktop and mobile screenshots were visually inspected for graph legibility, boundary/result grouping, clipped controls, state labels, and the flat blue/neutral styling. These checks do not establish accessibility for every assistive technology.

## Human validation still pending

Use these three tasks with a willing participant: identify the interval of a saved result; compare two revisions and explain the difference; make a reasoned revision and complete it. Record their role in general terms, observed hesitation, outcome, one resulting change, and a repeat of the affected task. A domain participant should assess scientific terminology. A screen-reader walkthrough is also pending. No participant was contacted during implementation.

Other practical limits: prepared nonnegative input only, binary64 numerical range, 2,000 points/256 KiB per trace, local trusted-machine operation, Chromium/Windows validation, and in-memory unsaved drafts. No regulatory, tamper-proof, biological, or instrument validation is claimed.

## Delivery record

The implementation commit is [`a2ae17fecec216a856274695ee8de3882c03e7d1`](https://github.com/fullstack-nick/TraceReview/commit/a2ae17fecec216a856274695ee8de3882c03e7d1). The subsequent evidence-only commit records these completed observations; application code is unchanged.

- A fresh clone from the public GitHub remote ran `./scripts/setup.ps1` and `./scripts/verify.ps1 -IncludeDev` successfully. It installed from the two lockfiles, initialized a fresh analyst/database, built the frontend, and served both test modes. Its working tree stayed clean and its build metadata recorded the implementation commit with `working_tree_dirty: false`.
- **34 backend tests passed** in the fresh checkout, including the exact-size CSV acceptance and backup/new-process restoration checks. Django system checks and migration drift checks passed.
- **17 browser scenarios passed against the built Waitress/WhiteNoise application**, and the same **17 passed against the Vite development proxy**, with no retries. ESLint, strict TypeScript, and the production build passed.
- The production bundle contains a roughly 251 kB initial JavaScript chunk and a separately loaded 1,157 kB basic Plotly chunk (about 78/383 kB gzip respectively). These are build observations, not performance benchmarks.
- The normal local database was populated with two original synthetic demonstrations: one editable saved trace and one completed trace containing two revisions. The neighboring-feature intervals 3.2–5.1 and 3.2–5.8 min produced approximately 79.99596041590465% and 99.15423360584256%. Their provenance records the clean implementation commit.
- Running setup again preserved both traces, the existing password hash, persistent signing secret, and exact completed report. The existing analyst was left unchanged.
- Startup on occupied port 8000 failed with the documented message and left the running process intact. Only the implementation-owned process tree was then stopped. Restart through `scripts/start.ps1` served the build at 127.0.0.1:8000.
- A real authenticated HTTP session survived that restart. Its completed JSON and original CSV matched the pre-restart bytes, and both initial static assets loaded. The synthetic completed JSON SHA-256 was `6f5b19f2a12e1d89271f980b96829365dcff1045f0e78b1b9f36e742a480b169` before and after restart.
- The source repository is public at [fullstack-nick/TraceReview](https://github.com/fullstack-nick/TraceReview). MIT, installed-dependency notices, synthetic fixtures, specifications, tests, and selected screenshots are included. Git excludes local data, credentials, secrets, logs, environments, and generated artifacts. No deployment or CI/CD files are tracked.

The fresh first backend test invocation reported a missing collected-static directory before the build step created it; the build and all subsequent built-browser checks succeeded. Local evidence logs are `.local/fresh-setup.log`, `.local/fresh-verification.log`, and `.local/setup-rerun.log`; they are intentionally not published.
