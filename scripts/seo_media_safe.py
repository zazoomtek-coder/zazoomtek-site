"""Conservative SEO video detection; no video API calls or page mutation.

Only literal, visible YouTube iframe tags under a <main> element may receive
VideoObject, and only with title and upload date already published in
home-video-feed.json. Script-created, side-rail and related-link videos are ignored.
"""
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
import json
import re
from urllib.parse import urlsplit

YT_EMBED = re.compile(r'^https://(?:www\.)?(?:youtube\.com|youtube-nocookie\.com)/embed/([A-Za-z0-9_-]{11})(?:[/?#]|$)', re.I)
YT_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')

class VisibleVideoParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = 0
        self.iframe_ids = []
        self.embedded_videos = 0

    def handle_starttag(self, tag, attributes):
        attrs = {k.lower(): (v or '') for k, v in attributes if k}
        if tag.lower() == 'main':
            self.in_main += 1
        if not self.in_main:
            return
        if 'hidden' in attrs or attrs.get('aria-hidden', '').lower() == 'true':
            return
        if re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', attrs.get('style', ''), re.I):
            return
        if tag.lower() == 'iframe':
            m = YT_EMBED.match(attrs.get('src', ''))
            if m:
                self.iframe_ids.append(m.group(1))
        elif tag.lower() == 'video':
            self.embedded_videos += 1

    def handle_endtag(self, tag):
        if tag.lower() == 'main' and self.in_main > 0:
            self.in_main -= 1

def feed_videos(root):
    path = Path(root) / 'home-video-feed.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, list):
        return {}
    out = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        video_id = item.get('id')
        published = item.get('publishedAt', '')
        title = item.get('title', '')
        if not isinstance(video_id, str) or not YT_ID.fullmatch(video_id):
            continue
        if not isinstance(title, str) or len(title.strip()) < 4 or len(title) > 230:
            continue
        if not isinstance(published, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', published):
            continue
        try:
            date = datetime.fromisoformat(published.replace('Z', '+00:00'))
        except ValueError:
            continue
        if date.tzinfo is None:
            continue
        out[video_id] = {'name': title.strip(), 'uploadDate': published}
    return out

def verified_video(source, known_videos):
    parser = VisibleVideoParser()
    # HTMLParser does not treat JS string literals as real HTML tags.
    parser.feed(source)
    if len(parser.iframe_ids) != 1:
        return None
    video_id = parser.iframe_ids[0]
    if video_id not in known_videos:
        return None
    found = known_videos[video_id]
    return {
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        'name': found['name'],
        'uploadDate': found['uploadDate'],
        'thumbnailUrl': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
        'embedUrl': f'https://www.youtube.com/embed/{video_id}',
    }


class PrimaryArticleImage(HTMLParser):
    """Read only the first descriptive image within a primary editorial article."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.article_depth = 0
        self.src = None
        self.alt = ''

    def handle_starttag(self, tag, attrs):
        data = {k.lower(): (v or '') for k, v in attrs if k}
        if tag.lower() == 'article':
            css = data.get('class', '').lower().split()
            if self.article_depth or 'article-main' in css:
                self.article_depth += 1
        if tag.lower() != 'img' or not self.article_depth or self.src is not None:
            return
        src = data.get('src', '').strip()
        alt = data.get('alt', '').strip()
        if len(alt) < 15 or not src:
            return
        if any(x in src.lower() for x in ('chatgpt.png','icons8.com','youtube-play','favicon','logo.')):
            return
        if src.startswith('/'):
            src = 'https://zazoomtek.it' + src
        elif not src.startswith('https://'):
            return
        u = urlsplit(src)
        if not u.netloc or not u.path or u.path.lower().endswith('.svg'):
            return
        self.src = src
        self.alt = alt

    def handle_endtag(self, tag):
        if tag.lower() == 'article' and self.article_depth:
            self.article_depth -= 1

def primary_article_image(source):
    parser = PrimaryArticleImage()
    parser.feed(source)
    return parser.src
