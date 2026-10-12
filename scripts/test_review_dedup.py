#!/usr/bin/env python3
"""Offline regression tests for written-review anti-duplicate rules."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
spec=importlib.util.spec_from_file_location(
    "youtube_posts_for_tests",Path(__file__).with_name("update-youtube-posts.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def post(pid,title):
    return {"id":pid,"text":"Review\n\n"+title+"\n\nIntroduzione\n\nTesto recensione.\n\n"
            "Gameplay\n\nDettagli.\n\nConclusioni\n\nRisultato.\n\nVoto finale: 8/10",
            "published":"12 ottobre 2026"}


def run():
    assert module.review_identity(
        "Sesame Street: Amici e risate Recensione PS5 | Avventura in famiglia"
    )=="sesame street amici e risate"
    assert module.review_identity(
        "Review | Sesame Street: Amici e risate Recensione PS5"
    )=="sesame street amici e risate"
    assert module.review_identity("WALTO Recensione PC")=="walto"
    assert module.review_identity("NBA 2K27 | Recensione PS5")=="nba 2k27"
    assert module.review_identity("NBA 2K28 | Recensione PS5")!="nba 2k27"
    assert not module.same_review(
        {"key":"walto","platform":"pc"},{"key":"walto","platform":"ps5"})

    with tempfile.TemporaryDirectory() as d:
        previous=os.getcwd()
        try:
            os.chdir(d)
            Path("sesame-street-amici-e-risate-recensione-ps5.html").write_text(
                '<html><head><meta name="robots" content="index,follow">'
                '<meta name="description" content="Una recensione editoriale."></head>'
                '<body><h1>Sesame Street: Amici e risate Recensione PS5'
                ' | Un quartiere colorato</h1><img class="hero" src="/cover.webp">'
                '</body></html>',encoding="utf-8")
            Path("recensione-UgkxOldTransport.html").write_text(
                '<html><head><meta name="robots" content="index,follow"></head>'
                '<body><h1>Transport Fever 3 | Recensione PS5</h1></body></html>',
                encoding="utf-8")
            Path("nba-2k27-recensione-ps5.html").write_text(
                '<html><head><meta name="robots" content="noindex,follow"></head>'
                '<body><h1>NBA 2K27 Recensione PS5</h1></body></html>',
                encoding="utf-8")
            saved_card=('<article class="news-row"><a href="/sesame-street-amici-e-risate-recensione-ps5.html">'
                        '<img src="/cover.webp"></a><div class="news-copy"><h2>'
                        '<a href="/sesame-street-amici-e-risate-recensione-ps5.html">'
                        'Sesame Street: Amici e risate Recensione PS5</a></h2></div></article>')
            Path("recensioni-scritte.html").write_text(
                '<div class="news-list" id="reviewList">'+saved_card+'</div>',encoding="utf-8")
            pages,archived=module.existing_review_pages()
            assert len(pages)==2, pages
            rows=module.manual_review_rows(pages,archived)
            assert len(rows)==1 and rows[0]==saved_card
            incoming=[
                post("UgkxNewFever","Transport Fever 3 Recensione PS5"),
                post("UgkxNewSesame","Sesame Street: Amici e risate | Recensione PS5"),
                post("UgkxNewNBA","NBA 2K27 Recensione PS5"),
                post("UgkxNewUnique","Nuovo Gioco | Recensione PS5"),
                post("UgkxOldTransport","Transport Fever 3 | Recensione PS5"),
                post("UgkxOldUnique","Nuovo Gioco Recensione PS5"),
            ]
            chosen=module.select_unique_reviews(incoming,pages)
            ids=[p["id"] for p in chosen]
            assert "UgkxNewFever" not in ids,ids
            assert "UgkxNewSesame" not in ids,ids
            assert "UgkxOldTransport" in ids,ids
            assert "UgkxNewNBA" in ids,ids  # Noindex aliases are not a review
            assert "UgkxOldUnique" in ids and "UgkxNewUnique" not in ids,ids
            assert len(ids)==3,ids
        finally:
            os.chdir(previous)
    print("Review dedup tests OK: manual review, existing Community ID, "
          "repeat posts, platform and noindex handling.")


if __name__=="__main__":
    run()
