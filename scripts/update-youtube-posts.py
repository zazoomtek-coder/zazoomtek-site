#!/usr/bin/env python3
import json,re,html,urllib.request
from pathlib import Path

URL="https://www.youtube.com/@ZazoomTek/posts"
STATE=Path(".youtube-posts.json")
INDEX=Path("index.html")

def fetch():
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36","Accept-Language":"it-IT,it;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode("utf-8","replace")

def initial_data(s):
    pats=[r'var ytInitialData = ({.*?});</script>',r'ytInitialData\s*=\s*({.*?});</script>']
    for p in pats:
        m=re.search(p,s,re.S)
        if m:
            try:return json.loads(m.group(1))
            except:pass
    return {}

def txt(v):
    if not isinstance(v,dict):return ""
    if "simpleText" in v:return v["simpleText"]
    return "".join(x.get("text","") for x in v.get("runs",[]) if isinstance(x,dict))

def walk(x,out):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ("backstagePostRenderer","postRenderer") and isinstance(v,dict): out.append(v)
            walk(v,out)
    elif isinstance(x,list):
        for v in x:walk(v,out)

def image_url(p):
    found=[]
    def w(x):
        if isinstance(x,dict):
            if isinstance(x.get("thumbnails"),list):
                for t in x["thumbnails"]:
                    u=t.get("url","")
                    if u.startswith("http"):found.append((t.get("width",0)*t.get("height",0),u))
            for v in x.values():w(v)
        elif isinstance(x,list):
            for v in x:w(v)
    w(p)
    return max(found,default=(0,""))[1].replace("\\u0026","&")

def parse(s):
    nodes=[];walk(initial_data(s),nodes);posts=[];seen=set()
    for p in nodes:
        pid=p.get("postId") or p.get("backstagePostId")
        if not pid or pid in seen:continue
        seen.add(pid)
        body=txt(p.get("contentText",{})) or txt(p.get("backstagePostText",{}))
        when=txt(p.get("publishedTimeText",{}))
        posts.append({"id":pid,"text":body.strip(),"published":when,"image":image_url(p),"url":"https://www.youtube.com/post/"+pid})
    return posts[:5]

def render(posts):
    cards=[]
    for p in posts:
        im=f'<a href="{html.escape(p["url"])}" target="_blank" rel="noopener"><img src="{html.escape(p["image"])}" alt="Post Community ZazoomTek" loading="lazy"></a>' if p["image"] else ""
        body=html.escape(p["text"] or "Post Community ZazoomTek")
        cards.append(f'''    <article class="community-post-card">{im}<div class="community-post-copy"><p>{body}</p><small>{html.escape(p["published"])}</small><a href="{html.escape(p["url"])}" target="_blank" rel="noopener">Apri su YouTube →</a></div></article>''')
    return '\n'.join(cards)

def main():
    posts=parse(fetch())
    if not posts:
        print("No public posts parsed; keeping current site unchanged.")
        return
    STATE.write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    s=INDEX.read_text(encoding="utf-8")
    repl="<!-- COMMUNITY_POSTS_START -->\n  <section class=\"community-posts-grid\" id=\"community-posts-grid\">\n"+render(posts)+"\n  </section>\n  <!-- COMMUNITY_POSTS_END -->"
    s2=re.sub(r'<!-- COMMUNITY_POSTS_START -->.*?<!-- COMMUNITY_POSTS_END -->',repl,s,flags=re.S)
    if s2!=s:INDEX.write_text(s2,encoding="utf-8")
    print("Synced",len(posts),"YouTube Community posts")

if __name__=="__main__":main()
