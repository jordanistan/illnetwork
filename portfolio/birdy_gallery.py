"""Render the photo deck at build time; no browser API or album credentials."""
from html import escape
import re

ORIGINAL = 'https://raw.githubusercontent.com/jordanistan/iambirdy/main/iambirdy.jpg'
ALBUM = 'https://photos.app.goo.gl/hmzCdVn8bEniivNn8'

def render_gallery(photos):
    if not photos:
        raise ValueError('The gallery needs at least one real photo')
    slides = []
    for i, photo in enumerate(photos, 1):
        src = photo['src']
        local = re.fullmatch(r'(?:assets/birdy|site-assets/gallery)/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:jpg|jpeg|png|webp)', src, re.I)
        if src not in (ORIGINAL, 'iambirdy.jpg') and not local:
            raise ValueError('Use a checked-in photo path, not a temporary album URL')
        if not photo.get('alt', '').strip():
            raise ValueError('Every photo needs descriptive alternative text')
        src, alt, caption = map(escape, (src, photo['alt'], photo['caption']))
        slides.append(f'<figure class="photo-slide" role="group" aria-roledescription="slide" aria-label="Photo {i} of {len(photos)}"><img src="{src}" alt="{alt}" loading="lazy" decoding="async"><figcaption><span>{caption}</span><a href="{src}" target="_blank" rel="noopener noreferrer">View full photo ↗</a></figcaption></figure>')
    return ('<section class="section" id="photos" aria-labelledby="photos-heading">'
            '<p class="kicker">THE ORIGINAL CO-PILOT / PHOTO DECK</p>'
            '<h2 id="photos-heading">Life with Birdy.</h2>'
            '<p class="micro" id="photo-deck-help">Swipe or scroll sideways through the photos. Use the arrow keys when the deck is focused.</p>'
            '<div class="photo-deck" data-photo-deck role="region" aria-roledescription="carousel" aria-label="Birdy photo gallery">'
            '<div class="photo-track" id="birdy-photo-track" tabindex="0" aria-label="Scrollable photos" aria-describedby="photo-deck-help">'
            + ''.join(slides) + '</div><div class="photo-deck-controls" data-deck-controls hidden>'
            '<button class="button secondary" type="button" data-deck-prev aria-controls="birdy-photo-track" aria-label="Previous photo">← Previous</button>'
            f'<p class="micro" data-deck-status role="status" aria-live="polite" aria-atomic="true">Photo 1 of {len(photos)}</p>'
            '<button class="button secondary" type="button" data-deck-next aria-controls="birdy-photo-track" aria-label="Next photo">Next →</button></div></div>'
            f'<div class="actions"><a class="button secondary" href="{ALBUM}" target="_blank" rel="noopener noreferrer">Open Birdy’s Google Photos album ↗</a></div>'
            '<p class="micro">Original photos from Birdy’s site. The hero illustration is a stylized mascot.</p></section>')
