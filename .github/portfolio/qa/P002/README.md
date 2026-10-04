# P002 browser QA evidence

Chromium 143 tested all 14 portfolio domains at 1440, 390, and 320 CSS pixels on October 4, 2026. The checked-in JSON records 42 domain/viewport results; PNGs cover desktop and mobile for every domain, and PDFs cover both printable worksheets.

Verified behavior:

- no horizontal overflow or browser console/page errors;
- visible keyboard focus and working skip links;
- keyboard-operable FAQ sections;
- Pawsfect Walks estimator, Find Fido filters, and ILLNET AI planner;
- readable secondary actions on dark themes;
- explicit worksheet clearing and truthful browser-retention wording;
- complete 40-line worksheet content in print output.

Run a local preview server, then reproduce with:

```sh
PLAYWRIGHT_MODULE=/path/to/playwright node portfolio/browser_qa.cjs http://127.0.0.1:8000 .github/portfolio/qa/P002
```

Screen-reader and physical-printer testing were not performed. Browser coverage was Chromium only.
