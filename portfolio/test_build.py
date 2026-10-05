import importlib.util
from pathlib import Path
import tempfile, unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('studio_build',ROOT/'build.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class ReleaseBoundaryTests(unittest.TestCase):
    def test_preview_disables_lead_capture_and_excluded_domains(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'site'; mod.build('preview',out,None)
            for p in out.rglob('*.html'):
                text=p.read_text()
                self.assertNotIn('mailto:',text)
                self.assertNotIn('<form',text)
                self.assertIn('DESIGN REVIEW',text)
                self.assertIn('noindex,nofollow',text)
            for domain in mod.CONFIG['excluded']: self.assertFalse((out/domain).exists())
            self.assertEqual(14,len([p for p in out.iterdir() if p.is_dir() and '.' in p.name]))
            birdy=out/'iambirdy.com'; html=(birdy/'index.html').read_text()
            self.assertEqual(314,len(list((birdy/'assets'/'birdy').glob('*.webp'))))
            self.assertEqual(29,len(list((birdy/'assets'/'birdy').glob('*.mp4'))))
            self.assertEqual(29,html.count('<video controls preload="none"'))
            self.assertIn("media-src 'self'",html)
    def test_production_inquiry_requires_email_and_no_booking_capture(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'site'; mod.build('production',out,'pawsfectwalks.com')
            html=(out/'index.html').read_text()
            self.assertIn('mailto:jordan.robison@gmail.com?',html)
            self.assertIn('You must send your message',html)
            self.assertNotIn('<form',html)
            self.assertIn('frame-ancestors', (out/'_headers').read_text())
    def test_content_is_escaped(self):
        s=dict(mod.CONFIG['sites'][0]); s['headline']='<script>alert(1)</script>'
        html=mod.page(s,'preview')
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>alert',html)
    def test_unknown_domains_and_nonempty_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit): mod.build('production',Path(d)/'no','sxswasted.com')
            out=Path(d)/'used'; out.mkdir(); (out/'important').write_text('keep')
            with self.assertRaises(SystemExit): mod.build('preview',out,None)
            self.assertEqual('keep',(out/'important').read_text())
    def test_health_site_no_clinical_or_data_claim(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'site'; mod.build('production',out,'healthyheart.clinic')
            html=(out/'index.html').read_text()
            self.assertIn('not a licensed clinic',html)
            self.assertNotIn('<form',html)
            self.assertIn('No appointments, telehealth, diagnosis, or treatment',html)

if __name__=='__main__': unittest.main()
