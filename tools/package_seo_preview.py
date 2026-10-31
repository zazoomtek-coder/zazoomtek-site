#!/usr/bin/env python3
"""Build a navigable, full-site OFFLINE preview. Never deploys anything."""
from pathlib import Path
from urllib.parse import urlsplit
from html import escape,unescape
import os,re,shutil,zipfile
from package_offline_preview import local_route

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
OUT=ROOT/"ZazoomTek_Anteprima_SEO_31-10-2026"
ZIP=ROOT/"ZazoomTek_Anteprima_Completa_SEO_31-10-2026.zip"

def main():
 if not (DIST/"index.html").is_file() or not (DIST/"_redirects").is_file():
  raise RuntimeError("Real build and verified redirect rules required.")
 if OUT.exists():shutil.rmtree(OUT)
 shutil.copytree(DIST,OUT)
 # Offline filesystem links: keep the actual site's markup, article prose,
 # covers and CSS intact; only rewrite local href/src/poster paths.
 for file in OUT.rglob("*.html"):
  original=DIST/file.relative_to(OUT)
  markup=file.read_text(encoding="utf-8")
  def rewrite(m):
   attr,q,url=m.group(1),m.group(2),m.group(3)
   return attr+q+escape(local_route(unescape(url),original),quote=True)+q
  markup=re.sub(r'((?:href|src|poster)=)(["\'])(/[^"\']*)\2',rewrite,markup)
  file.write_text(markup,encoding="utf-8")
 for file in OUT.rglob("*.css"):
  css=file.read_text(encoding="utf-8")
  relative=Path(os.path.relpath(DIST/"assets",(DIST/file.relative_to(OUT)).parent)).as_posix()
  css=re.sub(r'url\((["\']?)/assets/',lambda m:'url('+m.group(1)+relative+'/',css)
  file.write_text(css,encoding="utf-8")
 rows=[];seen=set()
 for line in (DIST/"_redirects").read_text(encoding="utf-8").splitlines():
  parts=line.split()
  if len(parts)!=3:continue
  old,new,code=parts
  if not re.match(r'^/(?:news|recensione)-Ug',old) or not old.endswith(".html"):
   continue
  if old in seen:continue
  seen.add(old)
  dest=DIST/(new.lstrip("/")+".html")
  if not dest.is_file():raise RuntimeError("Missing redirect target "+new)
  rows.append((old,new,code,new.lstrip("/")+".html"))
 rows.sort(key=lambda x:x[0].lower())
 items="".join(
  "<tr><td><code>"+escape(old)+"</code></td><td><a href='"+escape(page,quote=True)+"'>"+escape(new)+"</a></td><td>"+escape(code)+"</td></tr>"
  for old,new,code,page in rows
 )
 page="""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
 <title>Anteprima SEO ZazoomTek · 31 ottobre 2026</title>
 <style>:root{font:16px system-ui,Arial,sans-serif;color:#263344;background:#f3f5f8}*{box-sizing:border-box}body{margin:0}
 .container{max-width:1120px;margin:auto;padding:24px}.hero{background:#131e2f;color:white;padding:28px;border-radius:15px}
 h1{font-size:27px;margin:0 0 10px}a{color:#ad1842}a.btn{display:inline-block;background:#fff;color:#172235;font-weight:700;border-radius:6px;padding:12px 18px;text-decoration:none;margin:9px 8px 0 0}
 .panel{background:white;border:1px solid #d8dee6;padding:19px;border-radius:12px;margin:22px 0}.panel h2{margin-top:0}table{border-collapse:collapse;width:100%;font-size:13px;table-layout:fixed}td,th{border-bottom:1px solid #e3e9f0;text-align:left;padding:9px;overflow-wrap:anywhere}th{background:#eef2f7}th:nth-child(1){width:42%}th:nth-child(2){width:48%}th:nth-child(3){width:10%}
 code{font-size:12px}p{line-height:1.5}.stat{font-size:26px;font-weight:750;color:#1b7745}
 </style></head><body><div class="container"><div class="hero">
 <h1>Anteprima del nuovo ZazoomTek.it</h1>
 <p>31 ottobre 2026 · sito completo ricostruito dal codice GitHub · nessuna pubblicazione anticipata</p>
 <a class="btn" href="index.html">Apri Home completa</a><a class="btn" href="news.html">News</a>
 <a class="btn" href="recensioni.html">Recensioni</a><a class="btn" href="guide.html">Guide</a></div>
 <div class="panel"><h2>Anteprima dei recuperi SEO</h2>
 <p><span class="stat">"""+str(len(rows))+"""</span> vecchi URL con identificativo YouTube originale reindirizzati a pagine reali e verificabili nel nuovo sito.</p>
 <p>Le righe mostrano le regole 301 effettivamente generate da <code>tools/build.py</code>. Clicca su un URL di destinazione per aprire la pagina offline.</p>
 <p>Non sono stati generati reindirizzamenti per vecchie pagine eliminate senza contenuto equivalente. I percorsi con <code>.html</code> verso lo stesso contenuto sono già normalizzati automaticamente da Cloudflare.</p>
 <table><thead><tr><th>Vecchio URL</th><th>Pagina attuale</th><th>HTTP</th></tr></thead><tbody>"""+items+"""</tbody></table></div>
 <p>Anteprima offline: immagini YouTube esterne possono richiedere Internet. Studio e servizi API necessitano di un server. Le regole 301 si attiveranno soltanto dopo la pubblicazione Cloudflare.</p>
 </div></body></html>"""
 (OUT/"ANTEPRIMA_SEO.html").write_text(page,encoding="utf-8")
 (OUT/"LEGGIMI_ANTEPRIMA.txt").write_text(
  "ZAZOOMTEK.IT - ANTEPRIMA OFFLINE SEO DEL 31 OTTOBRE 2026\n\n"
  "1. Estrai lo ZIP COMPLETAMENTE in una cartella Windows.\n"
  "2. Apri ANTEPRIMA_SEO.html per verificare i vecchi URL e i 301.\n"
  "3. Apri index.html per navigare tutto il vero sito generato: Home, News, Recensioni, Guide e articoli.\n"
  "4. Le immagini YouTube esterne potrebbero richiedere Internet. Studio e API non funzionano offline.\n"
  "5. Nessun deploy effettuato dal generatore di anteprima.\n",
  encoding="utf-8")
 count=0
 with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for f in OUT.rglob("*"):
   if f.is_file():
    z.write(f,f.relative_to(OUT))
    count+=1
 if count<170 or len(rows)<80:
  raise RuntimeError(f"Incomplete offline preview: {count} files, {len(rows)} legacy article redirects")
 print(f"OFFLINE SEO PREVIEW OK: {count} files, {len(rows)} mapped article redirects, {ZIP.stat().st_size} bytes",flush=True)

if __name__=="__main__":main()
