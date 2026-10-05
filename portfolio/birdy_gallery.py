"""Render the media deck at build time; no browser API or album credentials."""
from html import escape
import re

ORIGINAL = 'https://raw.githubusercontent.com/jordanistan/iambirdy/main/iambirdy.jpg'
ALBUM = 'https://photos.app.goo.gl/hmzCdVn8bEniivNn8'

def render_gallery(media):
    if not media:
        raise ValueError('The gallery needs at least one real photo or video')
    slides = []
    total = len(media)
    for i, item in enumerate(media, 1):
        src = item['src']
        kind = item.get('type', 'image')
        extension = r'(?:jpg|jpeg|png|webp)' if kind == 'image' else r'(?:mp4|webm)'
        local = re.fullmatch(rf'(?:assets/birdy|site-assets/gallery)/[A-Za-z0-9][A-Za-z0-9._-]*\.{extension}', src, re.I)
        original_image = kind == 'image' and src in (ORIGINAL, 'iambirdy.jpg')
        if not original_image and not local:
            raise ValueError('Use a checked-in media path, not a temporary album URL')
        if kind not in ('image', 'video'):
            raise ValueError('Gallery type must be image or video')
        if not item.get('alt', '').strip():
            raise ValueError('Every gallery item needs accessible text')
        src, alt, caption = map(escape, (src, item['alt'], item['caption']))
        if kind == 'image':
            visual = f'<img src="{src}" alt="{alt}" loading="lazy" decoding="async">'
            action = 'View photo'
        else:
            visual = (f'<video controls preload="none" aria-label="{alt}">'
                      f'<source src="{src}" type="video/mp4">'
                      'Your browser does not support embedded video.</video>')
            action = 'Open video'
        slides.append(f'<figure class="photo-slide" role="group" aria-roledescription="slide" aria-label="Gallery item {i} of {total}">{visual}<figcaption><span>{caption}</span><a href="{src}" target="_blank" rel="noopener noreferrer">{action} ↗</a></figcaption></figure>')
    return ('<section class="section" id="photos" aria-labelledby="photos-heading">'
            '<p class="kicker">THE ORIGINAL CO-PILOT / MEDIA DECK</p>'
            '<h2 id="photos-heading">Life with Birdy.</h2>'
            '<p class="micro" id="photo-deck-help">Swipe or scroll sideways through the photos and videos. Use the arrow keys when the deck is focused.</p>'
            '<div class="photo-deck" data-photo-deck role="region" aria-roledescription="carousel" aria-label="Birdy photo and video gallery">'
            '<div class="photo-track" id="birdy-photo-track" tabindex="0" aria-label="Scrollable photos and videos" aria-describedby="photo-deck-help">'
            + ''.join(slides) + '</div><div class="photo-deck-controls" data-deck-controls hidden>'
            '<button class="button secondary" type="button" data-deck-prev aria-controls="birdy-photo-track" aria-label="Previous gallery item">← Previous</button>'
            f'<p class="micro" data-deck-status role="status" aria-live="polite" aria-atomic="true">Item 1 of {total}</p>'
            '<button class="button secondary" type="button" data-deck-next aria-controls="birdy-photo-track" aria-label="Next gallery item">Next →</button></div></div>'
            f'<div class="actions"><a class="button secondary" href="{ALBUM}" target="_blank" rel="noopener noreferrer">Open Birdy’s Google Photos album ↗</a></div>'
            '<p class="micro">Birdy’s photo journal. Public copies are optimized for the web and stripped of embedded metadata.</p></section>')
