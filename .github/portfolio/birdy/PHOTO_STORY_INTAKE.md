---
project: I Am Birdy
status: awaiting-selected-photos-and-owner-notes
issue: https://github.com/jordanistan/illnetwork/issues/47
updated: 2026-10-04
---
# Turn Birdy's photos into stories

Source album supplied by Jordan: https://photos.app.goo.gl/hmzCdVn8bEniivNn8 . Access was denied in this cloud browser. Do not try alternate routes to bypass that denial. The native repository currently has one real photo, `iambirdy.jpg`; the new photo deck shows exactly that one photo. It does not automatically synchronize Google Photos.

An owner-authenticated local Codex can work from photos Jordan downloads to an explicitly supplied local folder, or Jordan can upload selected photos here. Start with 6–12 favorites spanning different outings. Keep original full-resolution masters outside the public repository; add appropriately sized public copies with descriptive filenames. Preserve natural appearance. If editing images, follow the available image-editing instructions.

For each selected photo, capture this short record. Notes can be rough; an editorial agent can turn confirmed facts into engaging copy.

| Field | Owner notes |
|---|---|
| Photo filename | |
| Place name and general location | |
| Visit date or approximate period, if known | |
| What Birdy did | |
| Favorite moment / why this photo matters | |
| Useful dog-travel detail, if personally observed | |
| Public caption approved? | |

Do not infer a location from a background, invent a date, or present a planned trip as completed. Avoid publishing exact live whereabouts or private location metadata. Remove unneeded EXIF location data from public export copies before committing. If a fact is unknown, omit it.

## Suggested story format

**Title:** a vivid phrase grounded in the actual visit.

**Place / period:** confirmed owner notes only.

**The moment:** 2–4 warm sentences about what happened, with Birdy at the center.

**A useful detail:** a short firsthand tip, when available. Recheck time-sensitive venue rules against the official venue source and record the date.

**Photo caption / alt:** caption tells the story; alternative text describes the visible photo without guessing.

## Implement in GitHub

Central source: `portfolio/birdy-gallery.json`, `portfolio/birdy_gallery.py`, and `portfolio/build.py`. Native review: `birdy-gallery.json`, `scripts/build_gallery.py`, and `scripts/birdy_gallery.py`.

- Place reviewed central photos in `portfolio/assets/birdy/`; use `assets/birdy/filename.jpg` in the central JSON. The builder copies only manifest-listed files.
- Place native copies in `site-assets/gallery/`; use `site-assets/gallery/filename.jpg` in native JSON. Rebuild with `python3 scripts/build_gallery.py`.
- Each entry has `src`, `alt`, and `caption`; all text is escaped during build. Use long captions for verified place/moment descriptions; a separate full story page can follow when enough facts are supplied.
- Keep the two manifests and renderers aligned. Do not publish scripts, manifests, or operational notes.
- Run existing release tests, JS syntax and artifact checks in each repo. Coordinate any stricter artifact-allowlist additions with P013's owner; do not edit claimed checker files independently.
- Test multiple slides on phone/desktop, arrow buttons, Left/Right/Home/End, manual swiping/scrolling, focus, resizing, reduced motion, and no-JS scrolling. With one slide, both buttons correctly remain disabled.
