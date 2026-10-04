## Recommended project: **TraceReview — a scientific trace-review workspace**

Build a **Django + React application where a scientist imports one chromatogram, selects a region around a peak, inspects the calculated area, and saves a traceable review record.**

The central workflow is:

**Import a trace → inspect it → adjust the analysis region → save a reasoned revision → complete the review → reopen the exact reviewed result.**

The important focus is not “build an impressive analytical algorithm.” It is:

> **Make one scientific decision understandable, easy to perform, and possible to reconstruct later.**

That gives you a focused way to practice: scientific workflow design, React interfaces, Django integration, visualization, and traceability.

---

## 1. Set a strict scope before starting

Make this a **single analytical module**, not a miniature laboratory platform.

| Dimension | Project boundary |
|---|---|
| Scientific task | Review the area of one manually selected region in a trace. |
| Input | One documented, two-column CSV format. |
| Data size | A few hundred points per trace; a hard limit of 2,000 points. |
| Main interface | One review workspace, with an import dialog and history panel. |
| Users | One analyst role, using ordinary Django authentication. |
| Workflow | Draft analysis → saved revisions → review complete. |
| Output | A read-only review summary and a downloadable JSON record. |

Do **not** add sample inventory, experiment scheduling, multiple assay types, automatic peak detection, machine learning, instrument connections, electronic signatures, or a configurable workflow engine.

You can store multiple imported traces so that you can reopen previous work. A simple trace selector is sufficient; you do not need a dashboard.

### The user scenario

Use this fictional requirement as your starting point:

> “I need to inspect this trace and decide where the main peak begins and ends. I sometimes adjust those boundaries. Later, I need to explain which boundaries produced the reported result and why I changed them.”

Notice that this is not a predefined screen specification. You must decide what information the scientist needs, which actions should be explicit, and how to prevent confusion between an experimental adjustment and a saved result.

That is the UI/UX responsibility you should practice.

---

## 2. Keep the scientific calculation deliberately simple

For this exercise, represent a trace as time-and-signal pairs:

```csv
time_min,signal_au
0.0,0.0
1.0,2.0
2.0,0.0
```

This tiny triangle is a calculation fixture, not your main demonstration dataset.

For the demonstration, generate a synthetic trace containing approximately 600 points, one prominent peak, and one smaller neighboring feature. Use a fixed generation seed, or deterministic functions, so the fixture does not change between runs.

### Define a limited input contract

Assume the uploaded data is already prepared for analysis: nonnegative signal values, with no baseline correction required by your application.

Validate that the file has the expected columns, finite numeric values, strictly increasing time values, sufficient points, and positive total area. Reject duplicate times, missing values, unsupported columns, and oversized files.

**Do not silently sort the file, remove problematic rows, or replace missing values.** Return an error that identifies the location and explains how to correct it.

Rejecting negative signals is a limitation of this exercise’s input contract—not a general statement that negative analytical measurements are invalid.

### Calculate only three values

The user chooses a start time \(a\) and end time \(b\). Calculate:

| Result | Definition |
|---|---|
| Total area | Area under the entire uploaded trace. |
| Selected-region area | Area under the trace between \(a\) and \(b\). |
| Selected-region area fraction | \(100 \times \text{selected area} / \text{total area}\). |

Use piecewise-linear interpolation and the trapezoidal rule. NumPy provides `numpy.trapezoid`, including support for explicitly supplied time coordinates rather than assuming equally spaced points. [NumPy](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html)

For successive points, the area contribution is:

\[
A_i = (t_{i+1}-t_i)\frac{y_i+y_{i+1}}{2}
\]

When a selected boundary falls between measured points, interpolate the signal at that boundary before integrating. Do not simply select the nearest existing point.

For the triangle above:

- The total area is \(2\).
- Selecting the interval from \(0.5\) to \(1.5\) gives an area of \(1.5\).
- The selected-region fraction is therefore \(75\%\).

This gives you an independently checkable test case.

### Be precise about what the result means

Call the result **“Selected-region area fraction,”** not “RNA purity” or “RNA integrity.”

Your exercise defines a mathematical measurement of the supplied signal. It does not establish a biological interpretation. Likewise, fixing the total integration window to the entire uploaded trace is a deliberate simplification.

Show that assumption in the interface:

> Total integration window: entire trace, 0.00–10.00 min.

The scientific knowledge to study here is limited: integration boundaries, interpolation, units, preprocessing assumptions, numerical precision, and the distinction between a calculated result and its interpretation.

---

## 3. Use a small, purposeful technology stack

Django and React are the chosen foundation. Everything else below is a recommendation for this exercise.

| Layer | Recommendation | What you practice |
|---|---|---|
| Frontend | React, TypeScript, Vite | Typed components, forms, state, and interaction design. |
| Visualization | Plotly through `react-plotly.js` | Scientific plotting and connecting controls to a visualization. |
| Backend | Django and Django REST Framework | Models, request validation, authenticated APIs, and workflow rules. |
| Calculation | A small Python module using NumPy | Explicit, testable numerical behavior. |
| Storage | SQLite for the local project | Persistence and migrations without database infrastructure becoming another project. |
| Testing | Django’s test runner and Playwright | Numerical/API correctness and complete user workflows. |

Plotly has an official React integration and configurable chart interactions, so you can use existing plotting functionality rather than building chart infrastructure yourself. [Plotly](https://plotly.com/javascript/react/)

Use ordinary Django session authentication with CSRF protection. Seed an ordinary analyst account; do not build registration, password-reset, or role-management screens. Django REST Framework documents session authentication and its CSRF requirements. [Django REST Framework](https://www.django-rest-framework.org/api-guide/authentication/)

Keep the architecture to one Django application and one React feature area. No Redis, Celery, microservices, or custom state-management framework is necessary.

---

## 4. Make the review workspace the main design exercise

Spend most of your design attention on this screen.

### Layout

**Header:** Show the trace label, source filename, current saved revision, and review status. Provide access to the source file and analysis history.

**Main area:** Display a large line chart with labeled axes, units, hover values, zooming, and a clearly highlighted selected interval.

**Analysis panel:** Place start and end fields beside the calculated results, with explicit actions for calculating a preview and saving an analysis.

**History panel:** Show earlier saved revisions, their boundaries, results, author, timestamp, and reason. Opening an earlier revision should be read-only.

Use numeric boundary fields in the first version. Drag handles are not necessary for completion. You can still practice meaningful visualization interaction through zooming, hovering, and synchronization between the fields and highlighted interval.

### Design the difficult states, not just the happy path

**An edited region is not yet a calculated result.**  
When someone changes a boundary, update the highlighted region but mark the previous result as outdated. Do not leave an old percentage looking as though it belongs to the new selection.

**A preview is not a saved revision.**  
Label the state explicitly: “Unsaved preview” versus “Saved revision 3.” A user should never need to infer whether work has been committed.

**Zooming is not changing the analysis.**  
Zooming the chart must not alter integration boundaries or the denominator. “Reset zoom” and “Reset analysis boundaries” are different actions.

**A failed save must preserve the user’s work.**  
Keep the entered boundaries and reason visible. Show a useful error and allow retrying; do not clear the form.

**Completing a review must identify the exact revision.**  
Use a confirmation such as:

> Complete review of revision 3? Its boundaries and results will become read-only.

Call this **“Complete review,” not “Approve sample.”** This project does not decide whether a sample passes a specification or is suitable for release.

### Include an accessible alternative to visual inspection

Make the boundary fields keyboard-operable, associate errors with their fields, and provide a numerical table or equivalent textual access to the plotted data. Do not communicate saved state or warnings through color alone. W3C guidance for complex graphics emphasizes providing textual descriptions and access to the represented information. [W3C](https://www.w3.org/WAI/tutorials/images/complex/)

Also render straight segments between measured points. Avoid displaying a visually smoothed curve while calculating the area of a different, unsmoothed trace.

---

## 5. Keep the backend small, but make its rules explicit

### Three domain models are enough

Use Django’s existing user model plus these three models:

| Model | Responsibility |
|---|---|
| `TraceRun` | The uploaded source, parsed points, source checksum, import metadata, workflow state, and reviewed-revision reference. |
| `AnalysisRevision` | An immutable saved set of boundaries, calculated results, algorithm version, author, timestamp, and reason. |
| `AuditEvent` | A server-created record of a committed action and its relevant before/after context. |

For this small project, storing the limited-size original upload and parsed points in the database is reasonable. You do not need one database row per measured point or a separate file-storage service.

An `AnalysisRevision` should contain the selected boundaries, the fixed total integration window, all three results, and a calculation identifier such as `linear-trapezoid-v1`. Record the application commit or release identifier as well.

### Keep calculations out of views and components

Put the calculation in a module with a function conceptually like:

```python
analyze_trace(points, start_time, end_time) -> AnalysisResult
```

It should not depend on HTTP requests, database models, or React.

Use this same function for previews and saved analyses. **The backend calculates the authoritative result; the browser does not submit a percentage to be trusted.**

Use Django REST Framework serializers for validating request fields and returning structured errors. Its serializers support both field-level and object-level validation. [Django REST Framework](https://www.django-rest-framework.org/api-guide/serializers/)

### A compact API

A sufficient API would be:

```text
POST /api/traces/                      Import a trace
GET  /api/traces/                      List existing traces
GET  /api/traces/{id}/                 Load the workspace data
POST /api/traces/{id}/preview/         Calculate without saving
POST /api/traces/{id}/revisions/       Save a new analysis revision
POST /api/traces/{id}/complete-review/ Lock the latest saved revision
GET  /api/traces/{id}/report/          Retrieve the reviewed record
GET  /api/traces/{id}/source/          Retrieve the original upload
```

For this dataset size, the detail response can include revision history and audit events. They do not need separate subsystems.

### Enforce a few important invariants

Preserve the uploaded source after import. Changes to analysis boundaries create new revisions rather than overwriting earlier ones. Require a reason for every saved revision; the first can describe the initial selection.

Derive authorship from the authenticated request and timestamps from the server. Do not accept either as authoritative browser input.

Save a revision and its audit event in the same transaction. Complete the review, set its revision reference, and write the corresponding audit event in one transaction as well. Django’s `transaction.atomic()` provides the all-or-nothing database behavior needed for these operations. [Django Project](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)

After review completion, reject further analysis writes in the backend—not merely by disabling controls in React. Do not expose update/delete operations for saved revisions or audit events.

Add a simple run-version field to detect stale saves from two browser tabs. Check and advance it atomically; return a conflict instead of silently overwriting newer work.

This is enough traceability practice without building an event-sourcing framework.

---

## 6. Implement it in six milestones

### Milestone 1 — Specify the workflow and create fixtures

Before implementing the backend, write a one-page workflow specification.

Describe the user’s goal, the distinction between preview/saved/reviewed states, and the information needed to reconstruct a result. Sketch the main screen and its invalid-input, unsaved, and reviewed states.

Create three demonstration fixtures: a clean trace, a trace with an ambiguous neighboring feature, and an invalid file. Keep the triangle example as a separate numerical test fixture.

**Finished when:** Another person can understand the workflow from your sketch, and every displayed result has a written definition.

**Practice:** Translating an ambiguous scientific request into concrete behavior rather than immediately choosing components.

### Milestone 2 — Build and test the calculation

Implement CSV parsing, input validation, boundary interpolation, and area calculation before introducing database persistence.

Test the triangle, an irregularly spaced trace, a full-width selection, boundaries between points, and invalid inputs. Verify calculations against hand-worked examples rather than only comparing one implementation with another.

Keep full numerical precision internally and apply display rounding only when presenting values.

**Finished when:** The calculation behaves correctly without Django or React, and its assumptions are documented.

**Practice:** Reproducibility, numerical edge cases, and separating scientific logic from application plumbing.

### Milestone 3 — Build the interactive React workspace

Start with a fixture loaded directly into the frontend.

Implement the chart, boundary fields, highlighted interval, result panel, validation messages, and preview/saved-state labels. Use a small number of components organized around responsibilities rather than splitting every visual element into a separate abstraction.

Keep chart viewport state separate from analysis parameters. Derive whether the form is dirty from its relationship to the saved revision rather than maintaining several independent flags that can contradict each other. React’s state-structure guidance specifically recommends avoiding contradictory and redundant state. [React](https://react.dev/learn/choosing-the-state-structure)

**Finished when:** A person can inspect the trace, set an interval with the keyboard, and explain which result belongs to which boundaries.

**Practice:** Scientific visualization, form behavior, visual hierarchy, and state modeling.

### Milestone 4 — Connect Django and persist revisions

Add the models, import endpoint, preview endpoint, and revision-saving endpoint.

Connect the workspace to real backend responses. Preserve local edits on errors. When an analysis is saved, update the interface from the server’s returned revision, not from an assumed success state.

For previews, ensure that a late response cannot overwrite results for newer inputs. Associate each response with the parameters that produced it.

**Finished when:** You can import a trace, save two different analyses with reasons, refresh the browser, and inspect both revisions.

**Practice:** Frontend/backend integration, validation, asynchronous behavior, and persistent scientific state.

### Milestone 5 — Complete review and export the record

Implement the final review action and backend write restrictions.

The reviewed summary should show the source identity, selected boundaries, total integration window, results and units, calculation version, selected revision, review note, author, and timestamp.

Provide a JSON download of that record and access to the original CSV. Use the same saved data for both the workspace and report; do not recalculate historical reports automatically with whatever code happens to be current.

**Finished when:** Reopening a reviewed trace shows its saved result, and attempts to modify it through the API are rejected.

**Practice:** Record identity, reproducible reporting, and workflow enforcement.

### Milestone 6 — Test usability and make one focused revision

Give a colleague or friend three tasks: identify the region used in a saved calculation, explain why a later result changed, and complete a review without losing work.

Observe hesitation and misunderstandings without explaining the interface. A non-scientist can help reveal navigation and state-label problems; feedback on scientific terminology and interpretation should come from a domain user when available.

Then make one justified improvement. For example, replace an ambiguous “Save” label with “Save analysis revision,” or show the saved boundaries beside the unsaved ones.

**Finished when:** You have a documented usability finding, a design change, and evidence that the change addressed the problem.

**Practice:** Taking responsibility for usability rather than merely implementing your original design.

---

## 7. Test the risks that matter most

You do not need hundreds of tests. Concentrate on failures that could make a scientific result misleading or difficult to reconstruct.

| Risk | Test |
|---|---|
| Incorrect integration | The triangle fixture produces the expected total and selected areas. |
| Incorrect boundary handling | A boundary between points uses interpolation, not nearest-point snapping. |
| Silent data alteration | Invalid or unsorted input is rejected rather than silently repaired. |
| Stale preview | A delayed response cannot appear as the result for newer boundaries. |
| Partial save | A failed audit write also rolls back the revision write. |
| Lost update | A stale browser tab cannot save over a newer run version. |
| False lock | A reviewed run rejects direct API writes. |
| Inconsistent reporting | The report matches the exact revision referenced by the completed review. |

Use Playwright for a complete journey: import, change boundaries, calculate, save, revise, complete review, reload, and inspect the report. Prefer interactions through visible labels and roles rather than selectors tied to implementation details, consistent with Playwright’s testing guidance. [Playwright](https://playwright.dev/docs/best-practices)

Also test failed requests. A reliable retry experience is part of the interface, not just a backend concern.

---

## 8. Practice regulated-software thinking without claiming compliance

This project should demonstrate selected ideas: preserving source data, attributing changes, retaining prior information, enforcing workflow states, and recording test evidence.

It should **not** be described as “Part 11 compliant.” The actual regulation includes broader requirements involving validation, access controls, record protection, audit trails, operational checks, and procedures. A history table and a locked screen do not establish that a system meets those requirements. [eCFR](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11/subpart-B/section-11.10)

Be equally precise about technical guarantees. An audit table with no application-level edit endpoint is not tamper-proof against a database administrator. A checksum can help detect a difference from a retained reference; it does not independently prove the origin of a file.

Keep documentation to three short documents:

| Document | Contents |
|---|---|
| Workflow specification | User goal, states, decisions, and scope exclusions. |
| Calculation specification | Input contract, formula, interpolation, units, examples, and limitations. |
| Test and design evidence | Requirements mapped to tests, plus the usability finding and resulting change. |

To practice working in an existing codebase, deliver the milestones through small branches or pull requests. Once the basic workflow works, introduce the required revision reason as a change request: update the schema, API, interface, and tests without discarding existing records.

That gives you a modest but useful maintenance exercise inside the same project.

---

## What the completed project should demonstrate

Your final demonstration should tell one coherent story:

> “I imported this synthetic trace, selected a region, and calculated its area fraction. I saved that analysis, then changed the boundary and documented why. The earlier result remains available. I completed the review of a specific revision, and the report preserves the source, parameters, calculation version, and result. Here are the tests and the usability change that support the workflow.”

That demonstrates: what users and data you supported, what UI/UX decisions you owned, how you handled traceability and reproducibility, and how you used Django with React.

**Stop when that story works well.** Do not add another assay or dashboard. The depth should come from making this one workflow clear, reliable, and explainable.

---

# Research and implementation addendum — 4 October 2026

**Status: planning and dependency investigation complete; application implementation has not started.** The material above is the supplied plan. With the author's explicit permission, four company-linked passages were removed or neutralized; all other wording was preserved. Everything below extends that baseline.

This addendum makes the next implementation pass executable from beginning to end. It distinguishes decisions made for this project from facts checked in documentation or on the development machine. Package versions and machine observations are a dated snapshot, not a promise about future releases.

Quick navigation: [machine readiness](#10-local-machine-and-prerequisite-investigation), [package versions](#11-dependency-baseline-and-compatibility-decisions), [UI specification](#17-minimal-workspace-specification), [start the next pass](#20-implementation-preparation-exact-sequence), [stage order](#21-end-to-end-work-packages-in-dependency-order), [acceptance checks](#22-verification-matrix-and-acceptance-criteria).

## 9. Binding decisions and interpretation of the baseline

| Topic | Decision for implementation |
|---|---|
| Product | TraceReview: an independent, local scientific trace-review workspace. |
| Scope | One CSV trace at a time, 2–2,000 points, manual interval selection, three measurements, immutable revisions, final review, source download, JSON report. Multiple runs can be reopened. |
| Distribution | Public source repository; the application and its data run locally. No hosted service, cloud deployment, telemetry, external fonts, runtime CDN, or remote database. |
| Repository | Intended repository: `fullstack-nick/TraceReview`, public, default branch `main`. Its creation belongs to the implementation preparation stage; it has not been created during this research pass. |
| License | MIT for project code and original synthetic fixtures. Preserve the licenses and notices of dependencies separately. |
| Automation | No CI/CD, deployment configuration, scheduled checks, or GitHub Actions workflows. Verification runs locally. |
| Main platform | Windows 11 x64, with PowerShell launch scripts and a browser interface. Keep Python/TypeScript code portable, but do not claim macOS/Linux verification without running it. |
| Runtime | Python 3.13, Django 5.2 LTS, DRF, NumPy, SQLite; React, TypeScript, Vite, Plotly. Waitress and WhiteNoise serve the built local application. |
| User model | One analyst role. Bootstrap one ordinary, non-staff Django account. Runs are scoped to their importing user, including downloads and history. No registration or user-management UI. |
| Visual design | A flat working surface with lines, fields, tables, and a large chart. No cards, tiles, metric blocks, ornamental dashboard, shadows, green palette, or marketing text. |
| Interaction | Explicit preview, explicit revision save, explicit completion. No automatic save, drag handles, peak finding, background recalculation, or reopen-completed action. |
| Documentation | This plan is the master handoff. During implementation produce a concise README and the three domain documents requested above. Do not turn the UI into the documentation. |

Resolve these tensions in the original exercise as follows, without rewriting it:

- The revision reason is mandatory **from the first schema and first working save**. The suggested later maintenance exercise is optional educational material, not an instruction to ship an intermediate model that loses reasons.
- The six original milestones remain the implementation backbone. Small local commits are useful recovery points; multiple branches or pull requests are not required to finish a single implementation pass.
- The three documents are `docs/workflow.md`, `docs/calculation.md`, and `docs/evidence.md`. Operational setup goes in `README.md`; dependency attribution goes in `THIRD_PARTY_NOTICES.md`.
- The usability milestone requires honest evidence. An automated walkthrough or an implementer's inspection must never be described as a colleague's or scientist's feedback. See section 23 for the completion rule when no participant is available.
- “Review complete” locks the entire run against further analytical operations. Selecting another historical revision does not undo completion or change the reported revision.
- “Local” means a browser talks to a server bound to `127.0.0.1`. It does not mean a packaged executable, a desktop shell, LAN sharing, or an air-gapped installer. Initial dependency acquisition requires internet access; ordinary use after setup must not.

No company names, company-linked product names, logos, screenshots, copied product copy, affiliation claims, or comparison claims belong in the project, repository metadata, fixtures, screenshots, or demo. Use original synthetic data and independently designed UI. The limited name search found no matching scientific project in the searched GitHub results; this is not a trademark-clearance claim.

## 10. Local machine and prerequisite investigation

### 10.1 Observed environment

These are actual checks made on 4 October 2026, not requirements inferred from the plan. Personal home-directory paths and credentials are deliberately omitted from this public-ready document.

| Item | Observed | Consequence |
|---|---|---|
| Workspace | Initially empty; no `.git` and no applicable ancestor `AGENTS.md` found | Start a new repository; there is no application to migrate. |
| Operating system | Windows 11 Pro, x64, build family 26200 | Use Windows-compatible commands and server packages. |
| PowerShell | 7.6.5 in this session | PowerShell scripts are suitable; call `npm.cmd` explicitly. |
| Git | 2.53.0.windows.2 | Available; author name/email and `main` default are configured. |
| GitHub CLI | 2.88.1; authenticated as `fullstack-nick` | Repository operations can use the existing login. The target repository returned 404 at inspection time. |
| Node.js / npm | 24.19.0 / 11.2.0 | Meets the selected frontend tools' engine constraints. No Node installation is needed. |
| `python` on PATH | CPython 3.11.9 | Do not use an unqualified `python` to create the project environment. |
| Other Python installations | 3.12.10, 3.14.0, and uv-managed 3.13.14 | Select the existing Python 3.13.14 explicitly. |
| uv | 0.12.2 | Available for project environment creation and a committed dependency lock. |
| SQLite in selected Python | 3.53.1; `json_valid('[1,2]')` returned 1 | SQLite and JSON support are already present; no database server or SQLite installation is needed. |
| Backend libraries | Django, DRF, NumPy, Waitress, WhiteNoise absent from selected interpreter; no project environment | Install into the project `.venv`, never the shared interpreter. |
| Frontend dependencies | No project manifest or `node_modules` existed | Install project packages after creating the manifest and lock. |
| Browsers | Chrome 153.0.8010.54 and Edge 154.0.4258.48 | Suitable for manual inspection. |
| Playwright cache | Chromium and headless-shell revision 1243 present; Chrome for Testing executable reports 153.0.8010.12 | This matches the selected Playwright 1.63.0 browser metadata. Confirm launch during preparation. |
| Local ports | No listeners observed on 8000, 5173, 8001, or 5174 | Planned ports were available; launch scripts must still check them each time. |
| Free disk space | Approximately 99 GiB on the workspace volume | No immediate space prerequisite. |

No global tools, project libraries, application files, database, or GitHub repository were installed or created as part of the investigation. A temporary directory outside the project was used for dependency metadata and resolver checks; its Python environment is empty. Package-manager metadata caches may have been populated.

### 10.2 Installation conclusion

**No missing system prerequisite blocks implementation.** What remains is ordinary project setup: `.venv`, locked Python dependencies, locked npm dependencies, and a Playwright browser installation/verification command. Docker, WSL, Redis, Celery, PostgreSQL, a C/C++ compiler, and a global Django/Vite installation are not required for the selected package set.

The selected backend set resolved in a temporary Python 3.13 environment with binary-only installation required. A compatible Windows x64 NumPy wheel was also verified in PyPI metadata. This establishes dependency availability, not execution of application tests. An initial dry-run against the shared uv-managed interpreter was correctly refused; the successful check used an isolated virtual environment.

Do not change system-wide execution policy, Python defaults, Git settings, or browser installations to build this project. Use the selected interpreter and local commands explicitly.

## 11. Dependency baseline and compatibility decisions

### 11.1 Python packages

| Dependency | Selected version | Purpose |
|---|---|---|
| CPython | 3.13.14 installed; project accepts `>=3.13,<3.14` | Stable local interpreter already available. |
| Django | 5.2.17 | Supported LTS foundation, auth, ORM, transactions, test runner. |
| djangorestframework | 3.18.1 | API serialization, validation, permissions. |
| NumPy | 2.5.3 | Binary64 arrays, interpolation, trapezoidal integration. |
| Waitress | 3.0.2 | Local WSGI server that supports Windows. |
| WhiteNoise | 6.12.0 | Serve the compiled frontend assets without another web server. |

The binary-only resolver selected transitive dependencies `asgiref 3.12.1`, `sqlparse 0.6.0`, and `tzdata 2026.5` for this Windows interpreter. Put the direct exact versions in `pyproject.toml`, let uv write the full lock, and commit `uv.lock`. Set `.python-version` to `3.13.14`; do not modify the shared uv installation. Use `uv sync --locked` thereafter. No pytest, pandas, SciPy, or database driver is needed.

Django 5.2 supports Python 3.13 and is an LTS release; the selected DRF metadata requires Django 5.2 or newer. Choosing 5.2 is a deliberate stability choice even though a newer Django feature series exists. Sources: [Django 5.2 support](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Django package metadata](https://pypi.org/pypi/Django/5.2.17/json), [DRF package metadata](https://pypi.org/pypi/djangorestframework/3.18.1/json), [NumPy wheel metadata](https://pypi.org/pypi/numpy/2.5.3/json), and [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/).

### 11.2 Frontend packages

| Group | Exact direct versions |
|---|---|
| Application | `react 19.3.0`, `react-dom 19.3.0` |
| Chart | `react-plotly.js 4.1.0`, `plotly.js 4.1.1` |
| Build and types | `vite 8.3.2`, `@vitejs/plugin-react 6.1.1`, `typescript 6.0.3`, `@types/react 19.3.0`, `@types/react-dom 19.3.0`, `@types/node 24.19.1` |
| Lint | `eslint 10.12.0`, `@eslint/js 10.0.1`, `typescript-eslint 8.71.0`, `eslint-plugin-react-hooks 7.1.1`, `eslint-plugin-react-refresh 0.5.7` |
| Browser verification | `@playwright/test 1.63.0`, `@axe-core/playwright 4.13.0` |

Use npm, exact direct versions, `package-lock.json`, and `npm ci`. Set the tested Node range to `>=24.19.0 <25` and record npm 11.2.0 in `packageManager`. Do not scaffold with an unreviewed `@latest` dependency set. No state library, component framework, CSS framework, router package, chart service, or separate frontend unit-test stack is required. Django tests cover the pure calculation and services; Playwright covers the actual browser states and interactions.

Specific compatibility findings:

1. The registry's TypeScript latest was 7.0.2, but the current `typescript-eslint` supported range was `>=4.8.4 <6.1.0`. Select 6.0.3, not 7.x. [Maintainer compatibility policy](https://typescript-eslint.io/users/dependency-versions/).
2. Vite 8.3.2 and the selected React plugin accept Node 24.19.0. The plugin's compiler-related peers are optional; do not add React Compiler or Babel tooling. [Vite prerequisites](https://vite.dev/guide/) and [plugin package metadata](https://registry.npmjs.org/@vitejs/plugin-react/6.1.1).
3. `react-plotly.js` 4.1.0 supports React 18/19 and ships its own declarations; `plotly.js` 4.1.1 also ships declarations. Do **not** add the old `@types/react-plotly.js` or `@types/plotly.js` packages. The package contents and exports were inspected. [Wrapper metadata](https://registry.npmjs.org/react-plotly.js/4.1.0) and [Plotly metadata](https://registry.npmjs.org/plotly.js/4.1.1).
4. Use `react-plotly.js/factory` with `plotly.js/dist/plotly-basic.min.js`. That existing package file was verified at approximately 1.19 MB uncompressed. It supplies the scatter plot needed here while keeping the complete chart library out of the browser bundle. Add one narrow ambient declaration for this bundle path using the upstream Plotly types. Do not write a custom chart engine. [Factory integration](https://github.com/plotly/react-plotly.js#customizing-the-plotlyjs-bundle).
5. Playwright 1.63.0 expects Chromium revision 1243, already present in the machine cache. Still run `npx playwright install chromium` after local package installation so missing supporting files are repaired normally. Package metadata inspection is not a browser launch test. [Browser installation guidance](https://playwright.dev/docs/browsers).

These exact versions are the starting baseline, not permission to ignore a real installation or runtime failure. At preparation, resolve them, run the smoke checks below, and record any necessary narrowly scoped adjustment before building features. Avoid broad upgrades during implementation.

The complete npm set above passed a temporary `npm install --package-lock-only --ignore-scripts --no-audit --no-fund --strict-peer-deps --engine-strict` check with Node 24.19.0/npm 11.2.0. It produced a lock outside the repository and installed no frontend packages. Run npm from the intended working directory; the first attempt using only a trailing `--prefix` did not select that directory in this environment. Runtime imports, TypeScript compilation, and browser launch remain preparation checks, not claimed research results.

### 11.3 Licensing and assets

Use the standard MIT text in `LICENSE`, with the year and the repository owner's chosen attribution; `2026 TraceReview contributors` is the default attribution for this project. Add the MIT identifier to project manifests. MIT requires retaining its copyright and license notice. [MIT text and application guidance](https://choosealicense.com/licenses/mit/).

Dependency metadata identifies React/Vite/Plotly/WhiteNoise as MIT, Django/DRF as BSD-3-Clause, TypeScript/Playwright as Apache-2.0, Waitress as ZPL, and the accessibility tooling as MPL-2.0. NumPy's wheel includes several upstream notices. Preserve actual installed license texts in `THIRD_PARTY_NOTICES.md` or accompanying notice files when redistributing bundled assets; the project's MIT label does not relicense dependencies. Do not use third-party datasets, graphics, web fonts, icons, screenshots, or branding. A text wordmark, system font stack, and native controls are sufficient.

## 12. Architecture, local execution, and repository shape

### 12.1 Request and storage arrangement

```text
Browser (React workspace)
  same-origin /api/* requests, Django session + CSRF
            |
       Django + DRF
       auth / serializers / permissions
            |
       review services -------- pure CSV + calculation modules
            |
       SQLite file
       original bytes + parsed points + revisions + audit events
```

Development: browser at `http://127.0.0.1:5173`; Vite proxies `/api/` to Django on `127.0.0.1:8000`. Use `strictPort: true`, `host: '127.0.0.1'`, and a documented proxy configuration. If `changeOrigin: true` is used, add only `http://127.0.0.1:5173` to Django's development `CSRF_TRUSTED_ORIGINS`. The browser still makes same-origin requests; do not install CORS middleware or add wildcard origins.

Finished local app: browser at `http://127.0.0.1:8000`; Waitress serves Django, which supplies the HTML shell and API; WhiteNoise supplies the built static assets. Use `DEBUG=False`, explicit `ALLOWED_HOSTS`, and a persistent locally generated secret key. Never bind to `0.0.0.0` by default. Waitress supports Windows; WhiteNoise integrates with Django static-file collection. [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/) and [WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html).

Configure Vite's production asset base as `/static/app/`, emit the build to `frontend/dist/`, map that directory under the `app` prefix in `STATICFILES_DIRS`, and run `collectstatic`. Serve the built `index.html` at `/` through a Django view with `Cache-Control: no-store`; do not cache the entry document as an immutable asset. Vite already hashes asset names, so use WhiteNoise's compressed static storage without adding a second filename-manifest scheme. Only existing `/static/` paths receive static responses; unknown `/api/` and static paths must return proper 404s, not the SPA shell.

Use hash locations such as `/#/traces/<uuid>` and `/#/traces/<uuid>/report` so refresh/bookmarks work without a routing library or a catch-all server route. Optional `?revision=<uuid>` belongs inside the hash. A small location adapter handles navigation and dirty-form confirmation consistently, including browser Back/Forward.

### 12.2 Intended tree

```text
TraceReview/
  IMPLEMENTATION_PLAN.md
  README.md
  LICENSE
  THIRD_PARTY_NOTICES.md
  .gitignore
  .gitattributes
  .python-version
  pyproject.toml
  uv.lock
  backend/
    manage.py
    config/                 settings, urls, wsgi
    review/                 the only domain Django app
      models.py
      serializers.py
      views.py
      urls.py
      services.py
      csv_input.py
      calculation.py
      reports.py
      migrations/
      management/commands/  init_analyst, backup_database
      tests/
  frontend/
    package.json
    package-lock.json
    index.html
    vite.config.ts
    tsconfig*.json
    eslint.config.js
    src/
      main.tsx
      App.tsx
      api.ts
      types.ts
      styles.css
      features/review/     workspace, chart, fields, history, report
      types/plotly-basic.d.ts
    e2e/
    playwright.config.ts
  fixtures/
    triangle.csv
    irregular.csv
    clean-trace.csv
    neighboring-feature.csv
    invalid-duplicate-time.csv
    README.md
    generate.py
  scripts/
    setup.ps1
    dev.ps1
    build.ps1
    start.ps1
    verify.ps1
    serve_local.py
  docs/
    workflow.md
    calculation.md
    evidence.md
  .local/                   ignored: SQLite, secret, logs, local backups
```

Do not create empty abstractions just to match the tree. Split a file only when responsibilities justify it. Keep request validation, domain mutation, and numerical calculation separate even if each is small.

### 12.3 Operational behavior

- `setup.ps1`: verify versions, create/sync `.venv`, install npm dependencies, verify Chromium, create the local secret if absent, migrate, and create the analyst if absent. A rerun must not replace the secret, password, or data. Prompt securely for the initial password; unattended setup may consume `TRACEREVIEW_ANALYST_PASSWORD` from the process environment. Never commit or supply a default password.
- `dev.ps1`: start Django and Vite on the documented ports, report the URL, and clean up only processes it started. If launching helpers with `Start-Process`, use `-WindowStyle Hidden`. Fail on occupied ports; do not kill unrelated listeners or silently choose another port.
- `build.ps1`: type-check, compile the SPA, copy/build its entry document as specified, collect static assets, and capture application build metadata.
- `start.ps1`: start the built local app with Waitress. Fail with a useful instruction if the build or migrations are missing. Do not install packages, reseed data, or rebuild on every launch. Keep the foreground process stoppable with Ctrl+C.
- `verify.ps1`: run the checks in section 22, fail on a nonzero exit code, and preserve useful logs locally. No hosted automation.
- Place the database at `.local/tracereview.sqlite3`, sessions in Django's database backend, and the generated secret in `.local/secret_key`. Never put credentials or scientific records in browser localStorage, fixtures, Git, or remote issue attachments.
- Back up with SQLite's supported backup API into a separate local file. Do not copy a live database file casually. Restore only while the app is stopped, keeping the previous database. Document the command and verify one backup/restore round trip. [Python SQLite backup](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup).
- Ignore `.venv/`, `node_modules/`, compiled assets, local settings/secrets, SQLite and journal files, logs, Playwright output, and personal CSV uploads. Commit only synthetic fixtures. Use `.gitattributes` to make committed fixture CSV bytes deterministic with LF line endings despite the machine's `core.autocrlf=true`.

## 13. Scientific and CSV contract: version 1

### 13.1 Exact input rules

The parser identifier is `csv-time-signal-v1`. These choices intentionally resolve details that the baseline leaves open.

| Property | Contract |
|---|---|
| File count | Exactly one file per import. A `.csv` suffix is expected; MIME type is advisory and cannot substitute for parsing. No ZIP, spreadsheet, or compressed input. |
| Raw size | At most 262,144 bytes (256 KiB), checked before decoding. Request envelope limit: 524,288 bytes (512 KiB). |
| Encoding | Strict UTF-8, with an optional UTF-8 BOM at the beginning. Preserve the original bytes, including BOM and line endings. Reject invalid encoding; do not guess an alternative. |
| Newlines | LF and CRLF accepted; final newline optional. Reject empty records within the data and extra blank records after it. A single terminating newline is not an extra blank record. |
| Header | Exactly `time_min,signal_au`, in that order, case-sensitive; no other columns or duplicate header. Remove only a leading BOM for parsing. Do not trim or rename header fields. |
| CSV dialect | Comma delimiter and standard double-quote quoting, parsed with Python `csv.reader(..., strict=True)`. No delimiter sniffing, comments, thousands separators, or multiline fields. Every record has exactly two cells. |
| Numbers | ASCII decimal numbers, optional sign, optional decimal point, optional exponent. Maximum 128 characters per decoded cell, including whitespace. Leading/trailing ASCII spaces or tabs in numeric cells are permitted for parsing; source bytes are not changed. Reject empty cells, underscores, booleans, `NaN`, infinity, comma decimals, and other text. |
| Representation | Convert validated tokens to binary64; reject overflow to infinity, a nonzero token underflowing to zero, and distinct time tokens collapsing to equal binary64 values. Zero and negative zero are numerically equivalent. |
| Point count | Minimum 2, maximum 2,000 data records, excluding the header. Stop and identify record 2,001 rather than silently truncating. |
| Time | Finite and strictly increasing after conversion. Negative time is allowed; the uploaded coordinate system defines the time origin. No sorting, deduplication, resampling, or time shifting. |
| Signal | Finite and nonnegative. This is a prepared-signal contract, not a rule about raw instrument data. No baseline subtraction, clipping, smoothing, or normalization. |
| Integral | Full-trace area must be finite and strictly greater than zero. Reject nonrepresentable intermediate calculations with a numeric-range error. |
| Label | Optional import field, trimmed, 1–120 characters when provided; default to the filename stem. Preserve the resulting label as import metadata. |
| Filename | Retain a safe basename, at most 255 characters; reject control characters. Never interpret an uploaded filename as a filesystem path. The original file content remains exact. |
| Duplicate imports | Permitted as distinct runs when deliberately submitted with different request IDs. Same request ID is a retry, not a second import. |

Use one explicit ASCII number grammar, conceptually `[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`, then finite/representability checks. Set a consistent 128-character CSV field limit once at parser initialization. Use `Decimal` only to detect a nonzero token lost during conversion if needed; the scientific computation remains binary64. Reject malformed CSV with a line-aware error. Python documents the CSV reader's newline handling and strict dialect option. [CSV documentation](https://docs.python.org/3.13/library/csv.html).

Error locations use **physical file line numbers, starting at 1**, so line 1 is the header. The parser rejects multiline fields, keeping record/line interpretation understandable. Return the first error in file order, with stable machine code, line, column name when applicable, and a corrective message. Example: `Line 18, time_min: must be greater than the previous time (2.5).` Never include the entire uploaded file or a large attacker-controlled value in the error.

Check size at the application boundary and read at most the maximum plus one byte. `FILE_UPLOAD_MAX_MEMORY_SIZE` is only a memory-to-disk threshold, not a rejection limit; it is insufficient alone. Configure Waitress's body cap, bounded upload handling in Django, and bounded JSON requests. A too-large import returns 413 before persistence. [Django upload settings](https://docs.djangoproject.com/en/5.2/ref/settings/#file-upload-max-memory-size) and [Waitress body limit](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).

### 13.2 Boundary and calculation rules

Inputs satisfy `t_min <= a < b <= t_max`, with finite binary64 numbers. Bounds are inclusive at the trace ends; a zero-width, reversed, or outside interval is invalid. No snapping or implicit clamping. A selection containing no measured interior point is valid: its two interpolated endpoints still define a segment. Selected area may equal zero even though total area must be positive.

The authoritative pure function must:

1. Accept already validated ordered points and validated boundaries; retain defensive shape/finite checks at its public boundary.
2. Calculate total area with `numpy.trapezoid(signal, x=time)` over all points.
3. Form selected coordinates as `a`, all original times strictly between `a` and `b`, and `b`, without duplicating an endpoint that equals a measured point.
4. Obtain endpoint signals by linear interpolation, using original signals unchanged for interior points.
5. Integrate those selected points by the same trapezoidal method.
6. Compute the percentage as `(selected_area / total_area) * 100.0` to avoid needless overflow from multiplying area first.
7. Return immutable/plain result data, including both windows, all three numbers, units, point count, and algorithm identifier `linear-trapezoid-v1`.

NumPy's trapezoid operation does not sort the supplied x values; validation must do the ordering check. NumPy interpolation also expects increasing coordinates and can extrapolate by endpoint values, so validate bounds before calling it. [Trapezoid reference](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html) and [interpolation reference](https://numpy.org/doc/stable/reference/generated/numpy.interp.html).

Use explicit floating-point error handling and final finite checks. Reject input/calculations outside the supported numeric range; do not manufacture a zero or percentage. For tiny numerical overshoot of selected area beyond total, allow only a documented relative tolerance of `1e-12 * total_area`; normalize that numerical residue to the nearest physical endpoint. Any larger violation is a calculation error. When `a == t_min` and `b == t_max`, reuse the calculated total as selected area and return exactly 100. No tolerance relaxes ordering or boundary limits.

Units are `min` for time, `AU` (arbitrary signal units) for signal, `AU·min` for both areas, and `%` for the fraction. These are measurements of the supplied signal, with no biological interpretation, acceptance limit, uncertainty estimate, or sample-release decision.

Persist full binary64 values. JSON exports contain numeric values without display rounding and never contain `NaN`/infinity. In the UI, show areas to six significant digits and percentages to two decimal places; show a nonzero fraction below 0.01% as `<0.01%` and a non-full fraction rounding to 100% as `>99.99%`. Provide full numerical values in the report/data view. Boundary editors retain round-trippable values rather than rounding a saved boundary on load. Timestamps use UTC in storage and export; human display includes an explicit local time zone.

### 13.3 Independent numerical examples

| Fixture / selection | Total area | Selected area | Fraction |
|---|---:|---:|---:|
| Triangle `(0,0), (1,2), (2,0)`, `[0.5,1.5]` | 2 | 1.5 | 75% |
| Same triangle, `[0,2]` | 2 | 2 | 100% |
| Same triangle, `[0.25,0.75]` | 2 | 0.5 | 25% |
| Irregular `(0,0), (1,2), (3,2), (4,0)`, `[0.5,3.5]` | 6 | 5.5 | 91.666666…% |
| Two points `(0,1), (2,3)`, `[0.5,1.5]` | 4 | 2 | 50% |
| `(0,0), (1,0), (2,2)`, `[0,0.5]` | 1 | 0 | 0% |

For the irregular example, the full area is `1 + 4 + 1 = 6`; the selected area is `0.75 + 4 + 0.75 = 5.5`. For the triangle interval `[0.25,0.75]`, endpoint signals are 0.5 and 1.5, so its area is `0.5 * (0.5 + 1.5) / 2 = 0.5`. These expected values are hand-derived, not outputs of the function under test. Use relative tolerance `1e-12` and absolute tolerance `1e-12` for these ordinary-scale fixtures; test tiny values separately with scale-appropriate tolerances.

### 13.4 Demonstration fixture design

Commit the actual generated CSV bytes; the generator explains provenance but is not run automatically when the app starts. Use 601 points with `t_i = i / 60`, `i = 0..600`, covering exactly 0–10 minutes. Generate nonnegative, baseline-free curves deterministically:

- Main peak: `exp(-0.5 * ((t - 4.5) / 0.45)^2)`.
- Clean trace: main peak plus `0.12 * exp(-0.5 * ((t - 7.0) / 0.20)^2)`.
- Ambiguous trace: main peak plus `0.30 * exp(-0.5 * ((t - 5.35) / 0.25)^2)`.
- Invalid demonstration: a short otherwise valid CSV with one duplicate time and a documented expected error location.

Write numbers with 17 significant digits, UTF-8, and LF; document the actual committed file hashes. The synthetic values are illustrations, not assay measurements. The fixture workflow changes `[3.2,5.1]` to `[3.2,5.9]` with a reason about including the neighboring feature. Do not hard-code its percentages before calculating and validating them during implementation. Keep the hand-worked small fixtures separate from the visually useful demonstration data.

## 14. Persisted data and traceability

Use Django's existing user model and exactly the three domain models in the baseline. UUIDs identify runs, revisions, and audit events externally. Each saved snapshot contains primitive JSON-compatible values; do not pickle Python objects.

### 14.1 `TraceRun`

| Fields | Rules |
|---|---|
| `id`, `label`, `source_filename` | UUID; immutable import label and safe filename. Renaming is outside version 1. |
| `source_bytes`, `source_sha256`, `source_size` | `BinaryField`, lowercase 64-character SHA-256, byte count. Hash the exact original bytes before decoding. Never replace the source. |
| `points`, `point_count`, `time_min`, `time_max`, `total_area` | Ordered JSON array of `[time, signal]`, count, full integration window and initial total. Keep the stored parsed representation. |
| `parser_version`, `import_calculation_version`, `import_build` | Identify the parser, calculation and server build that accepted the file. |
| `imported_by`, `imported_by_name`, `imported_at` | User foreign key with `PROTECT`, username snapshot, server UTC timestamp. |
| `status` | `draft` or `reviewed`; default `draft`. A run with saved revisions remains `draft` until completed. |
| `run_version` | Positive integer, starts at 1 after import; every successful committed domain mutation increments it exactly once. Previews, reads and retries do not. |
| `latest_revision` | Nullable protected foreign key to `AnalysisRevision`; points to the latest committed revision for this run. |
| `reviewed_revision`, `reviewed_by`, `reviewed_by_name`, `reviewed_at`, `review_note`, `review_build` | Null/empty before completion; permanently populated in one completion transaction. Note is optional, trimmed, at most 2,000 characters. |

Do not put raw source bytes into ordinary list/detail responses. Import/revision metadata are not editable through the API. A completed run must have a reviewed revision equal to the latest revision at completion. All revision references must belong to the same run, checked in the service; a foreign key alone cannot enforce this relationship.

Add database checks for a positive run version and point count within 2–2,000, and for coherent completion fields: draft rows have no reviewed revision/author/time/build, while reviewed rows have all required completion fields. The optional note stays an empty string when absent. Because runs and revisions reference each other, create the models and add the revision-reference fields in a migration order Django can resolve; verify both migration from an empty database and `makemigrations --check`.

### 14.2 `AnalysisRevision`

| Fields | Rules |
|---|---|
| `id`, `run`, `revision_number` | UUID, protected run foreign key, positive sequential integer scoped to the run. Unique `(run, revision_number)`. |
| `start_time`, `end_time` | Full-precision selected bounds. |
| `total_start_time`, `total_end_time` | Saved full-trace denominator window. |
| `total_area`, `selected_area`, `area_fraction_percent` | Full-precision authoritative calculation results. |
| `time_unit`, `signal_unit`, `area_unit`, `fraction_unit` | Persist unit identifiers so later display changes do not reinterpret old records. |
| `source_sha256`, `parser_version`, `algorithm_version` | Snapshot the identity and interpretation relevant to this result. |
| `application_version`, `git_commit`, `working_tree_dirty`, `runtime_versions` | Server-supplied provenance: app release, commit if available, whether it had edits, Python/NumPy and relevant backend versions. |
| `reason`, `created_by`, `created_by_name`, `created_at` | Trimmed reason of 1–1,000 characters; protected user foreign key, username snapshot, server UTC timestamp. |

Add database constraints for positive revision number, `start_time < end_time`, selected window within total window, positive total area, and nonnegative selected area / percentage between 0 and 100. Finite-value checks also belong in the service: do not assume database comparisons fully validate NaN. Use `FloatField` for numerical values; decimal fields would not change the underlying binary64 algorithm into exact arithmetic.

Snapshots are immutable through ordinary application operations. Do not expose revision PUT/PATCH/DELETE, register writable domain models in Django admin, or implement cascade deletion. A model-level guard against editing an existing revision is useful defense against accidental `save()`, but is not a claim that a database owner cannot edit records. Keep all domain writes in the service module.

Application provenance is frozen when saving. Capture the clean Git commit for the final demonstrated build. In development, record `working_tree_dirty=true` honestly; if Git is absent, record an explicit release identifier and `git_commit=null`, not a fabricated hash. A dirty-worktree marker identifies a limitation: a commit alone cannot reconstruct its uncommitted edits. Before final demonstration, commit the application, rebuild, and create demonstration records against that build.

### 14.3 `AuditEvent`

| Fields | Rules |
|---|---|
| `id`, `run`, `revision` | UUID; protected run foreign key and optional revision reference. |
| `event_type` | Exactly `trace_imported`, `revision_saved`, or `review_completed`. |
| `actor`, `actor_name`, `occurred_at` | Authenticated user, username snapshot, server UTC time. |
| `version_before`, `version_after`, `context` | Structured before/after status and revision identity, with relevant boundaries/reason or source identity. Import is 0 → 1. |
| `request_id`, `request_fingerprint`, `result` | Unique client operation UUID, server-computed normalized request fingerprint, and immutable minimal committed response data for safe retries. |

Enforce unique `(run, version_after)` and globally unique `request_id`. There is exactly one audit event per successful import, revision save, or completion. Read/preview/failed operations produce no domain audit event. Store no passwords, cookies, access tokens, full request headers, or redundant raw uploads in audit context. Retry bookkeeping fits this model; do not introduce a fourth domain model or an event-sourcing system.

Authorship and timestamps always come from the server. Include username snapshots in revisions, completion and audit events so a later administrative username change cannot silently alter historical reports.

## 15. Transactions, stale tabs, and retry safety

### 15.1 SQLite strategy

Use `transaction.atomic()` for committed domain operations, with SQLite `OPTIONS = {'transaction_mode': 'IMMEDIATE', 'timeout': 5}` and `ATOMIC_REQUESTS=False`. Keep default journal behavior for this small single-user workload; do not add WAL configuration without a demonstrated need. Parse and calculate before acquiring the write transaction, then recheck the mutable run state within it. Original points are immutable, so the precomputed result remains associated with the same source.

Inside the transaction, check the request's expected version and change the row with a conditional update equivalent to:

```text
UPDATE run
SET run_version = run_version + 1
WHERE id = requested_run
  AND imported_by = authenticated_user
  AND status = 'draft'
  AND run_version = expected_version
```

Require exactly one affected row. Then insert the revision, update the latest-revision reference, and insert its audit event; roll back everything on any exception. Completion similarly sets status, the exact latest reviewed revision, review metadata, the next version, and its audit event in one transaction. Use the database's unique revision-number constraint as an additional check.

SQLite ignores `select_for_update()`, so it must not be the concurrency mechanism. `IMMEDIATE` acquires the write reservation at transaction start; it does not remove the need for the version precondition. A busy database after the short timeout becomes a retryable 503, not a misleading stale-version response. Catch transaction errors **outside** the atomic block. [Django SQLite behavior](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes) and [atomic error handling](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).

For a coherent workspace snapshot, retrieve the run, revision history and audit metadata inside a short transaction and serialize after leaving it. Under the selected SQLite mode this briefly reserves a writer slot even for this multi-query read; that is acceptable for the bounded local workspace. Never keep a transaction open while rendering, streaming a download, waiting for UI input, or doing network work.

### 15.2 Preconditions and idempotency

All three committed operations accept a `request_id` UUID. Revision save and completion also require `expected_version`; completion additionally requires `revision_id`. The server never infers “whichever revision is latest now” from a stale dialog.

For an apparent retry, normalize/validate the request and compute its fingerprint, then do a read-only receipt lookup before numerical work. A matching committed receipt can return immediately without recalculation. Repeat the receipt lookup inside the write transaction for new operations, since a competing identical request may commit between the first lookup and transaction acquisition.

Within the transaction:

1. Look for a committed audit event with this request ID. If the same user, operation and normalized payload match, return the recorded committed response with `replayed=true`. Do this before rejecting a reviewed/stale run, because a previous request may already have succeeded.
2. A reused ID with different content returns `409 idempotency_conflict`, without exposing another user's data.
3. For a new operation, require ownership. Reject a reviewed run with `409 review_locked`; reject a mismatched version with `409 version_conflict`; reject a non-latest completion target with `409 revision_conflict`.
4. Execute and record the mutation and event atomically, including the request fingerprint and result.

The fingerprint covers the operation, authenticated user ID, run ID where relevant, expected version, targeted revision, normalized fields, and source SHA-256 for imports. The result stores only the operation's immutable receipt, committed revision/review data and committed version, not a live run-detail response.

The browser generates the ID once per intended operation, disables duplicate submits, and retains the ID and exact payload after an uncertain network failure. Retry uses that same ID. If the user edits the form after an uncertain result, first reload/reconcile the run; do not silently issue a new save that may duplicate the committed one. A new intentional operation gets a new ID. This also makes an import retry safe without globally deduplicating identical files.

After successful mutation or replay, fetch current detail. The receipt identifies what committed; current detail may already be newer because another tab acted. Do not present the receipt's old version as the current run version. If refresh fails after a successful receipt, say the save succeeded but refresh failed, keep the receipt, and offer retry of the read.

### 15.3 Conflict UX

Keep raw boundaries, reason and any valid matching preview after a 409/503/network failure. A stale-version message offers **Reload latest**, which refreshes the saved baseline while preserving the local draft. Show the new saved revision in the normal history area. Never automatically save the local draft over the new baseline.

After reloading an active draft, require a fresh preview and an explicit save with the new version. If the run was completed elsewhere, make it read-only and preserve the local values in the conflict message long enough to copy; offer **View reviewed result**. Do not create a reopen/rebase/merge subsystem. Retrying a known completed operation still returns its original receipt.

## 16. HTTP contracts and session authentication

### 16.1 Common conventions

Use JSON for the API except multipart import and file downloads. Use UUID strings for identifiers, integers for versions/numbers, JSON numbers for finite numerical values, and ISO 8601 UTC strings ending in `Z` for timestamps. Reject unknown write fields so the browser cannot accidentally submit authorship, stored percentages, status, or arbitrary model attributes. Reasons and notes are plain text; React escapes them normally.

Authenticate and owner-scope every trace operation. Return 404 for another user's run, including source/report access. Use 403 with code `authentication_required` for unauthenticated protected requests, consistent with DRF session authentication; do not design the frontend around 401. Permission and CSRF failures use distinct codes.

One JSON error envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Check the highlighted fields.",
    "fields": {"end_time": ["Must be greater than start time."]},
    "location": null,
    "current_version": null
  }
}
```

For a CSV error, `location` is `{ "line": 18, "column": "time_min" }`. Fields absent from a particular error can be null/empty consistently. Status codes: 400 for invalid data, 403 for missing session/CSRF, 404 for missing/inaccessible runs, 405 for unsupported methods, 409 for workflow/version/idempotency conflicts, 413 for excessive body/file size, 415 for unsupported request media type, and 503 for a retryable database lock. Unexpected 500 responses carry a generic message; details stay in a local log. A proxy/server may emit a non-JSON 413/500, so the client must also handle non-JSON failures without dropping form state.

### 16.2 Endpoint details

| Method and path | Request | Successful response / rules |
|---|---|---|
| `GET /api/session/` | None; anonymous access allowed | 200: authenticated flag, `{id, username}` or null, and a CSRF token. Ensure the CSRF cookie exists. |
| `POST /api/login/` | Django login form fields `username`, `password`, with CSRF | 200: user summary and fresh CSRF token; invalid credentials → 400 `invalid_credentials`. Always apply Django CSRF protection, even before login. |
| `POST /api/logout/` | CSRF, no business fields | 204 after ending the session. UI guards unsaved work first. |
| `POST /api/traces/` | Multipart `file`, optional `label`, `request_id` | 201 committed import receipt; original retry → 200 replay receipt. Start at run version 1, no revision. |
| `GET /api/traces/` | Optional `offset` and `limit`, default 50, maximum 100 | 200 `{items, total, offset, limit}`; newest imports first with stable UUID tie-breaker. Summaries only, no points/source/history. |
| `GET /api/traces/{id}/` | None | 200 coherent detail: immutable trace metadata, points, status/version, current/ reviewed revision IDs, revisions, audit events, review metadata. No raw file bytes. |
| `POST /api/traces/{id}/preview/` | `start_time`, `end_time` | 200 authoritative results with echoed normalized boundaries, algorithm identifier, source hash and observed run version. No persistence or version increment. Reviewed run → 409. |
| `POST /api/traces/{id}/revisions/` | `start_time`, `end_time`, `reason`, `expected_version`, `request_id` | 201 committed revision receipt; replay → 200. Recalculate on the backend; accept no submitted result. |
| `POST /api/traces/{id}/complete-review/` | `revision_id`, `expected_version`, optional `review_note`, `request_id` | 200 committed completion receipt. Require at least one saved revision and target the latest. |
| `GET /api/traces/{id}/report/` | Optional `download=1` | 200 versioned reviewed-record JSON; `download=1` adds attachment disposition. Draft → 409 `review_not_complete`. |
| `GET /api/traces/{id}/source/` | None | 200 attachment containing the exact original bytes, safe filename, and `text/csv` content type. |

Example save request:

```json
{
  "start_time": 0.5,
  "end_time": 1.5,
  "reason": "Initial selection around the central peak.",
  "expected_version": 1,
  "request_id": "31dc9191-f5db-4b93-a22d-155a276b48c1"
}
```

A receipt has `{request_id, operation, run_id, committed_version, revision, review, replayed}`. `revision` is the newly saved immutable revision where applicable; `review` is the immutable completion snapshot where applicable; otherwise those fields are null. An import receipt identifies the created run. Lists and history omit internal request fingerprints, raw source blobs and stored receipts. History order is newest revision first; audit order is chronological with the run version as tie-breaker.

For a small local collection, history can be returned in full as the baseline proposes. The trace chooser may load additional pages using a plain **More traces** action; no dashboard or search subsystem is needed. Do not silently hide older runs after the first page.

### 16.3 Authentication implementation details

Use Django session auth, `IsAuthenticated` for domain views and a login endpoint based on Django's CSRF-protected `LoginView`/`AuthenticationForm`, adapted to JSON success/error responses. The React login form sends form-encoded fields to that view. Do not rely on DRF's anonymous-session behavior to protect login. The session bootstrap uses `get_token()`/`ensure_csrf_cookie`; every unsafe request includes `X-CSRFToken`, with `credentials: 'same-origin'`.

Login rotates the CSRF secret, so the response/bootstrap must refresh the token before import/save/logout. A custom CSRF failure view returns the shared JSON envelope. Do not blanket-apply `csrf_exempt`. DRF explicitly documents both the 403 behavior and the login CSRF exception. [Session authentication](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication) and [Django AJAX CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/).

Use project-specific cookie names, HttpOnly session cookies, `SameSite=Lax`, and a persistent secret. Secure-cookie flags are false for the explicit local HTTP setup; no forced HTTPS/HSTS redirect. Restrict allowed hosts; expose no admin route. Store passwords only through Django's password hashing. Provide CLI password change instructions instead of a reset screen.

If a session expires while editing, leave the draft in React memory and show a small login dialog. Reauthenticate and reload the latest server state before the user retries. Do not silently replay a write after login. If a different account logs in, clear the prior account's loaded records/draft before loading its workspace.

## 17. Minimal workspace specification

### 17.1 Layout and visual language

Design for a 1440×900 desktop and remain usable at 1024×768. At narrow widths, place the analysis form below the chart. At 390 px / 200% zoom, controls must remain reachable without page-wide horizontal scrolling; the data/history tables may scroll within their own labeled region.

```text
TraceReview   [Trace: Neighboring feature v] [Import]               analyst · Sign out
----------------------------------------------------------------------------------
neighboring-feature.csv · Saved revision 2                    Source   Data   History

 Signal (AU)                                      Start (min) [ 3.2       ]
   |                                              End (min)   [ 5.9       ]
   |               /\                             [Calculate preview]
   |              /  \_/\
   |_____________/_______\__________              Selected-region area fraction
                      Time (min)                  92.34%  (illustrative only)
 [Zoom] [Pan] [Reset zoom]                         Selected area    ... AU·min
                                                  Total area       ... AU·min
 Total integration window: entire trace,           Reason
 0–10 min.                                        [                       ]
                                                  [Save analysis revision]
                                                  Complete review
```

The sketch is a layout specification, not a computed fixture result. Actual values come from the backend. Use no enclosing card outlines or filled metric tiles. A single divider between chart and controls is enough. “Panel” in the baseline means a functional region of the screen, not a decorated card.

Default palette: background `#FAFAFB`, white plotting surface, primary text `#20242C`, secondary text `#555D6B`, dividers `#D8DCE4`, blue accent/trace `#2457C5`, blue translucent selection, amber warning `#8A4B08`, red error `#B42318`. Verify actual foreground/background contrast during implementation. Use the system UI font stack, a normal 14–16 px control/body size, restrained spacing, and visible focus outlines. No green states, gradients, drop shadows, pill status badges, stock illustrations, or decorative icon sets.

### 17.2 Deliberate text placement

The persistent workspace explains itself in three places only:

1. **Identity/status line:** source filename, saved/current revision, and state. Use the state text here rather than repeating badges throughout the page.
2. **Form/results area:** field labels, units, the three result labels and relevant actions. One result freshness message appears only when needed.
3. **Chart caption:** the fixed total integration window. No repeated scientific disclaimer below every result.

Import instructions appear only inside the import dialog: `CSV · time_min,signal_au · 2–2,000 points · up to 256 KiB`, plus one short note that signals must be nonnegative and already prepared. Link to a synthetic example file. Detailed calculation assumptions, audit metadata and build versions belong in the report, optional history details, or docs. Do not reduce text by scattering many abbreviated helper messages.

An empty workspace contains **Import trace** and a sample-file link, not a dashboard or onboarding tour. The completed report is a plain document/table layout. Successful saves update the one status line; avoid a separate toast if it adds no information. Errors appear at the affected field or as one operation message above the form.

### 17.3 Chart behavior

- Use SVG `scatter`, `mode: 'lines'`, `line.shape: 'linear'`, and disable line simplification if it would omit measured vertices. Render all points, with no smoothing, resampling, or data-dependent decimation.
- Axes are `Time (min)` and `Signal (AU)`; hover shows the measured time and signal. No biological labels or inferred peak boundaries.
- Highlight the selected interval with a translucent vertical rectangle and boundary lines. Invalid/incomplete boundaries remove the draft rectangle instead of leaving an apparently valid old interval. Historical mode highlights the historical bounds.
- Keep zoom/pan independent of analysis. Use stable `uirevision` per run and separate viewport state; rebuilding selection shapes must preserve the user's zoom. **Reset zoom** changes the viewport only. **Use full trace** changes the boundary inputs and invalidates the selected result.
- Keep the Plotly modebar hidden; provide a small accessible toolbar with Zoom, Pan and Reset zoom. No image export, lasso/box-selection analysis tool, editable title, cloud link, or Plotly logo control. Double-click may reset the viewport; it must not reset bounds.
- A chart failure must leave the numeric fields, point table and stored result usable, with one chart error message. A responsive chart resizes when history opens and on viewport changes.

Plotly provides persistent UI revision behavior and configurable chart controls; the application still owns the separation between viewport and scientific parameters. [UI revision](https://plotly.com/javascript/uirevision/) and [configuration options](https://plotly.com/javascript/configuration-options/).

### 17.4 History, data and review summary

**History** opens a flat side region on wide screens and an accessible dialog/drawer on narrow screens. Each row shows revision number, start/end, fraction, author and time. Expanding/selecting a revision reveals its reason and other results. Viewing an older revision is read-only and clearly says `Viewing revision N`; **Back to latest** restores the current run. The reviewed revision is labeled in text. A disclosure at the bottom exposes the three kinds of committed audit events; do not duplicate the entire audit log permanently beside the chart.

**Data** exposes a semantic table of time/signal values, with row numbers, a caption, column headings and all points available. At 2,000 points, simple pages of 100 rows with previous/next controls are sufficient; do not use inaccessible virtualization. The source download remains available as an additional option, not the only accessible representation.

**Complete review** opens a confirmation showing the exact revision number, interval, fraction, and an optional review note. The message is one sentence: `Complete review of revision N? This run will become read-only.` Use **Complete review** and **Cancel**. Default focus goes to the dialog heading or Cancel, not the irreversible action. Unsaved changes must be resolved before this dialog can open.

After completion, the same workspace displays the saved reviewed result and read-only boundaries, with **View report**, **Download JSON**, **Source**, and **History**. The report route shows source identity/hash, reviewed revision, boundaries/windows, values/units, author/times, reason/note and algorithm/build identifiers as a simple document. No PDF generation, print designer, or spreadsheet export.

### 17.5 Accessibility requirements

Use semantic headings, labels and tables; associate field errors with `aria-describedby`; announce asynchronous status in one polite live region. Invalid fields receive `aria-invalid`; saving/preview buttons expose disabled/busy state. Focus returns to the opener when a dialog closes. Keyboard users can import, enter bounds, preview, save, inspect history/data, complete and download without interacting with the plot.

Preserve native tab order and visible focus. Do not use color alone for dirty, saved, locked or error states. Provide a concise chart description and the Data alternative. Respect reduced-motion preference; no animation is needed. Test keyboard operation and at least one screen-reader walkthrough in addition to automated accessibility checks. [W3C guidance on complex graphics](https://www.w3.org/WAI/tutorials/images/complex/).

## 18. Frontend state and asynchronous behavior

### 18.1 State ownership

Keep one server snapshot for the selected run; one editable draft with **raw strings** for start, end and reason; the selected historical revision ID or null; one preview record keyed to parameters; and a small operation state (`idle`, `previewing`, `saving`, `completing`, `refreshing`). Session and dialog/viewport state are separate concerns. A reducer is appropriate for transitions; do not add a general state-management framework.

Derive validity, parameter equality, numerical-result freshness and unsaved-work status from those values. Avoid independent booleans such as `isDirty`, `isSaved`, `isReviewed`, `previewValid` that can disagree. A reason-only edit is unsaved work but does not invalidate a numerical preview. Compare numeric boundary values for equality after valid parsing, while preserving the raw input for editing. Do not use display-rounded strings for comparisons. [React state-structure guidance](https://react.dev/learn/choosing-the-state-structure).

Use labeled text inputs with `inputMode="decimal"` and the documented numeric grammar so partial input can remain visible. Do not convert an empty string into zero. No implicit rounding, comma-to-period conversion, or auto-correction. Associate a simple correction message with invalid input. Enter from a boundary field may calculate a preview; it must never complete a review or save without the reason/action being explicit.

### 18.2 Observable states and transitions

| State | Results and controls |
|---|---|
| No imported trace | Import action and sample link; no empty chart/results scaffold. |
| Imported, no revision | Default boundaries cover the full trace. Show total area/window as source metadata; selected area and fraction are uncalculated until preview. Status: `No saved revision`. |
| Latest saved revision, unchanged | Display that immutable revision's values and bounds. Status: `Saved revision N`. Completion is available. |
| Invalid edited bounds | Keep typed values, associate errors, remove invalid draft highlight, disable preview/save/completion. Never present the old selected result as current. |
| Valid edited bounds, no matching preview | Update the highlight; replace selected area/fraction with em dashes and `Calculate preview`. The fixed full-trace total remains valid. |
| Preview pending | Inputs can remain editable; disable duplicate preview submission; announce calculating once. A subsequent edit invalidates that request's result. |
| Matching preview | Show its returned result with `Unsaved preview`. Save requires a nonempty valid reason. Completion remains unavailable until saved. |
| Save pending | Freeze that submitted form and disable repeat submission; keep values and reason visible. |
| Save success | Use the server receipt, then refresh detail. Load the saved revision's round-trippable bounds, clear the reason only after confirmed success, and show its revision number. |
| Save failure / unknown outcome | Preserve the entire draft. Distinguish validation failure from retryable failure, stale version, and uncertain commit; use section 15's retry rules. |
| Historical revision | Show that revision's saved bounds/results read-only. Chart zoom is still allowed. No save, preview, or completion action targeting the historical revision. |
| Reviewed run | Load saved reviewed data, never automatically recalculate it. Analysis controls are read-only; report/source/history remain available. |

Saving an intentionally new reason with unchanged bounds is allowed and creates a new revision; require an explicit current preview and reason. Do not create revisions on blur, navigation, zoom or preview. There is no “edit revision” operation.

### 18.3 Request freshness

Each preview request captures the run ID, normalized numerical bounds and a monotonically increasing local request generation. Use `AbortController` when a new preview, boundary edit, navigation or unmount supersedes it. Cancellation alone is insufficient: only apply a response if its generation, run ID and echoed bounds still match. Changing bounds and changing them back must not accidentally accept an older generation. A reason edit alone can retain the matching preview.

If a preview reports a newer observed run version than the snapshot, do not silently update the save precondition. Surface that newer work exists and offer Reload latest. The save endpoint always recalculates independently; no preview token or browser percentage is authoritative.

Run-load requests need the same identity/generation guard: a slow response for trace A must not replace trace B. On reload/focus after another tab may have worked, avoid automatic replacement of an edited form; fetch and compare versions first. Polling and WebSockets are unnecessary.

### 18.4 Leaving work and recovering authentication

Unsaved work means a changed/invalid boundary string relative to the loaded baseline, a nonempty new reason, or a first unsaved preview with no revision. A preview identical to an existing saved revision with no new reason does not need a discard warning. Opening the history list alone does not discard work; selecting another revision, trace or report route does.

Use one small **Discard changes?** dialog for explicit in-app navigation, history selection and sign-out. Attach `beforeunload` only while work would be lost, understanding that browsers supply their own wording. Keep form state during ordinary dialog opening and request failures. Browser refresh intentionally restores persisted records; do not promise draft recovery after a tab closes. No localStorage draft system is needed.

Completion is allowed only when viewing the latest saved revision with no unsaved boundary/reason work, no outstanding mutation, and a current server snapshot. Its dialog captures the exact revision and expected version; a later concurrent save causes a 409 rather than completing a different revision.

## 19. Reviewed record and original source export

The API report and React report page use the same saved data. The report builder must not call the calculation function or reinterpret old source bytes. A new algorithm version must not change a previously reviewed number. Server build details in the record describe the saved analysis and review, not the server version that happens to export it later.

Use report schema identifier `tracereview-report-v1`, with this structure:

```text
schema_version
trace:
  id, label, imported_at, imported_by (id + saved name)
  point_count, parser_version
source:
  filename, byte_count, sha256, encoding: "base64", content
review:
  revision_id, revision_number, reviewed_at, reviewed_by (id + saved name)
  review_note, application_build
revisions[]:
  complete immutable revision snapshots, including reasons and calculation metadata
audit_events[]:
  committed actions and before/after context; no internal retry fingerprints/receipts
```

The reviewed revision is identified by `review.revision_id`, not by whichever element is last in an array. The JSON includes the bounded original CSV bytes encoded as base64, making the record self-contained and allowing its source SHA-256 to be checked independently. Do not duplicate parsed points in the report as well; they can be reconstructed from the source under the documented parser contract. Normal workspace detail still returns the stored points directly.

The report includes all saved revisions so the final result's rationale and earlier changes remain available. Array ordering is deterministic: revisions by increasing revision number, events by increasing `version_after`. Use stable field ordering, UTF-8, two-space indentation, LF and one terminating newline. Do not add an export-time timestamp, current username lookup, transient URLs, or current-runtime metadata that makes unchanged reports differ. Repeated downloads of the same completed run should have identical bytes within report schema v1.

The UI may format these numbers, but download serialization does not round them. Export all finite numeric values with Python's round-trippable JSON representation and reject nonfinite output. Use a safe attachment filename such as `tracereview-<run-id>-r<number>.json`; the separate source endpoint returns the exact uploaded bytes through a protected attachment response. Set private/no-store cache policy on API responses and sensitive downloads. [Django file-response handling](https://docs.djangoproject.com/en/5.2/ref/request-response/#fileresponse-objects).

Verify the decoded source's checksum in export tests, and verify that the downloaded CSV is byte-identical to the upload, including BOM/CRLF variants. A checksum and application audit history do not prove external origin or prevent deliberate database edits; retain the baseline's limited claims. Do not advertise regulatory compliance, electronic signatures, certification, or sample approval.

## 20. Implementation preparation: exact sequence

This stage runs at the beginning of the **next implementation pass**. Commands below are planned commands; nonexistent scripts/manifests are to be authored before their commands are run.

1. Read this whole document and recheck the workspace for newly added user files/instructions. Create a normal Git repository on `main` if it is still absent. Add `.gitignore` and `.gitattributes` before generating data or artifacts. Preserve this plan.
2. Create `LICENSE` with the chosen MIT attribution and a minimal README. Create the public `fullstack-nick/TraceReview` repository using the authenticated account, after checking its name again. If it now exists, inspect it and connect only if it is the intended project; never replace it or force-push over unrelated content. Do not create cloud hosting or workflow files.
3. Write root `pyproject.toml` with the exact backend dependencies, `[tool.uv] package = false`, and Python range `>=3.13,<3.14`; write `.python-version`. Run `uv lock` then `uv sync --locked`. All later backend commands use `uv run --locked`, not the PATH Python.
4. Write the frontend manifest with the exact direct set in section 11; run npm with `frontend` as the actual working directory. Generate `package-lock.json`, then prove `npm ci` can reproduce it. Do not install the old Plotly type packages. Do not use `--legacy-peer-deps` or force through incompatibilities.
5. Run the pinned Playwright CLI's Chromium installation check. Confirm an actual headless page can launch. Verify the selected NumPy imports and `trapezoid` operation, Django check against an empty test configuration, Plotly basic-bundle import, TypeScript compilation and a minimal Vite build. These small environment checks establish readiness before feature work.
6. Implement the configuration and local scripts outlined in section 12. Test both the Vite proxy and compiled single-origin serving path early; leave all user data outside Git. Configure a dedicated test database path from the beginning.

Representative preparation commands, once the referenced manifests exist:

```powershell
git init -b main
uv lock
uv sync --locked
uv run --locked python -c "import django,numpy,sqlite3; print(django.get_version(), numpy.__version__, sqlite3.sqlite_version)"
Push-Location frontend
npm.cmd install
npm.cmd ci
npx.cmd playwright install chromium
Pop-Location
```

Use explicit error checks after external commands in PowerShell; `ErrorActionPreference` alone does not reliably turn every nonzero executable exit into a terminating error. Scripts must propagate failures and avoid continuing to migrations or publication after a failed build/test.

GitHub creation can use `gh repo create fullstack-nick/TraceReview --public --source . --remote origin --description "Local scientific trace review with reproducible analysis revisions."` after a first local documentation commit. Push reviewed commits normally. This is source publication, not deployment. [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create).

## 21. End-to-end work packages, in dependency order

These expand the original six milestones rather than replacing them. The next pass should execute the sequence continuously, run the relevant checks at each gate, fix failures and proceed; ordinary implementation choices do not require repeated approval.

| Stage | Concrete work | Completion gate |
|---|---|---|
| Preparation | Repository, MIT, pinned environments, GitHub remote, scripts/configuration and basic local serving checks from section 20 | Python, TypeScript, Plotly, SQLite and Chromium can execute; no package compatibility blocker. |
| Milestone 1: workflow and fixtures | Create the three short domain documents from this addendum; generate/commit fixtures; record source hashes; turn the wireframe/state table into a concrete screen specification | Every result, state, field and action has defined semantics; fixtures have independent expected checks. |
| Milestone 2: numerical core | Implement strict CSV parsing, error locations, source hashing, interpolation and integration as pure modules; write the numerical/parser tests | Hand-derived examples and all required invalid-input boundaries pass independently of views/models. |
| Milestone 3: React workspace | Build the flat layout, chart, inputs, state reducer, import/history/data/review dialogs and report view using a fixture adapter | Keyboard input and state transitions work; stale results disappear; zoom does not edit bounds; no cards/green/extra copy. |
| Milestone 4a: persistence and auth | Add the three models/migrations, session/login/logout flow, owner filtering, immutable metadata and import/preview endpoints | A source upload survives reload exactly; unauthorized/CSRF attempts fail; preview creates no records. |
| Milestone 4b: revisions and integration | Add transactional revision saving, audit events, expected versions, operation IDs/retries; replace the fixture adapter with real API requests | Two reasoned revisions survive restart; stale/network failures preserve edits; duplicates and partial writes are prevented. |
| Milestone 5: completion and records | Add exact-revision completion, backend lock, read-only history/report, deterministic JSON/source downloads | Reopened review matches the saved snapshot; direct API writes fail; exports round-trip and do not recalculate. |
| Milestone 6: usability and hardening | Run complete browser tasks, failure paths, accessibility/manual checks; make one evidence-based improvement; finish built local mode and backup/restore | All mandatory local checks pass; usability evidence is accurately labeled; ordinary use requires no network. |
| Final handoff | Rebuild from a clean committed tree, verify fresh setup, update README/evidence/notices, push public source, show local running app and repository | A new checkout can be set up using the documented commands; deliver working source, test evidence, limitations and a concise demo path. |

Milestone 3's fixture adapter is temporary development scaffolding. It must not become a second numerical implementation or return synthetic success values in the final app. Use known fixture responses for interaction development and remove/unwire the adapter before the integration gate. Do not defer validating the actual production bundle until the final stage.

Suggested checkpoints: foundation/specification, calculation, workspace, persistence, reviewed record, final validation. A one-pass implementation can still use these local commits for review and recovery. No artificial maintenance change or extra assay should be introduced to fill out the project.

## 22. Verification matrix and acceptance criteria

Test the risks, not the number of files. Use the Django test runner for pure logic, model/service/API behavior and real database transactions. Use Playwright for user-visible behavior with real React and Django. Locators should use roles and accessible labels; reserve direct plot-coordinate assertions for the chart's visual behavior. [Playwright best practices](https://playwright.dev/docs/best-practices).

### 22.1 Required checks

| ID | Risk / requirement | Evidence to implement |
|---|---|---|
| CALC-01 | Incorrect area/interpolation | All six hand-worked examples in section 13; endpoints on/between points and both bounds within one segment. |
| CALC-02 | Window/precision mistakes | Full width = 100%; irregular spacing; zero selected area; invalid/equal/reversed/outside bounds; finite/nonfinite/overflow cases; round-trip saved precision. |
| CSV-01 | Silent input alteration | Header order/case/extra/missing columns, empty/malformed/overlong cells, NaN/Inf/underscore/comma decimal, negative signal, unordered/duplicate times, time rounding collapse, nonzero underflow and invalid encoding all reject with useful location. |
| CSV-02 | Boundary sizes | 2 and 2,000 points accepted; 0/1/2,001 rejected; 256 KiB boundary enforced; oversized envelope/file produces 413; blank records vs final newline handled as specified. |
| CSV-03 | Source loss | BOM and CRLF retained byte-for-byte; SHA-256 matches original upload and exported base64; deliberately identical imports with different operation IDs remain separate runs. |
| AUTH-01 | Unauthorized access | All domain routes require login; second user's list/detail/source/report/history cannot access the first user's run; no admin or role-management path. |
| AUTH-02 | Login/CSRF holes | With actual CSRF enforcement enabled, missing/wrong token fails on login, import, save, complete and logout; valid token works; login token rotation works through the Vite proxy and built mode. |
| AUTH-03 | Lost draft on session expiry | Expired session preserves draft, reauthentication reloads version, no automatic mutation, and a different login clears prior user's data. |
| DB-01 | Mutable history | Revision/audit update/delete routes absent (405/404); service/model rules reject overwriting; author/time/results supplied by client rejected as unknown fields. |
| DB-02 | Partial transaction | Force audit insertion failure for import, save and completion; assert source/run/revision/status/version changes all roll back. |
| DB-03 | Lost update | Two clients with the same version: one save commits, the other conflicts. Assert exactly one new revision/event and one version increment. |
| DB-04 | Save/completion race | Concurrent saves and completion competing for one expected version cannot lock an unintended revision; test real independent SQLite connections and bounded busy handling. |
| DB-05 | Duplicate retry | Repeat same operation ID/body for import, save and completion: original result, no extra event/version. Reuse ID with different payload → 409; lost response after commit can be retried safely. |
| FLOW-01 | False review lock | No-revision completion fails; historical/stale target fails; completed run rejects both preview and revision writes; second new completion conflicts, original completion retry succeeds. |
| UI-01 | Stale numerical result | Changing valid or invalid bounds removes old selected values from the current-result position; highlight and field errors match draft. Reason-only edit keeps correct numerical preview. |
| UI-02 | Late response | Delay preview A, edit/request B, let A return last; only B may display. Repeat across trace navigation and edit-away/edit-back. |
| UI-03 | Zoom affects analysis | Zoom/pan/reset zoom do not change bounds, total area, percentage, status or run version; Use full trace does invalidate the draft result. |
| UI-04 | Failed save loses work | Inject validation, 503, 500/non-JSON, network failure and post-commit response loss; values/reason stay visible; retry/reconciliation follows the correct path. |
| UI-05 | Accidental discard/completion | Trace/history navigation, browser Back/Forward and logout guard dirty work; Cancel preserves it; completion is disabled until edits are resolved. |
| REPORT-01 | Report uses current code | After completion, patch the calculation function to fail; report/history/source still work and preserve stored numbers. |
| REPORT-02 | Record mismatch | Report reviewed ID, reason/note, author/time/windows/units/build/source hash match the saved revision; same report downloads are byte-identical. |
| E2E-01 | Complete actual workflow | Login → import synthetic trace → preview → save reasoned revision → change interval → save second revision → inspect first read-only → complete latest → restart/reload → read report/download JSON/source. |
| A11Y-01 | Inaccessible primary workflow | Keyboard-only journey, modal focus return, field errors, semantic Data/history tables, status announcements, contrast and non-color state communication; automated axe check plus a recorded manual check. |
| LOCAL-01 | Hidden runtime internet dependency | With external HTTP(S) browser requests blocked but loopback allowed, built app still logs in/imports/previews/saves/completes/exports; no remote assets or telemetry requests. |
| LOCAL-02 | Setup/runtime fragility | Fresh checkout + locked install + migrate + init analyst + build + start works; second setup preserves data/credentials/secret; port collision fails usefully. |
| LOCAL-03 | Data recovery | Backup database, restore into a separate test location with app stopped, reopen exact reviewed result and compare exports. |

For database race tests, use `TransactionTestCase` with a dedicated **file-backed** SQLite test database and separate connections/threads or processes. Ordinary `TestCase` transaction wrapping and a shared in-memory database are not sufficient evidence of the chosen lock strategy. Assert final records and versions, not only response codes. Keep tests isolated from `.local/tracereview.sqlite3`.

CSRF tests must use a client with CSRF enforcement enabled. DRF's convenience clients can otherwise skip the very protection under test. Browser tests use a dedicated test analyst and isolated database; reset only that explicit test path, never user data.

Run Chromium as the automated browser target. A manual smoke in the installed Edge is useful; Firefox/WebKit/browser-farm coverage is outside scope. Accessibility automation does not establish complete accessibility; record exactly which manual steps were performed.

### 22.2 Local command contract

Once scripts and tests exist, the documented verification entry point is `./scripts/verify.ps1`. It runs the equivalent of these commands, with explicitly isolated test settings:

```powershell
uv run --locked python backend/manage.py check
uv run --locked python backend/manage.py makemigrations --check --dry-run
uv run --locked python backend/manage.py test
Push-Location frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npx.cmd playwright test
Pop-Location
```

Run the browser journey against development-proxy mode during integration and against the compiled Waitress/WhiteNoise application for final acceptance. The test harness starts/stops its own servers and does not reuse a personal running instance (`reuseExistingServer=false`). Use separate test ports 8001/5174 or a dedicated built-test port, consistent trusted origins and a dedicated database setting.

Document actual commands, package versions, commit, date, counts and failures/fixes in `docs/evidence.md`. Store large Playwright traces/screenshots locally and commit only useful synthetic screenshots/evidence intentionally selected for documentation. Do not fabricate test results, participant quotes, benchmarks, or untested platform support.

## 23. Usability evidence and final completion standard

The implementation should be technically complete in one pass. Human validation cannot be manufactured to satisfy a checkbox. Prepare the original three tasks as a concise script:

1. Open a saved run and identify the exact interval used for its displayed result.
2. Inspect two revisions and explain why their reported fractions differ.
3. Make a reasoned revision and complete it without losing work or confusing preview with saved state.

If a participant is available, record their role in general terms, task outcome, observed hesitation, the resulting design change, and a repeat of the affected task. Do not contact another person or send data without explicit user authorization. A domain participant is needed to validate scientific terminology; a general user can assess navigation and state clarity.

If no participant is available during the one-pass build, perform and record an implementer-led cognitive walkthrough plus the automated journey, make one justified improvement, and label human/domain validation **pending**. This can satisfy the technical delivery gate, but it does not satisfy or replace the original human-usability evidence goal. Keep that limitation explicit in the handoff. If no screen reader is available for the manual accessibility check, record that limitation similarly rather than claiming the check passed.

The technical delivery is complete when:

- The original demonstration story works on the actual locally served build, including restart, historical inspection, final locking and both downloads.
- The numerical, parser, ownership/CSRF, transaction, concurrency, idempotency, UI-freshness and export checks above pass.
- The UI follows the flat, minimal, no-green design and shows only useful text; keyboard and narrow-viewport use are verified.
- A fresh setup is reproducible from locks and documented commands; local data/credentials survive reruns, stay out of Git and can be backed up/restored.
- The public repository exists, contains MIT licensing and required third-party notices, and contains no cloud deployment or CI/CD configuration.
- Documentation accurately separates tested functionality, scientific limitations and any outstanding human validation.

Do not call the project scientifically validated, regulated-ready or tamper-proof. Its value is the narrowly defined calculation and reconstructable local review workflow.

## 24. Research ledger and next-pass handoff

### 24.1 Completed during this planning pass

| Investigation | Evidence / conclusion |
|---|---|
| Baseline preservation | Original attachment copied into this document; only four company-linked passages changed with explicit user permission. All new decisions are appended. |
| Repository inspection | Empty directory, no Git repository or applicable instruction files at inspection time. |
| Local tools | Actual versions of OS, shell, Python interpreters, uv, Node/npm, Git/gh, SQLite and browsers checked. |
| GitHub readiness | Existing CLI authentication works; intended owner is `fullstack-nick`; target repository did not exist when checked. No repository created in this pass. |
| Backend availability | Exact selected packages resolved in an isolated Python 3.13.14 environment with binary-only artifacts required; Windows NumPy wheel verified. No dependency installation into the project. |
| Frontend availability | Exact selected manifest passed strict npm peer/engine resolution and lock generation outside the repository. This was metadata resolution, not a build or audit. |
| Plotly integration | React/version peers, bundled declarations, factory export and precompiled basic-bundle file checked in published metadata/package contents. |
| Browser readiness | Playwright 1.63.0's required Chromium revision matches cached executable revision 1243. Launch remains a preparation check. |
| Main integration risks | SQLite row-lock limitation, immediate transactions, login CSRF, stale previews, retry-after-commit, source-byte preservation and static-serving arrangement researched and resolved in this specification. |
| Design decisions | Concrete flat layout, palette, text placement, accessibility alternatives and all significant workflow states specified. |
| Scientific scope | Strict CSV grammar/limits, precision policy, interpolation, units, independent examples and deterministic fixture formulas specified. |
| Verification and release | Local command sequence, risk-based test matrix, GitHub/MIT/no-CI constraints, usability evidence distinction and final acceptance defined. |

### 24.2 Remaining work is implementation, not an open architecture choice

There is no unresolved architecture decision that needs to block the next pass. The chosen defaults are the browser-based loopback app, one analyst role, Django/React/SQLite, explicit preview/save/complete, a versioned self-contained JSON report, and the package set in section 11.

Still to be executed during implementation: project dependency installation, runtime smoke checks, source code and fixtures, tests, actual screenshots/usability evidence, the GitHub repository, MIT file/notices, and a fresh-checkout run. Do not confuse a successful resolver with a successful application. If a pin becomes unavailable or a smoke test exposes a real incompatibility, record the smallest necessary adjustment here and proceed with the same architecture.

Future project work should start at section 20, follow section 21, and use section 22 as its acceptance checklist. Preserve the original plan above and extend this addendum when new evidence makes a small clarification necessary.

## 25. Implementation decisions and delivery (2026-10-04)

The subsequent instruction authorized full end-to-end implementation. The original proposal and research above are retained unchanged. The implemented workflow, numerical contract, architecture/API, and observed evidence are documented in `docs/workflow.md`, `docs/calculation.md`, `docs/architecture.md`, and `docs/evidence.md`.

- The public source repository is `https://github.com/fullstack-nick/TraceReview`, with MIT licensing and third-party notices. Application data, account credentials, secrets, test databases, build outputs, and logs remain ignored locally. There is no CI/CD or cloud deployment configuration.
- The selected package pins resolved and executed on this Windows machine. TypeScript 6.0.3 is used as researched for compatibility with the selected lint tooling. Plotly's own declarations and its precompiled basic bundle work with the React factory API. Python 3.13.14 and Node 24.19.0 are the tested runtimes.
- The frontend was connected directly to the real numerical/API implementation during construction; a separate temporary fixture adapter was unnecessary. The final application contains no mock calculation or synthetic success path. Synthetic files are ordinary input fixtures.
- Small React components/hooks express the state transitions without a separate reducer or state-management package. Raw boundary strings, preview generation/abort guards, pending operation IDs, conflict state, and immutable saved DTOs retain the specified semantics. Focus/visibility return compares server versions without replacing local edits.
- Container-based Plotly sizing corrects observed narrow-viewport overflow. Lazy chart loading and error boundaries preserve access to numerical controls/Data if plotting fails. The blue/neutral flat layout, sparse state text, semantic tables, and keyboard path are exercised in browser checks.
- Build/runtime provenance snapshots identify the running backend's commit, dirty flag, and runtime versions. A clean committed build and process restart are required before reference records; `.local/build.json` is operator metadata, not a mutable replacement for stored revision provenance.
- The local command entry points are `scripts/setup.ps1`, `scripts/build.ps1`, `scripts/start.ps1`, `scripts/dev.ps1`, and `scripts/verify.ps1 -IncludeDev`. Tests isolate their databases and servers. `backup_database` uses SQLite's backup API and refuses existing destinations; a restored record is verified in fresh processes.
- Human/domain usability validation and a screen-reader walkthrough remain pending. Agent-led cognitive walkthrough, visual inspection, keyboard automation, axe checks, and the resulting responsive-layout improvement are recorded separately and are not represented as a human study.

Final commit identifiers, test counts, reproducible setup, and restart evidence are maintained in `docs/evidence.md` rather than rewriting the earlier planning ledger.
