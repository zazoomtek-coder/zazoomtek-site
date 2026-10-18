#!/usr/bin/env python3
"""Regression checks: Community prefixes route content but never appear on-site."""
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
spec = importlib.util.spec_from_file_location(
    "zt_community_routing_under_test",
    Path(__file__).with_name("update-youtube-posts.py"),
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def post(pid, text):
    return {
        "id": pid,
        "text": text,
        "image": "/ChatGPT.png",
        "published": "15 ottobre 2026",
        "published_iso": "2026-10-15T08:00:00Z",
    }

tech = post("TechExample", "News Tech: Nuovo smartphone con chip IA\n\nHardware e software al centro della notizia.")
gaming = post("GamingExample", "News Gaming: Nuovo DLC per il videogioco\n\nUna stagione porta missioni extra.")
extra = post("ExtraExample", "News Extra: Festival del cibo e della cultura\n\nIl nuovo evento racconta tradizioni e gastronomia.")
extra_standalone = post("ExtraNextLine", "News Extra\nFestival dello sport e dei giocattoli\n\nArrivano nuovi eventi di quartiere.")
cross_topic_extra = post("ExtraMentioningGaming", "News Extra: Festa dello sport con tornei di videogiochi\n\nL'evento è una festa generale, non una novità software.")
legacy = post("LegacyExample", "News: Notizie dalla redazione\n\nUn approfondimento generale.")
review = post("ReviewExample", "Review\nPoly Fighter | Recensione PC\n\nGameplay\n\nUna recensione con analisi delle meccaniche.")

for item, expected in [
    (tech, "tech"), (gaming, "gaming"), (extra, "extra"),
    (extra_standalone, "extra"), (cross_topic_extra, "extra"),
    (legacy, "news"), (review, "review"),
]:
    assert module.post_category(item) == expected, (expected, item["text"])
    assert module.is_review(item) == (expected == "review"), item["text"]

assert module.special_community_section(post(
    "UgkxSpecialTech", "News Tech Impact: Videogiochi e terapia nel percorso clinico"
)) == "tech-impact"
assert module.special_community_section(post(
    "UgkxSpecialGaming", "News Gaming Inside: Norme UE sul gaming e tutela dei giocatori"
)) == "gaming-inside"
assert module.news_title(extra) == "Festival del cibo e della cultura"
assert module.news_title(extra_standalone) == "Festival dello sport e dei giocattoli"
assert module.news_title(tech) == "Nuovo smartphone con chip IA"
assert module.news_title(gaming) == "Nuovo DLC per il videogioco"
assert module.review_title(review) == "Poly Fighter | Recensione PC"
assert "News Extra" not in module.news_body_html(extra)
assert "News Extra" not in module.news_body_html(extra_standalone)
assert "News Extra" not in module.post_excerpt(extra)
assert "News Gaming" not in module.post_excerpt(gaming)

feed = module.render_article_feed([extra, gaming, tech, cross_topic_extra])
assert feed.count('class="article-row"') == 2, "Extra leaked into Tech/Gaming Home feed"
assert "Festival del cibo" not in feed
assert "Festa dello sport" not in feed
assert 'data-post-category="tech"' in feed
assert 'data-post-category="gaming"' in feed

ticker = module.render_ticker([extra, gaming, tech, cross_topic_extra])
assert "Festival" not in ticker and "Festa dello sport" not in ticker
assert "Nuovo DLC" in ticker and "Nuovo smartphone" in ticker

source = Path(__file__).with_name("update-youtube-posts.py").read_text(encoding="utf-8")
assert "write_news_archive(general_news,reviews)" in source
assert "write_extra_archive(news,reviews)" in source
assert 'if post_category(p)=="extra":' in source
assert "write_article_pages(general_news)" in source

print("PASS: News Tech, News Gaming and Review route correctly.")
print("PASS: News Extra is shown only in the Extra archive and never in Tech/Gaming.")
print("PASS: Editorial category prefixes are absent from visible titles and body copy.")
