#!/usr/bin/env python3
"""Offline tests for independent Studio editing and static snapshot packaging."""
import importlib.util
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

studio=load("services10_studio","08-studio.py")
layout=load("services10_layout","09-layout.py")

def main():
    with TemporaryDirectory() as folder:
        root=Path(folder)
        (root/"studio").mkdir()
        (root/"watch").mkdir()
        (root/"assets").mkdir()
        (root/"scripts").mkdir()
        (root/"services10-data").mkdir()
        (root/"studio"/"edit-button.js").write_text("window.ZT_EDIT=true;",encoding="utf-8")
        (root/"studio"/"index.html").write_text("<html><body><main>Studio</main></body></html>")
        (root/"index.html").write_text("<html><head><title>Home</title></head><body><main>Home</main></body></html>")
        (root/"news.html").write_text("<html><head><title>News</title></head><body><main>News archive</main></body></html>")
        article=root/"news-UgkxArticle.html"
        article.write_text('<html><head><title>Article</title></head><body><main><h1>News</h1></main></body></html>')
        (root/"watch"/"index.html").write_text("<html><body>Watch archive</body></html>")
        video=root/"watch"/"abcdef12345.html"
        video.write_text("<html><body><main><h1>Video</h1></main></body></html>")
        (root/"zt-design.css").write_text("body{color:#111}")
        (root/"assets"/"cover.webp").write_bytes(b"fake-image-for-byte-copy-only")
        (root/"scripts"/"private.py").write_text("print('private')")
        (root/"services10-data"/"community.json").write_text('{"private":"staging"}')
        (root/".env").write_text("SENSITIVE=private")
        (root/"notizie-dal-web.json").write_text('{"items":[]}')
        assert studio.inject(root)==2
        assert studio.inject(root)==0
        assert '/studio/edit-button.js' not in (root/"index.html").read_text()
        assert '/studio/edit-button.js' not in (root/"studio"/"index.html").read_text()
        assert '/studio/edit-button.js' in article.read_text()
        assert '/studio/edit-button.js' in video.read_text()
        source_digest=hashlib.sha256((root/"assets"/"cover.webp").read_bytes()).hexdigest()
        result=layout.build(root)
        dist=root/"dist"
        assert result["home"] and result["news"] and result["studio"] and result["watch"]
        assert (dist/"news-UgkxArticle.html").is_file()
        assert (dist/"studio"/"edit-button.js").is_file()
        assert (dist/"zt-design.css").is_file()
        assert (dist/"notizie-dal-web.json").is_file()
        assert not (dist/".env").exists()
        assert not (dist/"scripts"/"private.py").exists()
        assert not (dist/"services10-data"/"community.json").exists()
        assert hashlib.sha256((dist/"assets"/"cover.webp").read_bytes()).hexdigest()==source_digest
    print("PASS: complete static snapshot preserves content and images; Studio only on interior pages")

if __name__=="__main__":
    main()
