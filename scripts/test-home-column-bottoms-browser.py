#!/usr/bin/env python3
"""Fail closed on a visibly empty Home Tech/Gaming column (real Chromium).

This observes the rendered article bottoms, not just the number of news cards.
The design is locked; the fix must operate on real chronological news only.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    root = Path("dist")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Quiet, directory=str(root.resolve()))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True, args=["--no-sandbox"]
            )
            for width in (1150, 1440, 1770):
                page = browser.new_page(viewport={"width": width, "height": 950})
                page.goto(
                    f"http://127.0.0.1:{server.server_port}/",
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
                page.wait_for_selector(
                    "#articoli .ztp-news-tech .ztp-news-items > article",
                    timeout=25000,
                )
                # Lazy-loaded news images must be measured AFTER scrolling.
                page.locator(
                    "#articoli .ztp-news-gaming .ztp-news-items > article"
                ).last.scroll_into_view_if_needed()
                page.wait_for_timeout(2500)
                page.locator(
                    "#articoli .ztp-news-tech .ztp-news-items > article"
                ).last.scroll_into_view_if_needed()
                page.wait_for_timeout(1800)
                data = page.evaluate("""() => {
                    function cards(category) {
                        return [...document.querySelectorAll(
                          '#articoli .ztp-news-' + category +
                          ' .ztp-news-items > article.article-row'
                        )].filter(node => !node.hidden &&
                              node.getBoundingClientRect().height > 0);
                    }
                    const tech=cards('tech'),gaming=cards('gaming');
                    const url=(card)=>new URL(
                        card.querySelector('h3 a')?.href || '/',
                        location.origin
                    ).pathname;
                    const featured=[...document.querySelectorAll(
                        '#ztFeaturedGrid > a'
                    )].map(x => new URL(x.href).pathname);
                    return {
                        techCount:tech.length,gamingCount:gaming.length,
                        diff:tech.length&&gaming.length
                          ? Math.abs(tech.at(-1).getBoundingClientRect().bottom -
                                     gaming.at(-1).getBoundingClientRect().bottom)
                          : Infinity,
                        links:[...tech,...gaming].map(url),
                        featured,techBottom:tech.at(-1)?.getBoundingClientRect().bottom,
                        gamingBottom:gaming.at(-1)?.getBoundingClientRect().bottom
                    };
                }""")
                print(f"DESKTOP {width}: Tech={data['techCount']} "
                      f"Gaming={data['gamingCount']} "
                      f"bottom-gap={data['diff']:.1f}px", flush=True)
                links = data["links"]
                if data["techCount"] < 10 or data["gamingCount"] < 10:
                    raise AssertionError(f"{width}: a news column is empty")
                if len(links) != len(set(links)):
                    raise AssertionError(f"{width}: duplicate article links")
                if set(links) & set(data["featured"]):
                    raise AssertionError(f"{width}: carousel article appears twice")
                if data["diff"] > 180:
                    raise AssertionError(
                        f"{width}: visible white gap of {data['diff']:.1f}px "
                        "between the Tech and Gaming column bottoms"
                    )
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
