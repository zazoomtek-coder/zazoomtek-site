#!/usr/bin/env python3
"""Offline full-home screenshots and basic browser layout smoke tests."""
import argparse
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import threading
from playwright.sync_api import sync_playwright

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path("dist"))
    ap.add_argument("--output",type=Path,default=Path("staging-screenshots"))
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    http=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(a.root.resolve())))
    threading.Thread(target=http.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for label,width,height in (("desktop",1440,900),("tablet",820,1080),("mobile",390,844)):
                page=browser.new_page(viewport={"width":width,"height":height})
                page.goto(f"http://127.0.0.1:{http.server_port}/",wait_until="domcontentloaded",timeout=30000)
                page.wait_for_selector("#ztFeaturedGrid",timeout=20000)
                page.wait_for_timeout(1700)
                c=page.locator("#ztFeaturedGrid > a.zt-feature-card")
                if c.count()!=5:raise RuntimeError(f"{label}: {c.count()} cards")
                sections=c.evaluate_all("(a)=>a.map(n=>n.dataset.featureSection)")
                if sections!=["tech"]*4+["gaming"]:raise RuntimeError(f"{label}: incorrect categories")
                frame=page.locator("#ztFeaturedGrid").bounding_box()
                if not frame or frame["height"]<100 or frame["width"]<200:
                    raise RuntimeError(f"{label}: featured area collapsed")
                if page.locator("body").evaluate("(e)=>e.scrollWidth")>width+20:
                    raise RuntimeError(f"{label}: horizontal overflow")
                page.screenshot(path=str(a.output/f"home-{label}.png"),full_page=True,animations="disabled")
                page.close()
                print(f"PASS {label}: 5 cards, correct order, visible and within viewport",flush=True)
            browser.close()
    finally:
        http.shutdown();http.server_close()
if __name__=="__main__":main()
