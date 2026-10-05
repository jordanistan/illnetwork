#!/usr/bin/env python3
"""Deterministic, dependency-free domain builds. Preview never captures leads."""
from pathlib import Path
from html import escape as esc
from urllib.parse import urlencode
import argparse, hashlib, json, shutil
from birdy_gallery import render_gallery

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'sites.json').read_text())
POLICY = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; font-src 'self'; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
HEADERS = f"/*\n  Content-Security-Policy: {POLICY}; frame-ancestors 'none'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n  Strict-Transport-Security: max-age=31536000\n"
MARKS = {'paws':'p','ghost':'G','lab':'//','ai':'i','jordan':'JR','birdy':'b','fido':'f','hearty':'h','heart':'+','studio':'✦'}

def svg_art(theme):
    bg, ink, accent = {
      'paws':('#e3ebd9','#21593b','#eaaa64'), 'birdy':('#f6d7b4','#9c3d1c','#d07735'),
      'fido':('#dcebc7','#256340','#c6ad66'),'lab':('#e1e8ce','#146843','#96b370'),
      'ghost':('#1c132c','#b991ff','#53d3cb'),'ai':('#18243e','#8ec7ff','#af9bff'),
      'jordan':('#dbe4e3','#284f68','#92aca9'),'hearty':('#efd6c6','#9b462e','#c99266'),
      'heart':('#e1ede7','#37655a','#a8c6bd'),'studio':('#231b2c','#d9adff','#bb765b')
    }[theme]
    grid = ''.join(f'<path d="M{x} 0V500M0 {x}H500"/>' for x in range(0,501,50))
    start = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500"><rect width="500" height="500" fill="{bg}"/><g fill="none" stroke="{ink}" opacity=".09">{grid}</g>'
    if theme in ('paws','fido'):
      art = f'<g fill="none" stroke="{ink}" stroke-width="2" opacity=".22"><path d="M0 100Q140 220 250 120T500 220M0 380Q150 270 280 380T500 310M100 0Q220 130 110 300T220 500M380 0Q250 180 390 300T300 500"/></g><path d="M100 360Q50 150 220 190T380 100" stroke="{ink}" stroke-width="6" stroke-dasharray="10 12" fill="none"/><circle cx="100" cy="360" r="14" fill="{ink}"/><g transform="translate(290 175)"><circle r="76" fill="{accent}"/><path d="M-24 20Q-31 4 -13 -10Q0 -23 13 -10Q31 4 24 20Q13 34 0 27Q-13 34 -24 20" fill="{ink}"/><ellipse cx="-25" cy="-24" rx="10" ry="14" fill="{ink}"/><ellipse cx="0" cy="-38" rx="10" ry="14" fill="{ink}"/><ellipse cx="25" cy="-24" rx="10" ry="14" fill="{ink}"/></g><text x="65" y="440" fill="{ink}" font-family="monospace" font-size="12">ONE GOOD WALK AT A TIME</text>'
    elif theme == 'birdy':
      art = f'<circle cx="250" cy="230" r="180" fill="{accent}" opacity=".24"/><path d="M125 300L130 80L235 180L360 80L380 300Q360 414 250 414Q140 414 125 300" fill="{accent}"/><path d="M150 130L165 215L205 188M340 130L328 215L292 188" fill="{ink}"/><path d="M200 285Q250 230 300 285L314 355Q250 415 186 355" fill="#fff5e8"/><ellipse cx="250" cy="304" rx="24" ry="17" fill="{ink}"/><path d="M250 320V344M223 347Q250 370 277 347" stroke="{ink}" stroke-width="4" fill="none"/><circle cx="183" cy="263" r="10" fill="{ink}"/><circle cx="317" cy="263" r="10" fill="{ink}"/><path d="M160 395Q250 447 340 395" fill="none" stroke="{ink}" stroke-width="12"/><text x="250" y="469" text-anchor="middle" font-family="monospace" font-size="12" fill="{ink}">CHIEF SNIFFER / BIRDY</text>'
    elif theme in ('lab','ai','jordan','ghost'):
      art = f'<g fill="none" stroke="{ink}" stroke-width="2"><rect x="55" y="92" width="390" height="295" rx="12"/><path d="M55 135H445"/><circle cx="80" cy="113" r="4"/><circle cx="95" cy="113" r="4"/><circle cx="110" cy="113" r="4"/></g><text x="87" y="178" font-size="11" font-family="monospace" fill="{ink}">~/lab / {theme.upper()}</text><path d="M90 217L117 239L90 261M135 269H172" stroke="{ink}" stroke-width="6" fill="none"/><g fill="none" stroke="{ink}" stroke-width="2"><circle cx="321" cy="257" r="55"/><circle cx="321" cy="257" r="27"/><path d="M321 189V325M253 257H389"/></g><rect x="87" y="316" width="144" height="6" fill="{ink}" opacity=".45"/><rect x="87" y="338" width="95" height="6" fill="{ink}" opacity=".22"/><path d="M212 388V413M287 388V413M172 420H328" stroke="{ink}" stroke-width="2"/><circle cx="393" cy="360" r="7" fill="{accent}"/><text x="55" y="455" fill="{ink}" font-family="monospace" font-size="11">OBSERVE → UNDERSTAND → BUILD</text>'
    elif theme in ('heart','hearty'):
      art = f'<circle cx="250" cy="235" r="155" fill="{accent}" opacity=".4"/><rect x="130" y="95" width="255" height="330" rx="10" fill="#fffaf6" transform="rotate(8 250 250)"/><g stroke="{ink}" fill="none" stroke-width="2" transform="rotate(8 250 250)"><path d="M166 168H346M166 225H346M166 280H346M166 335H346M166 390H295"/><rect x="164" y="182" width="17" height="17" rx="3"/><rect x="164" y="238" width="17" height="17" rx="3"/><rect x="164" y="293" width="17" height="17" rx="3"/></g><path d="M220 49C220 23 259 21 265 48C272 21 310 23 310 49C310 73 266 97 266 97C266 97 220 73 220 49Z" fill="{ink}"/>'
    else:
      art = f'<defs><radialGradient id="g"><stop stop-color="{ink}"/><stop offset="1" stop-color="{accent}"/></radialGradient></defs><circle cx="250" cy="220" r="136" fill="url(#g)"/><g fill="none" stroke="{ink}"><ellipse cx="250" cy="220" rx="208" ry="53" transform="rotate(-30 250 220)"/><ellipse cx="250" cy="220" rx="218" ry="68" transform="rotate(-30 250 220)" opacity=".35"/></g><g fill="{ink}"><circle cx="75" cy="69" r="2"/><circle cx="419" cy="97" r="3"/><circle cx="396" cy="399" r="2"/><path d="M80 370L84 355L88 370L103 374L88 378L84 393L80 378L65 374Z"/></g><text x="250" y="456" text-anchor="middle" fill="{ink}" font-family="monospace" font-size="12">STUDY NO. 01 / ORBIT</text>'
    return start + art + '</svg>'

def header(s, mode, prefix='../'):
    photos_link = '<a href="index.html#photos">Gallery</a>' if s['theme']=='birdy' else ''
    preview = f'<div class="preview">DESIGN REVIEW · No live booking, payments, or data capture · <a href="{prefix}review.html">All domain previews ↗</a></div>' if mode=='preview' else ''
    return preview + f'<a class="skip" href="#main">Skip to content</a><header><div class="shell nav"><a class="brand" href="index.html"><span class="brandmark" aria-hidden="true">{MARKS[s["theme"]]}</span>{esc(s["brand"])}</a><nav class="navlinks" aria-label="Main navigation"><a href="#explore">Explore</a>{photos_link}<a href="#how">The approach</a><a href="#questions">Questions</a></nav><a class="navend" href="#contact">{("Review the concept" if mode=="preview" else "Get in touch")} ↗</a></div></header>'

def asset_name(s,name):
    if s['theme']!='birdy': return name
    path=ROOT/'assets'/name
    return path.stem+'-'+hashlib.sha256(path.read_bytes()).hexdigest()[:12]+path.suffix

def document(s, content, mode, title=None, prefix='../', extra_class=''):
    title = title or s['brand']+' — '+s.get('eyebrow','Concept preview').title()
    robots = '<meta name="robots" content="noindex,nofollow">' if mode=='preview' or s['theme'] in ('heart','studio') else ''
    canonical = '' if mode=='preview' else f'<link rel="canonical" href="https://{s["domain"]}/">'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="{POLICY}"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="description" content="{esc(s.get('lede',s.get('text','')),quote=True)}">{robots}{canonical}<meta property="og:title" content="{esc(title,quote=True)}"><meta property="og:type" content="website"><title>{esc(title)}</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/{asset_name(s,'site.css')}"></head>
<body class="{s['theme']} {extra_class}">{header(s,mode,prefix)}{content}<footer class="shell footer"><div class="footerline"><strong>{esc(s['brand'])}</strong><nav class="footlinks" aria-label="Footer"><a href="privacy.html">Privacy & terms</a><a href="#contact">Contact</a><a href="https://github.com/jordanistan">GitHub ↗</a></nav></div><p>© 2026 Jordan Robison · {esc(s.get('stage','Supporting domain concept'))}. No claimed testimonials, certification, sales, or customer counts.</p></footer><script src="assets/{asset_name(s,'site.js')}" defer></script></body></html>'''

def offer_cards(s,mode):
    out=[]
    for i,item in enumerate(s['offers']):
      d=item if isinstance(item,dict) else dict(zip(('name','label','text'),item))
      price=f'<div class="price">{esc(d["price"])}</div><div class="micro">Draft pricing · final quote by agreement</div>' if d.get('price') else ''
      out.append(f'<article class="card"'+(f' data-category="{["parks","patios","travel"][i]}"' if s['theme']=='fido' else '')+f'><span class="serial">0{i+1} / {esc(s["brand"].upper())}</span><p class="label">{esc(d["label"])}</p><h3>{esc(d["name"])}</h3><p>{esc(d["text"])}</p>{price}</article>')
    return ''.join(out)

LABS={
 'linux': ('Independent Linux Lab','Inventory before change', ['Identify the Linux distribution and version in a test machine you own.','List running services and identify why each is needed. Do not stop unfamiliar services without checking their role.','Record which ports are listening and how you intend to restrict access.','Review how updates are applied and where the last successful backup lives.','Write a summary of what you observed, one thing to investigate, and a reversible next step.']),
 'infrastructure': ('Infrastructure Learning Lab','Draw the system, then test the restore', ['Choose a small non-production system or a disposable lab.','List its components, data stores, dependencies, owners, and trust boundaries.','Document how configuration and secrets are managed; never include real values in the notes.','Restore synthetic data into an isolated environment. Record whether the result meets your expected outcome.','Record the setup, observations, rollback steps, and unresolved questions.']),
 'ai': ('Intelligent Learning Lab','Evaluate a workflow before connecting it', ['Choose one repetitive task with a measurable output.','Define inputs using synthetic examples, and identify data that must remain private.','Record what the automation may suggest and what requires a human decision.','Test normal input, missing information, incorrect output, and an explicit stop request.','Keep a decision log. Do not give a prototype production access until permissions, error handling, and ownership are settled.'])
}

def extra(s,mode):
    t=s['theme']
    if t=='paws':
      return '<section class="section"><div class="tool tool-grid" data-walk-calculator><div><p class="kicker">PLAN A ROUTINE</p><h3>A simple weekly estimate.</h3><div class="field"><label for="walk-duration">Walk length</label><select id="walk-duration"><option value="30">30 minutes · $22</option><option value="60">60 minutes · $35</option></select></div><div class="field"><label for="walk-count">Walks per week</label><select id="walk-count">'+''.join(f'<option value="{i}">{i}</option>' for i in range(1,6))+'</select></div></div><div class="result" aria-live="polite"><strong data-total>$22 / week</strong><p data-estimate>1 × 30-minute walk at $22 per walk. Planning estimate only; no package discount or booking implied.</p><p>Travel, additional pets, holidays, and special care are discussed separately. No reservation is made here.</p></div></div></section>'
    if t=='lab':
      return '<section class="section"><p class="kicker">STARTER FIELD NOTES / FREE</p><h2>Leave the lab with something useful.</h2>'+''.join(f'<a class="download" href="labs/{key}.html"><div><strong>{esc(title)}</strong><span>{esc(sub)} · 5-step starter exercise</span></div><b aria-hidden="true">↗</b></a>' for key,(title,sub,_) in LABS.items())+'<a class="download" href="https://github.com/jordanistan/illnetwork"><div><strong>Illnet Rx source & setup</strong><span>Existing local-first Linux scanner · Read the repository instructions</span></div><b aria-hidden="true">↗</b></a></section>'
    if t=='jordan':
      return '<section class="section projects"><p class="kicker">PUBLIC WORK</p><h2>Projects you can inspect.</h2>'+''.join(f'<a class="project-row" href="{url}"><strong>{name}</strong><p>{txt}</p><span aria-hidden="true">↗</span></a>' for name,txt,url in [('SpaceGhostKilla','Security research, a free audit preview, and scoped consulting.','https://github.com/jordanistan/spaceghostkilla'),('ILL Network','Local-first Linux tooling and three learning tracks.','https://github.com/jordanistan/illnetwork'),('Domain studio','Dependency-free sites, secure builds, and documented handoffs.','https://github.com/jordanistan/illnetwork/tree/main/portfolio')])+'</section>'
    if t=='birdy':
      return render_gallery(json.loads((ROOT/'birdy-gallery.json').read_text()))
    if t=='ai':
      return '<section class="section"><div class="tool tool-grid" data-workflow><div><p class="kicker">WORKFLOW STARTER</p><h3>Pick one thing to simplify.</h3><div class="field"><label for="workflow">Process</label><select id="workflow"><option value="leads">Lead intake & drafts</option><option value="reports">Report preparation</option><option value="scheduling">Scheduling suggestions</option><option value="bookkeeping">Bookkeeping categories</option></select></div><p class="micro">A planning prompt, not an AI agent. No data leaves the page.</p></div><div class="result" aria-live="polite"><p data-workflow-output>Start with a lead intake checklist. Keep outreach drafts for human review; do not auto-send messages.</p></div></div></section>'
    if t in ('hearty','heart'):
      labels=['The routine I choose','When I want to make space for it','What helped or got in the way'] if t=='hearty' else ['Questions I want to ask','Reminders for the visit','Notes from the conversation']
      return '<section class="section"><div class="tool"><p class="kicker">A PRINTABLE STARTER</p><h3>'+('My everyday planner' if t=='hearty' else 'My visit-preparation worksheet')+'</h3><p class="micro">This site does not transmit or store these notes. Your browser may retain field values. Clear the worksheet when finished; use your own device and keep printed copies private.</p><div class="worksheet">'+''.join(f'<div class="field"><label for="note{i}">{esc(label)}</label><textarea id="note{i}" maxlength="1500" autocomplete="off"></textarea></div>' for i,label in enumerate(labels))+'<button class="button" data-print type="button">Print my worksheet ↗</button><button class="button secondary" data-clear-worksheet type="button">Clear worksheet</button><p class="micro" data-clear-status role="status"></p></div></div></section>'
    if t=='studio':
      return '<section class="section"><p class="kicker">ORIGINAL VECTOR STUDIES / CONCEPT WORK</p><h2>Between light and space.</h2><div class="gallery">'+''.join(f'<figure><img src="assets/study-{i}.svg" alt="Original geometric space-inspired artwork, study {i}" loading="lazy"><figcaption>0{i} / {name} · Vector concept · Not a product listing</figcaption></figure>' for i,name in enumerate(['Orbit','Signal','Horizon'],1))+'</div></section>'
    if t=='ghost':
      return '<section class="section"><div class="tool"><p class="kicker">EXISTING PROJECT / FREE PREVIEW</p><h3>Start with the Cloud Security Quick Audit.</h3><p>The existing research website and free Quick Audit stay intact. The Field Manual and KubeScan remain unreleased; this concept does not enable their checkout.</p><a class="button secondary" href="https://github.com/jordanistan/spaceghostkilla">Explore the security source ↗</a></div></section>'
    return ''

def contact(s,mode):
    if mode=='production':
      email=s.get('email',CONFIG['contact']); href='mailto:'+email+'?'+urlencode({'subject':s['subject']})
      action=f'<a class="button" href="{esc(href,quote=True)}">{esc(s["cta"])} <span aria-hidden="true">↗</span></a><p class="micro">Opens your email app. Nothing is submitted by this website. You must send your message; a reply is required to confirm any service.</p><p><a href="mailto:{esc(email)}">{esc(email)}</a></p>'
    else:
      action='<p><strong>Design review only</strong></p><p>Live inquiries, appointments, purchases, and subscriptions are not enabled in this preview.</p><a class="button" href="#explore">Explore the concept ↗</a>'
    return f'<section class="contact" id="contact"><div><p class="kicker">THE NEXT STEP</p><h2>{esc(s["contact_title"])}</h2><p>{esc(s["contact_text"])}</p></div><div>{action}</div></section>'

def birdy_page(s,mode):
    media=json.loads((ROOT/'birdy-gallery.json').read_text())
    first=media[0]
    intro=('<section class="section birdy-story" id="explore"><div><p class="kicker">MEET YOUR CO-PILOT</p><h2>A pink collar.<br>A world to explore.</h2></div><div><p class="lede">'+esc(s['intro'])+'</p><p>Some photos are about a place. Others are about the company you keep. This journal makes room for both: the destination, the small discoveries, and Birdy right in the middle of it all.</p><a class="story-link" href="#photos">Start with the photo deck ↓</a></div></section>')
    notes=('<section class="section" id="how"><p class="kicker">BEHIND THE PHOTOS</p><h2>More than a postcard.</h2><div class="cards"><article class="card"><span class="serial">01 / THE PLACE</span><h3>Where did we go?</h3><p>A name, a setting, and the details that make each place memorable. The photo is the beginning of the story.</p></article><article class="card"><span class="serial">02 / THE MOMENT</span><h3>What caught Birdy’s attention?</h3><p>The little things deserve a place in the journal, too. A good stop, an unexpected discovery, or simply a photo worth keeping.</p></article><article class="card"><span class="serial">03 / THE FIELD NOTES</span><h3>Would we bring a dog again?</h3><p>When there’s a useful detail to share, we’ll include it with the story: access, shade, water, and what made the outing work.</p></article></div></section>')
    faq='<section class="section faq" id="questions"><div><p class="kicker">GET TO KNOW BIRDY</p><h2>A few things<br>you might wonder.</h2></div><div>'+''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q,a in s['faqs'])+'</div></section>'
    body=f'<main tabindex="-1" id="main" class="shell"><section class="hero birdy-hero"><div><p class="kicker">{esc(s["eyebrow"])}</p><h1>{"<br>".join(esc(s["headline"]).splitlines())}</h1><p class="lede">{esc(s["lede"])}</p><div class="actions"><a class="button" href="#photos">Explore Birdy’s gallery ↓</a><a class="button secondary" href="#explore">Meet the co-pilot</a></div><p class="micro">{esc(s["note"])}</p></div><figure class="birdy-portrait"><img src="{esc(first["src"])}" alt="{esc(first["alt"])}" width="1600" height="1205" fetchpriority="high"><figcaption>Birdy / always good company.</figcaption></figure></section><div class="ribbon"><b>I AM BIRDY</b><span>Places. Moments. Field notes.</span><span>WITH JORDAN ↗</span></div>'+intro+render_gallery(media)+notes+faq+contact(s,mode)+'</main>'
    html=document(s,body,mode)
    html=html.replace('>Explore</a>', '>Our story</a>').replace('>The approach</a>', '>Travel notes</a>').replace('>Questions</a>', '>About Birdy</a>')
    html=html.replace('Pet &amp; travel journal. No claimed testimonials, certification, sales, or customer counts.', 'A life in photos.')
    html=html.replace('Birdy &amp; Jordan’s photo journal. No claimed testimonials, certification, sales, or customer counts.', 'Birdy &amp; Jordan’s photo journal.')
    return html

def page(s,mode):
    if s['theme']=='birdy': return birdy_page(s,mode)
    filterbar = '<div class="filterbar" data-filters role="group" aria-label="Outing categories">'+''.join(f'<button type="button" data-filter="{key}" aria-pressed="{str(key=="all").lower()}">{name}</button>' for key,name in [('all','All ideas'),('parks','Parks'),('patios','Patios'),('travel','Travel')])+'</div><p class="micro" data-filter-count aria-live="polite">3 planning categories shown. These are not venue listings.</p>' if s['theme']=='fido' else ''
    body=f'''<main tabindex="-1" id="main" class="shell"><section class="hero"><div><p class="kicker">{esc(s['eyebrow'])}</p><h1>{'<br>'.join(esc(s['headline']).splitlines())}</h1><p class="lede">{esc(s['lede'])}</p><div class="actions"><a class="button" href="{'#explore' if s['theme']=='lab' else '#contact'}">{esc(s['cta'])} <span aria-hidden="true">↗</span></a><a class="button secondary" href="#explore">Take a look ↓</a></div><p class="micro">{esc(s['note'])}</p></div><div class="hero-art"><img src="assets/hero.svg" alt="" width="500" height="500"><div class="artcaption"><span>{esc(s['brand'])}</span><span>EDITION / 01</span></div></div></section><div class="ribbon"><b>{esc(s['domain'])}</b><span>{esc(s['stage'])}</span><span>BUILT WITH CARE ↗</span></div><section class="section" id="explore"><div class="section-head"><div><p class="kicker">THE IDEA / IN PRACTICE</p><h2>{esc(s['section'])}</h2></div><p>{esc(s['intro'])}</p></div>{filterbar}<div class="cards">{offer_cards(s,mode)}</div></section>{extra(s,mode)}<section class="section" id="how"><p class="kicker">A SIMPLE APPROACH</p><h2>Start small. Make it useful.</h2><div class="steps">'''
    body+=''.join(f'<article class="step"><div class="number">0{i}</div><h3>{esc(a)}</h3><p>{esc(b)}</p></article>' for i,(a,b) in enumerate(s['steps'],1))
    body+='</div></section><section class="section faq" id="questions"><div><p class="kicker">A FEW GOOD QUESTIONS</p><h2>Before you begin.</h2></div><div>'+''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q,a in s['faqs'])+'</div></section>'+contact(s,mode)+'</main>'
    return document(s,body,mode)

def alias_page(s,mode):
    target='../'+s['primary']+'/index.html' if mode=='preview' else 'https://'+s['primary']+'/'
    content=f'<main tabindex="-1" id="main" class="shell"><section class="hero" id="explore"><div><p class="kicker">A SUPPORTING DOMAIN</p><h1>{"<br>".join(esc(s["headline"]).splitlines())}</h1><p class="lede">{esc(s["text"])}</p><a class="button" href="{target}">Visit {esc(s["primary"])} ↗</a></div><div class="hero-art"><img src="assets/hero.svg" alt="" width="500" height="500"></div></section><section class="section" id="how"><h2>One project, a clear home.</h2><p>This address supports the main brand. Its current work and release status live on the primary site.</p></section><section class="section" id="questions"><h3>Are products available here?</h3><p>No orders, bookings, or subscriptions are taken on this supporting page.</p></section><section class="section" id="contact"><a href="{target}">Find the primary project ↗</a></section></main>'
    return document(s,content,mode,extra_class='alias')

def privacy(s,mode):
    text=f'''<main tabindex=\"-1\" class="shell" id="main"><article class="legal"><p class="kicker">PRIVACY / TERMS / PROJECT STATUS</p><h1>A clear starting point.</h1><p>Last updated October 4, 2026. Operator: Jordan Robison. Site: {esc(s['domain'])}.</p><h2 id="explore">What this page does</h2><p>{'This is a design and educational preview. It takes no bookings, orders, subscriptions, or inquiries.' if mode=='preview' else 'This static site introduces a project. Any available email link opens your own email app; no message is sent automatically. Services require a separate written agreement.'}</p><h2 id="how">Information & privacy</h2><p>This build has no analytics scripts, advertising cookies, account creation, uploads, or server forms. The site does not transmit or store worksheet notes, but your browser may retain field values. Clear the worksheet when finished. Your hosting provider may process technical access information under its own privacy policy. Print only on a device and printer you trust.</p><p>If you choose to send email outside this preview, your email provider and the recipient process that message. Include only details needed for the inquiry. Never send access codes, payment-card data, API keys, or medical records.</p><h2 id="questions">Quotes, products & cancellations</h2><p>Shown prices are draft estimates. No purchase or recurring commitment is created by visiting this page. Final scope, fees, cancellation rules, refunds, delivery dates, and any applicable taxes are confirmed before accepting a paid engagement. Products labeled planned or unreleased cannot be purchased here.</p><h2>Specific project limitations</h2><p>{esc(s.get('stage','Supporting address'))}. No fabricated customer reviews, success claims, or professional accreditation are implied. Health projects are educational and do not provide clinical care. Starfield is a concept pending brand clearance. Dog-care bookings require verified operating readiness.</p><h2 id="contact">Contact</h2><p>{'Contact capture is disabled in design review mode. Return to the project concept below.' if mode=='preview' else 'Use the project’s contact link for questions or privacy requests. Do not include sensitive data.'}</p><a class="button secondary" href="index.html#contact">Back to the project ↗</a></article></main>'''
    return document(s,text,mode,title=s['brand']+' / Privacy & terms')

def write_site(s,path,mode):
    path.mkdir(parents=True,exist_ok=True); (path/'assets').mkdir(exist_ok=True)
    for name in ['site.css','site.js']: shutil.copyfile(ROOT/'assets'/name,path/'assets'/asset_name(s,name))
    (path/'assets'/'hero.svg').write_text(svg_art(s['theme']))
    (path/'assets'/'favicon.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="10" fill="#183c2b"/><text x="24" y="33" text-anchor="middle" font-family="monospace" font-size="25" fill="#f7f4e8">{esc(MARKS[s["theme"]])}</text></svg>')
    (path/'index.html').write_text(alias_page(s,mode) if 'primary' in s else page(s,mode))
    (path/'privacy.html').write_text(privacy(s,mode)); (path/'.nojekyll').touch()
    (path/'_headers').write_text(HEADERS)
    (path/'robots.txt').write_text('User-agent: *\nDisallow: /\n' if mode=='preview' or s['theme'] in ('heart','studio') else 'User-agent: *\nAllow: /\nSitemap: https://'+s['domain']+'/sitemap.xml\n')
    (path/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://'+s['domain']+'/</loc></url></urlset>')
    if s['theme']=='birdy':
      for item in json.loads((ROOT/'birdy-gallery.json').read_text()):
        if item['src'].startswith('assets/birdy/'):
          target=path/item['src']; target.parent.mkdir(parents=True,exist_ok=True)
          shutil.copyfile(ROOT/item['src'],target)
    if s['theme']=='studio':
      for i,t in enumerate(['studio','ai','ghost'],1): (path/'assets'/f'study-{i}.svg').write_text(svg_art(t))
    if s['theme']=='lab' and 'primary' not in s:
      (path/'labs').mkdir(exist_ok=True)
      for key,(title,sub,items) in LABS.items():
        txt=f'{title}\n{sub}\n\n'+'\n'.join(f'{i}. {item}' for i,item in enumerate(items,1))+'\n\nRecord: setup / observations / outcome / next step. Never include credentials.\n'
        (path/'labs'/f'{key}.txt').write_text(txt)
        body=f'<main tabindex="-1" id="main" class="shell"><article class="labcontent"><p class="kicker" id="explore">FREE STARTER / {esc(title)}</p><h1>{esc(sub)}</h1><p class="notice">Use a system you own or a disposable lab. This is a starter exercise, not an automated scanner or a production-hardening recipe.</p><ol id="how">'+''.join(f'<li>{esc(item)}</li>' for item in items)+f'</ol><h3 id="questions">What did you learn?</h3><p>Record the setup, observations, outcome, limitations, and next step. Keep secrets and private logs out of GitHub.</p><a class="button" href="{key}.txt" download>Download the field note ↗</a><p id="contact"><a href="../index.html">Back to the lab</a></p></article></main>'
        html=document(s,body,mode,title=title+' / '+sub,prefix='../../')
        html=html.replace('href="assets/','href="../assets/').replace('src="assets/','src="../assets/').replace('href="privacy.html"','href="../privacy.html"').replace('href="index.html"','href="../index.html"')
        (path/'labs'/f'{key}.html').write_text(html)

def build(mode,out,domain):
    if out.exists() and any(out.iterdir()): raise SystemExit('Output must be empty; refusing to overwrite an existing directory.')
    out.mkdir(parents=True,exist_ok=True)
    sites=CONFIG['sites']+CONFIG['aliases']
    if domain:
      matches=[s for s in sites if s['domain']==domain]
      if not matches: raise SystemExit('Unknown or excluded domain')
      write_site(matches[0],out,mode)
      if mode=='preview':
        for p in out.rglob('*.html'):
          p.write_text(p.read_text().replace('../review.html','index.html'))
      return
    for s in sites: write_site(s,out/s['domain'],mode)
    primary=next(s for s in CONFIG['sites'] if s['domain']=='ill.network')
    # The root is the educational ILL lab. All domain previews are in /review.html.
    write_site(primary,out,mode)
    root=(out/'index.html').read_text().replace('../review.html','review.html'); (out/'index.html').write_text(root)
    review='<main tabindex="-1" id="main" class="shell"><section class="section" id="explore"><p class="kicker">DOMAIN STUDIO / OCTOBER 2026</p><h1>Fourteen addresses.\nOne starting point.</h1><p>Educational design previews for the active portfolio. No transactions or data capture. The SXSW and four soccer domains are deliberately excluded.</p><div class="catalog" id="how">'+''.join(f'<a class="card" href="{s["domain"]}/index.html"><p class="kicker">{esc(s["theme"])}</p><h3>{esc(s["brand"])}</h3><p>{esc(s["domain"])}</p><span>Open design preview ↗</span></a>' for s in sites)+'</div><p id="questions">Every preview uses relative assets and has a separate production export. Source and launch instructions are in the repository.</p><p id="contact"><a href="https://github.com/jordanistan/illnetwork/tree/main/portfolio">Inspect the source ↗</a></p></section></main>'
    (out/'review.html').write_text(document(primary,review,mode,title='Domain studio / All previews',prefix=''))
    (out/'privacy.html').write_text((out/'privacy.html').read_text().replace('../review.html','review.html'))
    (out/'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    for p in (out/'labs').glob('*.html'): p.write_text(p.read_text().replace('../../review.html','../review.html'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--mode',choices=['preview','production'],default='preview'); parser.add_argument('--output',required=True); parser.add_argument('--domain'); args=parser.parse_args()
    output=Path(args.output).resolve()
    if output==ROOT or ROOT.is_relative_to(output): raise SystemExit('Unsafe output directory')
    build(args.mode,output,args.domain)
    print(f'Built {args.domain or "14-domain portfolio"} in {args.mode} mode: {output}')
