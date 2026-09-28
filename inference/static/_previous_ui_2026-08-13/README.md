# Previous UI, parked 2026-08-13

The page that was live until 2026-08-13. Kept whole rather than overwritten, per
the house rule in CLAUDE.md: corrections are additive and superseded material is
labelled, not deleted.

Superseded by the redesign that had been sitting unused in `_backup_ui_redesign/`
since it was written. That redesign was already drop-in compatible with `app.js`
— all 79 element ids it addresses were present — but predated two features, so
they were rebuilt into its own structure rather than transplanted:

  - AEGIS metrics (`/api/aegis/stats`, healing log, recent executions)
  - TimeTravelLens (`/api/time_travel/last`, actors, on-demand analyze)

Both lived here as hidden full-screen tabs. They are now always-visible side
sections with detail behind `<details>`.

All 28 `data-tt` tooltips from this page were carried across verbatim, along with
the tooltip engine and its CSS. Nothing was dropped: `rail` and `ctt` were the
only ids not present in the redesign, and every interactive child of `rail`
exists in the new header and side panel.

One behaviour deliberately NOT carried forward: this page wrote
`stats.total_forge_calls || 0` and similar on every AEGIS field, so a dead
endpoint and an idle system produced identical output. The replacement renders
absent values as "—". That is the same defect that let the cocoon dashboard show
a clean, empty, healthy store for eight weeks while its backend raised
TypeError on every request.
