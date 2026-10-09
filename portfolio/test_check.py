import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('studio_check', ROOT / 'check.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)

SAFE_PAGE = '''<!doctype html>
<html lang="en"><head>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'">
<title>Safe page</title>
</head><body><h1>Safe page</h1></body></html>
'''


class ArtifactAllowlistTests(unittest.TestCase):
    def test_minimal_allowed_artifact_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text(SAFE_PAGE)
            self.assertEqual([], CHECK.check(root))

    def test_empty_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = CHECK.check(Path(directory))
            self.assertIn('Artifact contains no HTML pages', errors)

    def test_unexpected_text_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text(SAFE_PAGE)
            (root / 'private-notes.txt').write_text('must not publish')
            errors = CHECK.check(root)
            self.assertIn('Unexpected file in artifact: private-notes.txt', errors)

    def test_allowlist_rejects_unapproved_paths_and_domains(self):
        rejected = (
            'assets/debug.json',
            'labs/private-notes.txt',
            'sxswasted.com/index.html',
            'austinfcsoccer.com/index.html',
            'pawsfectwalks.com/README.md',
            'pawsfectwalks.com/assets/birdy/source.jpg',
            'pawsfectwalks.com/labs/ai.txt',
            'healthyheart.clinic/assets/study-1.svg',
            'spaceghostkilla.com/assets/birdy/birdy-0123456789abcdef.mp4',
            'iamjordanrobison.com/assets/site-0123456789ab.css',
        )
        for path in rejected:
            with self.subTest(path=path):
                self.assertFalse(CHECK.allowed_artifact_file(Path(path)))

    def test_allowlist_accepts_generated_site_shapes(self):
        accepted = (
            'index.html',
            'review.html',
            'pawsfectwalks.com/privacy.html',
            'ill.network/labs/linux.html',
            'ill.network/labs/linux.txt',
            'starfieldstudio.com/assets/study-3.svg',
            'starfieldstudio.shop/assets/study-1.svg',
            'iambirdy.com/assets/site-0123456789ab.css',
            'iambirdy.com/assets/birdy/birdy-0123456789abcdef.webp',
            'iambirdy.com/assets/birdy/birdy-fedcba9876543210.mp4',
        )
        for path in accepted:
            with self.subTest(path=path):
                self.assertTrue(CHECK.allowed_artifact_file(Path(path)))

    def test_single_domain_root_files_require_explicit_domain(self):
        birdy_media = Path('assets/birdy/birdy-0123456789abcdef.webp')
        starfield_study = Path('assets/study-1.svg')
        self.assertFalse(CHECK.allowed_artifact_file(birdy_media))
        self.assertTrue(CHECK.allowed_artifact_file(birdy_media, 'iambirdy.com'))
        self.assertFalse(CHECK.allowed_artifact_file(starfield_study))
        self.assertTrue(CHECK.allowed_artifact_file(starfield_study, 'starfieldstudio.com'))
        nested_birdy = Path(
            'iambirdy.com/assets/birdy/birdy-0123456789abcdef.webp'
        )
        self.assertFalse(
            CHECK.allowed_artifact_file(nested_birdy, 'spaceghostkilla.com')
        )

    def test_cross_domain_file_is_rejected_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text(SAFE_PAGE)
            media = root / 'assets' / 'birdy' / 'birdy-0123456789abcdef.mp4'
            media.parent.mkdir(parents=True)
            media.write_bytes(b'not owner-approved media')
            nested = (
                root / 'iambirdy.com' / 'assets' / 'birdy'
                / 'birdy-fedcba9876543210.webp'
            )
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b'also not owner-approved media')
            errors = CHECK.check(root, 'spaceghostkilla.com')
            self.assertIn(
                'Unexpected file in artifact: assets/birdy/birdy-0123456789abcdef.mp4',
                errors,
            )
            self.assertIn(
                'Unexpected file in artifact: '
                'iambirdy.com/assets/birdy/birdy-fedcba9876543210.webp',
                errors,
            )


if __name__ == '__main__':
    unittest.main()
