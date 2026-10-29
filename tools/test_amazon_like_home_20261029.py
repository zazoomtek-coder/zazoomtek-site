#!/usr/bin/env python3
"""Check actual Desktop CSS pixel layout in headless Chrome, never deploy."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import html as htmllib
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ARTICLE = DIST / "community-ugkxf-aembzj-nrh3uwdvfxhfshcpji31jjc.html"
PROBE = "zzt-real-browser-affiliate-geometry"

script = """
<script>
window.addEventListener('load', function() {
  setTimeout(function() {
    const by = sel => document.querySelector(sel);
    const area = by('.inner-layout');
    const related = by('.inner-layout>.related');
    const amazon = by('.inner-layout>.inner-amazon-fill');
    const rail = by('.inner-layout>.inner-sidebar');
    const story = by('.inner-layout>.inner-column');
    const rect = node => {
      const r = node.getBoundingClientRect();
      return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right};
    };
    const data = {related:rect(related),amazon:rect(amazon),
       rail:rect(rail),story:rect(story),display:getComputedStyle(area).display,
       template:getComputedStyle(area).gridTemplateAreas,
       scrollWidth:document.documentElement.scrollWidth,windowWidth:window.innerWidth,
       amazonIntro:getComputedStyle(by('.inner-amazon-fill .amazon-feature-intro')).display,
       amazonHeading:getComputedStyle(by('.inner-amazon-fill h2.amazon-feature-title')).fontSize,
       amazonBadge:getComputedStyle(by('.inner-amazon-fill .amazon-feature-badge')).fontSize,
       amazonImageMax:getComputedStyle(by('.inner-amazon-fill .amazon-feature-product img')).maxHeight,
       amazonCardRadius:getComputedStyle(by('.inner-amazon-fill .amazon-feature-box')).borderTopLeftRadius,
       amazonGridDisplay:getComputedStyle(by('.inner-amazon-fill .amazon-feature-products')).display,
       amazonGridColumns:getComputedStyle(by('.inner-amazon-fill .amazon-feature-products')).gridTemplateColumns,
       amazonProductY:Array.from(document.querySelectorAll('.inner-amazon-fill .amazon-feature-product')).map(x=>Math.round(x.getBoundingClientRect().y)),
       amazonHeight:rect(by('.inner-amazon-fill .amazon-feature-box')).height,
       amazonBorderColor:getComputedStyle(by('.inner-amazon-fill .amazon-feature-box')).borderTopColor,
       amazonLink:by('.inner-amazon-fill .amazon-feature-cta').href,
       amazonLabel:by('.inner-amazon-fill .amazon-feature-box h2').textContent
       };
    const status = document.createElement('pre');
    status.id = 'zzt-real-browser-affiliate-geometry';
    status.textContent = JSON.stringify(data);
    document.body.append(status);
  }, 700);
});
</script>
"""


def main():
    chrome = next((p for n in ("google-chrome", "chromium", "chromium-browser")
                   if (p := shutil.which(n))), None)
    if not chrome:
        raise RuntimeError("A real Chrome/Chromium binary is required; no fake layout pass.")
    assert ARTICLE.exists(), ARTICLE
    old = ARTICLE.read_text(encoding="utf-8")
    ARTICLE.write_text(old.replace("</body>", script + "</body>"), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0),
               partial(SimpleHTTPRequestHandler, directory=str(DIST)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_address[1]) + "/" + ARTICLE.name
    try:
        result = subprocess.run([chrome, "--headless=new", "--no-sandbox",
            "--disable-gpu", "--disable-dev-shm-usage", "--disable-extensions",
            "--hide-scrollbars", "--virtual-time-budget=6000",
            "--window-size=1500,950", "--dump-dom", url],
            timeout=55, text=True, capture_output=True)
        if result.returncode:
            raise AssertionError("Chrome returned "+str(result.returncode)+" "+result.stderr[-400:])
        m = re.search(r'<pre id="' + PROBE + r'">(.*?)</pre>', result.stdout, re.S)
        if not m:
            raise AssertionError("Chrome did not execute dynamic layout audit. " + result.stdout[-1200:])
        data = json.loads(htmllib.unescape(m.group(1)))
        print("CHROME ACTUAL PIXEL GEOMETRY", json.dumps(data, ensure_ascii=False),flush=True)
        assert data["display"] == "grid"
        assert abs(data["related"]["y"] - data["amazon"]["y"]) < 3, data
        assert abs(data["rail"]["x"] - data["amazon"]["x"]) < 3, data
        assert abs(data["story"]["width"] - data["related"]["width"]) < 3, data
        assert data["amazon"]["x"] > data["related"]["right"] + 5, data
        assert data["scrollWidth"] <= data["windowWidth"] + 2, data
        # Exact approved ZIP preview's computed visual metrics.
        assert data["amazonIntro"] == "block", data
        assert data["amazonHeading"] == "15.5px", data
        assert data["amazonBadge"] == "8px", data
        assert data["amazonImageMax"] == "49px", data
        assert data["amazonCardRadius"] == "9px", data
        assert data["amazonGridDisplay"] == "grid", data
        assert len(data["amazonGridColumns"].split()) == 3, data
        assert len(data["amazonProductY"]) == 3 and len(set(data["amazonProductY"])) == 1, data
        assert data["amazonHeight"] < 340, data
        assert data["amazonBorderColor"] == "rgb(255, 155, 12)", data
        assert data["amazonLink"] == "https://link.amazon/A0dJXv9PO", data
        assert data["amazonLabel"] == "Prodotti recensiti da ZazoomTek", data
        print("CHROME PASS: 3 tessere in una riga, look Home arancione, box compatto, link Amazon valido, no overflow.",flush=True)
    finally:
        server.shutdown()
        ARTICLE.write_text(old,encoding="utf-8")


if __name__ == "__main__":
    main()
