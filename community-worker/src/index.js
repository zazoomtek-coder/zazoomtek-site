const ID = /^Ugkx[A-Za-z0-9_-]{12,90}$/;
const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[char]));
const json = (value,status=200) => new Response(JSON.stringify(value),{
  status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}
});
const html = (value,status=200) => new Response(value,{
  status,headers:{"content-type":"text/html; charset=utf-8","cache-control":"public, max-age=60"}
});
function classify(text) {
  const head=text.split(/\r?\n/,1)[0].toLowerCase();
  if (/^(review|recensione)\b/.test(head)) return "recensioni";
  if (/\b(gaming|videogioc|playstation|xbox|nintendo)\b/.test(head)) return "gaming";
  if (/^news\b/.test(head)) return "news";
  return "community";
}
function page(title,body) {
  return `<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${esc(title)} | ZazoomTek</title><meta name="robots" content="index,follow,max-image-preview:large">
  <style>body{margin:0;color:#222;background:#f2f2f2;font:17px/1.65 system-ui,Arial}header,footer{background:#171717;color:white;padding:18px 5vw}header a,footer a{color:white}main{max-width:920px;margin:25px auto;padding:28px;background:white}h1{font-size:clamp(25px,4vw,42px);line-height:1.18}article p{white-space:pre-wrap;overflow-wrap:anywhere}.muted{color:#666;font-size:14px}a{color:#ae102c}</style></head><body>
  <header><a href="https://zazoomtek.it/">ZAZOOMTEK</a> · <a href="/community/">Community</a></header><main>${body}</main>
  <footer>© ZazoomTek · <a href="/privacy.html">Privacy</a></footer></body></html>`;
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    if (url.pathname==="/community/health") {
      try {
        await env.POSTS.prepare("SELECT 1 FROM community_posts LIMIT 1").first();
        return json({ok:true,service:"community-worker",storage:"d1"});
      } catch (error) {return json({ok:false,error:"D1 unavailable"},503);}
    }
    if(url.pathname==="/community/ingest") {
      if(request.method!=="POST") return json({error:"POST required"},405);
      if(!env.INGEST_TOKEN) return json({error:"Ingest token not configured"},503);
      if(request.headers.get("authorization")!==`Bearer ${env.INGEST_TOKEN}`) return json({error:"Unauthorized"},401);
      const size=Number(request.headers.get("content-length")||0);
      if(size>1024*1024) return json({error:"Payload too large"},413);
      let data;
      try{data=await request.json();}catch{return json({error:"Invalid JSON"},400);}
      if(!Array.isArray(data.posts)||data.posts.length>50) return json({error:"Expected at most 50 posts"},400);
      const failed=[];let accepted=0;
      for(const p of data.posts) {
        if(!p||!ID.test(p.id)||typeof p.text!=="string"||!p.text.trim()||p.text.length>20000){
          failed.push({id:String(p?.id??"").slice(0,100),error:"Invalid source"});continue;
        }
        const title=p.text.split(/\r?\n/,1)[0].trim().slice(0,240);
        const iso=typeof p.published_iso==="string"?p.published_iso.slice(0,40):"";
        const source=`https://www.youtube.com/post/${p.id}`;
        const category=classify(p.text);
        try{
          await env.POSTS.prepare(
            "INSERT INTO community_posts (id,title,body,category,published_iso,source_url,updated_utc) VALUES (?,?,?,?,?,?,datetime('now')) "+
            "ON CONFLICT(id) DO UPDATE SET title=excluded.title,body=excluded.body,category=excluded.category,published_iso=excluded.published_iso,updated_utc=datetime('now')"
          ).bind(p.id,title,p.text,category,iso,source).run();accepted++;
        }catch(error){failed.push({id:p.id,error:"Database write failed"});}
      }
      return json({accepted,failed,complete:failed.length===0},failed.length?207:200);
    }
    if(request.method!=="GET" && request.method!=="HEAD") return json({error:"Method not allowed"},405);
    if(url.pathname==="/community/"||url.pathname==="/community") {
      const rows=await env.POSTS.prepare("SELECT id,title,category,published_iso FROM community_posts ORDER BY CASE WHEN published_iso='' THEN 1 ELSE 0 END,published_iso DESC,updated_utc DESC LIMIT 100").all();
      const cards=rows.results.map(p=>`<article><h2><a href="/community/post/${p.id}">${esc(p.title)}</a></h2><p class="muted">${esc(p.category)} · ${esc(p.published_iso)}</p></article>`).join("");
      return html(page("Community ZazoomTek",`<h1>Community ZazoomTek</h1><p>Post, news e recensioni importati dalla Community ufficiale.</p>${cards||"<p>In attesa del primo import.</p>"}`));
    }
    const match=/^\/community\/post\/(Ugkx[A-Za-z0-9_-]{12,90})\/?$/.exec(url.pathname);
    if(match){
      const p=await env.POSTS.prepare("SELECT * FROM community_posts WHERE id=?").bind(match[1]).first();
      if(!p)return html(page("Non trovato","<h1>Articolo non trovato</h1>"),404);
      const paragraphs=p.body.split(/\n\s*\n/).filter(Boolean).map(v=>`<p>${esc(v)}</p>`).join("");
      const canonical=`https://zazoomtek.it/community/post/${p.id}`;
      return html(page(p.title,`<article><h1>${esc(p.title)}</h1><p class="muted">${esc(p.published_iso)} · ${esc(p.category)}</p>${paragraphs}
      <p class="muted">Fonte: <a rel="noopener noreferrer" href="${esc(p.source_url)}">Post originale su YouTube</a></p></article>`));
    }
    return json({error:"Not found"},404);
  }
};
