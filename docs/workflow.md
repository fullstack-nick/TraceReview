# Review workflow

An analyst needs to identify a manually selected interval, record why those boundaries were chosen, and later reconstruct the exact result. The workspace supports one calculation and one analyst role. Each authenticated account sees its own imported traces.

```text
TraceReview   [Trace selector]   Import                       analyst  Sign out

Trace label                                         Source  Data  History
filename · current state

Zoom  Pan  Reset zoom                              Start       End
                                                 [        ]  [        ]
       signal (AU)                               Calculate preview
       large straight-segment chart               Use full trace
       with selected interval
                                                 Selected-region area fraction
                    time (min)                   — or calculated percentage
                                                 Selected area / Total area
Total integration window: entire trace           Revision reason
                                                 Save analysis revision
                                                 Complete review
```

The layout uses rows, whitespace, and dividers. The chart dominates a wide workspace; at narrow widths the controls follow it. Blue indicates interactions/selection; text communicates every state. Import, data, history, discard, and completion use focused native dialogs. Source and completed JSON downloads are direct authenticated links.

| State | Display and permitted actions |
|---|---|
| Imported | Whole-trace bounds, no selected result yet; preview available. |
| Boundaries edited | Highlight follows valid bounds; selected area/fraction are hidden. Invalid fields explain the correction. |
| Unsaved preview | Authoritative backend values for exactly the current bounds; a reason is required to save. |
| Saved revision | Saved interval/result identified by revision number. Edit, view history, or complete. |
| Historical revision | Read-only exact saved interval, result, reason, author/time; return to latest. |
| Completed review | Read-only reviewed revision, report and source; direct API edits also fail. |
| Failed request | Entries remain. Uncertain writes freeze their payload and retain the operation ID for retry. |
| Stale tab/session | Sign in if needed; explicitly reload latest. Draft entries remain; calculate again before saving. |

Preview does not persist. Save recomputes and commits a revision and audit event together. Completion is disabled while boundaries/reason are unsaved or a write is unresolved. Its confirmation identifies the exact latest saved revision, interval, percentage, and optional review note. Completion locks the whole run. There is no unlock or delete control.

Zoom, pan, and Reset zoom change only the viewport. Use full trace changes boundaries and invalidates the preview. Numeric inputs remain the only way to set analysis bounds; chart dragging never edits them. Data shows the original parsed values in a semantic paginated table. History shows reason, interval, percentage, actor, timestamp, and committed actions.

The reconstruction record contains exact source bytes/hash, parser/algorithm versions, all immutable revisions, reasons, authors/timestamps, build/runtime identifiers, audit contexts, and the reviewed revision ID. The report reads stored values without invoking current numerical code.

Unsaved work lives in memory. Trace/history navigation, browser history, logout, and import guard unsaved changes; browser close/reload uses its standard leave warning. A completed record arriving from another tab keeps the local draft in a “Retained local values” disclosure. Different-account reauthentication clears the previous workspace.

The UI avoids a dashboard, cards, explanatory banners, biological interpretations, and extra configuration. The source contract is described when importing; the denominator is stated once below the chart; errors and temporary recovery instructions appear where needed.
