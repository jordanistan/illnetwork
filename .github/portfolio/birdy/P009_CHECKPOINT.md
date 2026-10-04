# P009 checkpoint — 2026-10-04

Task: Birdy gallery and editorial rewrite / cloud / integration lead. Issue #47; fundraiser follow-up #48. Branch in both repos: `codex/birdy-photo-album-20261004`.

Claim ref: `claims/P009`, acquired at `45c397150ad0c22760d30df4eb48178e1d65d69d` in `jordanistan/illnetwork`. No other claim was modified. P013 checker work remains excluded.

Implemented: real-photo hero; Birdy-specific story/travel-note copy; accessible horizontal photo deck with native scroll snap, manual swipe, arrow controls, keyboard Left/Right/Home/End, count, reduced motion, no autoplay, no-JS scroll fallback. JSON is processed at build time, never fetched in the browser. Escape text and constrain image paths. Existing CSP is preserved; no new scripts, trackers, data capture, credentials or payment handling.

Media limit: one real repository photo only. Browser album access was denied. Do not bypass it. `PHOTO_STORY_INTAKE.md` records the next owner/local-Codex step. No destinations, dates, anecdotes, fundraising amounts or live GoFundMe URL were invented.

GoFundMe: owner selected routine care/adventures. Draft and budget worksheet are in `GOFUNDME_DRAFT.md`; pending USD goal, expense breakdown, period, organizer/recipient and published URL. Account/verification/terms remain owner actions.

Local checks: release boundary tests (5), source/native JS syntax, native artifact check (2 pages), preview and Birdy production artifact checks. Actual remote CI/deployment evidence will be appended to issue #47 after publishing; do not infer it from workflow files.

Next exact task: obtain selected photos with place/moment notes, append reviewed manifest entries, rebuild and test the multi-photo deck on desktop/mobile, then replace the generic travel-note examples with verified photo stories.

Claim retention: connector cannot delete Git refs. After a merged checkpoint, an owner-authenticated local session may release only our unchanged claim using:

```bash
git push --force-with-lease=refs/heads/claims/P009:45c397150ad0c22760d30df4eb48178e1d65d69d origin :refs/heads/claims/P009
```

If the lease fails, coordinate instead of deleting a changed claim. Acquire a new claim before further writing.
