# Domain studio

Dependency-free static websites for Jordan Robison's active domain portfolio. The Linux scanner in the parent repository is preserved.

```bash
python3 portfolio/build.py --mode preview --output _portfolio-preview
python3 portfolio/check.py _portfolio-preview
python3 portfolio/build.py --mode production --domain pawsfectwalks.com --output _production/pawsfectwalks
python3 portfolio/check.py _production/pawsfectwalks --domain pawsfectwalks.com
```

`portfolio/check.py` requires at least one HTML page and enforces an explicit
artifact allowlist. Generated exports may contain only the standard site files,
the review catalog, the three ILL lab downloads, approved Starfield vector
studies, and Birdy's opaque WebP/MP4 derivatives. Active domain directories come
from `sites.json`; held domains, source files, arbitrary text/JSON, and all other
paths are rejected. Domain-specific lab, Starfield, and Birdy files are allowed
only under their matching brand. The same checker validates the full preview;
single-domain production checks must supply `--domain` as shown above.

Preview mode is an educational design review: no forms, payment links, email capture, or live booking. Production mode enables email inquiries and draft prices. An inquiry is never a booking or payment. No card data, credentials, home addresses, medical information, or pet access codes belong in these sites or GitHub.

Start with Pawsfect Walks and SpaceGhostKilla. Supporting domains get distinct landing pages linking to their primary brand; they are not separate companies. Health brands remain educational, and Starfield is a concept pending name clearance and an approved print catalog.

See `.github/portfolio/STATUS.md`, `ROADMAP.md`, `DECISIONS.md`, and `LAUNCH.md` in the repository root. Edit `portfolio/sites.json` and source assets, then rebuild. Never edit generated output as the source of truth.
