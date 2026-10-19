#!/usr/bin/env python3
"""Isolated TG INSIDE / SPECIALI regression tests. Does not touch production."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
f=ROOT/'scripts/build-speciali.py'
spec=importlib.util.spec_from_file_location('zt_specials',f)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def check():
    special=(ROOT/'speciali.html').read_text(encoding='utf-8')
    home=(ROOT/'index.html').read_text(encoding='utf-8')
    assert special.count(mod.START)==special.count(mod.END)==1
    assert '<aside class="news-sidebar zt-side-mix">' in special
    assert 'zt-mix-recent' in special and 'zt-mix-feature' in special
    assert 'class="legal-footer' in special
    assert 'zt-specials-intro' in special
    assert '<meta property="og:title"' in special
    assert 'link rel="canonical"' in special
    assert 'id="zt-specials-ld"' in special
    assert '<nav class="nav">' in home
    assert 'TG INSIDE' not in home  # No risk to locked static Home navbar.
    visual=(ROOT/'zt-visual.js').read_text(encoding='utf-8')
    assert 'ZT_TG_INSIDE_20261019' in visual
    assert 'tech-today.html' in visual and 'gaming-today.html' in visual and 'speciali.html' in visual

    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        (root/'speciali.html').write_text(special,encoding='utf-8')
        (root/'sitemap.xml').write_text('<?xml version="1.0"?><urlset></urlset>',encoding='utf-8')
        (root/'studio').mkdir()
        (root/'assets/studio').mkdir(parents=True)
        (root/'assets/studio/test-cover.webp').write_bytes(b'RIFFxxWEBP')
        data=[
            {'category':'Speciali Tech','title':'Leggi e tecnologia: analisi','url':'/studio-speciali-tech-analisi.html',
             'image':'/assets/studio/test-cover.webp','published_at':'2026-10-19T12:00:00Z','description':'Tecnologia e norme'},
            {'category':'Speciali Gaming','title':'Diritti digitali dei giocatori','url':'/studio-speciali-gaming-diritti.html',
             'image':'/assets/studio/test-cover.webp','published_at':'2026-10-18T12:00:00Z','description':'Industria e tutela'},
            {'category':'Speciali Tech','title':'Duplicato','url':'/studio-speciali-tech-analisi.html',
             'image':'/assets/studio/test-cover.webp','published_at':'2026-10-16T12:00:00Z'},
            {'category':'Speciali Gaming','title':'Da ignorare, immagine assente','url':'/studio-speciali-gaming-broken.html',
             'image':'/assets/studio/absent.webp','published_at':'2026-10-16T12:00:00Z'}
        ]
        for p in ('studio-speciali-tech-analisi.html','studio-speciali-gaming-diritti.html',
                  'studio-speciali-gaming-broken.html'):
            (root/p).write_text('<html></html>',encoding='utf-8')
        (root/'studio/articoli.json').write_text(json.dumps(data),encoding='utf-8')
        assert mod.build(root)==2
        output=(root/'speciali.html').read_text(encoding='utf-8')
        assert output.count('data-zt-special="approved"')==2
        assert output.count('href="/studio-speciali-tech-analisi.html"')==2
        assert output.count('href="/studio-speciali-gaming-diritti.html"')==2
        assert 'Da ignorare' not in output and 'Duplicato' not in output
        schema=output.split('<script id="zt-specials-ld" type="application/ld+json">')[1].split('</script>')[0]
        data=json.loads(schema)
        assert data['@graph'][0]['mainEntity']['itemListElement'][0]['position']==1
        assert data['@graph'][0]['mainEntity']['itemListElement'][0]['url'].endswith('studio-speciali-tech-analisi.html')
        ET.fromstring((root/'sitemap.xml').read_text(encoding='utf-8'))
        assert mod.build(root)==2
        assert (root/'sitemap.xml').read_text(encoding='utf-8').count('/speciali.html')==1
    print('PASS: TG Inside Home-safe; complete sidebar and SEO; approved-only deduped SPECIALI')

if __name__=='__main__':
    check()
