#!/usr/bin/env python3
"""Validate publish artifacts, including an explicit file allowlist."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import re, sys, json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'sites.json').read_text())
ACTIVE_DOMAINS = frozenset(
    site['domain'] for site in CONFIG['sites'] + CONFIG['aliases']
)
STARFIELD_DOMAINS = frozenset(
    domain for domain in ACTIVE_DOMAINS if domain.startswith('starfieldstudio.')
)

SITE_FILES = frozenset({
    '.nojekyll',
    '_headers',
    'index.html',
    'privacy.html',
    'robots.txt',
    'sitemap.xml',
    'assets/favicon.svg',
    'assets/hero.svg',
    'assets/site.css',
    'assets/site.js',
})
LAB_FILE = re.compile(r'labs/(?:ai|infrastructure|linux)\.(?:html|txt)\Z')
STUDY_FILE = re.compile(r'assets/study-[1-3]\.svg\Z')
BIRDY_MEDIA = re.compile(r'assets/birdy/birdy-[0-9a-f]{16}\.(?:mp4|webp)\Z')
BIRDY_ASSET = re.compile(r'assets/site-[0-9a-f]{12}\.(?:css|js)\Z')


def allowed_artifact_file(relative, root_domain=None):
    """Return whether *relative* is an approved generated artifact path.

    Full previews contain one directory for each configured active domain. A
    single-domain production export contains the same site files at its root.
    The review catalog is allowed only at the artifact root.
    """
    relative = relative.as_posix()
    parts = relative.split('/')
    artifact_domain = root_domain or 'ill.network'
    if root_domain is None and parts[0] in ACTIVE_DOMAINS:
        artifact_domain = parts[0]
        relative = '/'.join(parts[1:])
    if relative == 'review.html' and len(parts) == 1 and root_domain is None:
        return True
    return (
        relative in SITE_FILES
        or (artifact_domain == 'ill.network' and bool(LAB_FILE.fullmatch(relative)))
        or (artifact_domain in STARFIELD_DOMAINS and bool(STUDY_FILE.fullmatch(relative)))
        or (artifact_domain == 'iambirdy.com' and bool(BIRDY_MEDIA.fullmatch(relative)))
        or (artifact_domain == 'iambirdy.com' and bool(BIRDY_ASSET.fullmatch(relative)))
    )

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.refs=[]; self.errors=[]; self.csp=False; self.lang=False; self.h1=0; self.title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')=='en'
        if tag=='h1': self.h1+=1
        if tag=='title': self.title=True
        if a.get('id'):
            if a['id'] in self.ids: self.errors.append('Duplicate element id '+a['id'])
            self.ids.add(a['id'])
        if tag=='meta' and a.get('http-equiv','').lower()=='content-security-policy':
            self.csp=True
            if "'unsafe-inline'" in a.get('content','') or "'unsafe-eval'" in a.get('content',''): self.errors.append('Unsafe CSP')
        if any(k.lower().startswith('on') for k in a): self.errors.append('Inline event handler')
        if tag=='script' and not a.get('src'): self.errors.append('Inline script')
        if 'style' in a: self.errors.append('Inline style')
        if tag in ('iframe','object','embed','form'): self.errors.append('Unexpected active embed/form')
        if tag=='input' and a.get('type') in ('password','file'): self.errors.append('Unexpected sensitive input')
        key={'a':'href','link':'href','img':'src','script':'src'}.get(tag)
        if key and a.get(key): self.refs.append(('canonical' if tag=='link' and a.get('rel')=='canonical' else tag,a[key]))


def check(root, domain=None):
    root=root.resolve(); errors=[]; pages={}
    if domain is not None and domain not in ACTIVE_DOMAINS:
        errors.append(f'Unknown artifact domain: {domain}')
    for p in root.rglob('*.html'):
        d=Page(); d.feed(p.read_text()); pages[p]=d
        for e in d.errors: errors.append(f'{p.relative_to(root)}: {e}')
        if not(d.lang and d.csp and d.h1==1 and d.title): errors.append(f'{p.relative_to(root)}: missing language/CSP/title or invalid H1 count')
    for p,d in pages.items():
        preview='DESIGN REVIEW' in p.read_text()
        for tag,ref in d.refs:
            u=urlsplit(ref)
            if u.scheme or u.netloc:
                if u.scheme not in ('https','mailto'): errors.append(f'{p.name}: unsafe scheme {u.scheme}')
                if preview and u.scheme=='mailto': errors.append(f'{p.name}: live email in preview')
                if tag in ('script','img','link') and not (tag=='img' and ref=='https://raw.githubusercontent.com/jordanistan/iambirdy/main/iambirdy.jpg'): errors.append(f'{p.name}: external resource {ref}')
                continue
            target=(root/u.path.lstrip('/')) if u.path.startswith('/') else (p.parent/unquote(u.path) if u.path else p)
            if target.is_dir(): target/='index.html'
            target=target.resolve()
            if not target.is_relative_to(root): errors.append(f'{p.name}: reference leaves artifact'); continue
            if not target.is_file(): errors.append(f'{p.relative_to(root)}: missing {ref}'); continue
            if u.fragment and target.suffix=='.html' and unquote(u.fragment) not in pages[target].ids: errors.append(f'{p.name}: missing fragment {ref}')
    if not pages:
        errors.append('Artifact contains no HTML pages')
    for p in root.rglob('*'):
        relative=p.relative_to(root)
        if p.is_symlink():
            errors.append(f'Internal file/symlink in artifact: {relative}')
            continue
        if not p.is_file(): continue
        if not allowed_artifact_file(relative, domain):
            errors.append(f'Unexpected file in artifact: {relative}')
        if p.suffix=='.js':
            js=p.read_text()
            if re.search(r'\b(eval|fetch|localStorage|sessionStorage)\b|innerHTML|document\.write|new Function',js): errors.append(f'Unsafe JS sink/network/storage in {p.name}')
        if p.suffix=='.svg':
            try:
                doc=ET.parse(p)
                for item in doc.iter():
                    if item.tag.endswith(('script','foreignObject')) or any(k.startswith('on') for k in item.attrib): errors.append(f'Active SVG in {p.name}')
            except ET.ParseError: errors.append(f'Malformed SVG {p.name}')
    for e in errors: print(e,file=sys.stderr)
    print(f'Artifact check: {len(pages)} pages, {len(errors)} errors')
    return errors
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('artifact_directory')
    parser.add_argument('--domain', choices=sorted(ACTIVE_DOMAINS))
    args=parser.parse_args()
    raise SystemExit(bool(check(Path(args.artifact_directory), args.domain)))
