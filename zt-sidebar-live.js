/* ZazoomTek — dynamic editorial sidebars, 2026.
   Rotates only real published stories/videos from /zt-sidebar-feed.json.
   The HTML assembled on Firebase remains a complete SEO-accessible fallback.
   No cookies, visitor identifiers or tracking; never changes article content. */
(function(){
  "use strict";
  // The homepage video sidebar is intentionally owned by its own live-video
  // workflow and must never acquire a duplicate featured-news block.
  if(location.pathname==="/" || location.pathname==="/index.html")return;

  const SIDEBAR_SLOT_MS=2*60*60*1000;
  const path=location.pathname;
  const slot=Math.floor(Date.now()/SIDEBAR_SLOT_MS);
  const used=new Set([path]);
  function hash(value){
    let n=2166136261;
    for(let i=0;i<value.length;i++){
      n^=value.charCodeAt(i);
      n=Math.imul(n,16777619);
    }
    return n>>>0;
  }
  function isStory(item){
    return item && typeof item.url==="string" &&
      /^\/[a-zA-Z0-9_%-]+\.html$/.test(item.url) &&
      typeof item.title==="string" && item.title.trim() &&
      typeof item.image==="string" && item.image.trim();
  }
  function choose(pool,key,count){
    if(!Array.isArray(pool) || !count)return [];
    const available=pool.filter(x=>isStory(x)&&!used.has(x.url));
    if(!available.length)return [];
    const start=(hash(path+"|"+key)+slot)%available.length;
    const picks=[];
    for(let i=0;i<available.length && picks.length<count;i++){
      const item=available[(start+i)%available.length];
      if(!picks.some(x=>x.url===item.url))picks.push(item);
    }
    for(const pick of picks)used.add(pick.url);
    return picks;
  }
  function setLink(link,item){
    if(!link||!item)return;
    link.href=item.url;
    if(link.querySelector("img")){
      const image=link.querySelector("img");
      image.src=item.image;
      image.alt=item.title;
    }
  }
  function feature(section,feed){
    const imgLink=section.querySelector("a.zt-mix-feature-image");
    const headline=section.querySelector(".zt-mix-feature-copy h3 a");
    if(!imgLink||!headline)return;
    const picked=choose(feed.news,"featured",1)[0];
    if(!picked)return;
    setLink(imgLink,picked);
    headline.href=picked.url;
    headline.textContent=picked.title;
    const button=section.querySelector(".zt-mix-read");
    if(button)button.href=picked.url;
  }
  function recent(section,feed){
    const module=section.querySelector(".module-title");
    const heading=(module?.textContent||"").toLowerCase();
    const group=heading.includes("recension")?"reviews":"news";
    const container=section.querySelector(".zt-mix-recent-list");
    if(!container)return;
    const rows=[...container.querySelectorAll("a.zt-mix-recent-row")];
    if(!rows.length)return;
    const selected=choose(feed[group],group+"-recent",rows.length);
    if(!selected.length)return;
    selected.forEach((item,i)=>{
      const row=rows[i];
      row.href=item.url;
      const image=row.querySelector("img");
      if(image){image.src=item.image;image.alt=item.title;}
      const label=row.querySelector("span");
      if(label)label.textContent=item.title;
    });
    // Only reduce rows if the source has fewer verified entries than the
    // number of available slots; don't duplicate the same story.
    rows.slice(selected.length).forEach(row=>{row.hidden=true;});
  }
  function editorial(section,feed){
    const module=section.querySelector("a.module-title");
    const href=module?.getAttribute("href")||"";
    let group=null;
    if(href.includes("/tech-today.html"))group="tech";
    else if(href.includes("/gaming-today.html"))group="gaming";
    else if(section.classList.contains("zt-sidebar-editorial") ||
            section.getAttribute("data-zt-auto")==="editorial")group="editorial";
    if(!group)return;
    const rows=[...section.querySelectorAll("a.zt-mix-editorial-row")];
    if(!rows.length)return;
    const selected=choose(feed[group],group+"-editorial",rows.length);
    if(!selected.length)return;
    selected.forEach((item,i)=>{
      const row=rows[i];
      row.href=item.url;
      const image=row.querySelector("img");
      if(image){image.src=item.image;image.alt=item.title;}
      const label=row.querySelector("span");
      if(label)label.textContent=item.title;
    });
    rows.slice(selected.length).forEach(row=>{row.hidden=true;});
  }
  function video(section,feed){
    const module=section.querySelector("a.module-title");
    const href=module?.getAttribute("href")||"";
    const category={
      "/recensioni.html":"recensioni",
      "/test.html":"test",
      "/unboxing.html":"unboxing",
      "/gaming.html":"gaming"
    }[href];
    if(!category)return;
    const videos=feed.videos?.[category];
    if(!Array.isArray(videos)||!videos.length)return;
    const available=videos.filter(v=>v&&/^[A-Za-z0-9_-]{11}$/.test(v.id)&&v.title);
    if(!available.length)return;
    const index=(hash(path+"|"+category+"-video")+slot)%available.length;
    const clip=available[index];
    const link=section.querySelector("a.zt-mix-video-row");
    if(!link)return;
    link.href="https://www.youtube.com/watch?v="+clip.id;
    const img=link.querySelector("img");
    if(img){
      img.src="https://i.ytimg.com/vi/"+clip.id+"/hqdefault.jpg";
      img.alt=clip.title;
    }
    const label=link.querySelector(":scope > span:last-child");
    if(label)label.textContent=clip.title;
  }
  function apply(feed){
    if(!feed || !Array.isArray(feed.news)|| !Array.isArray(feed.reviews))return;
    const asides=document.querySelectorAll("aside.zt-side-mix");
    for(const aside of asides){
      // Featured first, never move the Amazon affiliate widget or the box order.
      const sections=[...aside.querySelectorAll(":scope > section")];
      sections.filter(s=>s.classList.contains("zt-mix-feature")).forEach(s=>feature(s,feed));
      sections.filter(s=>s.classList.contains("zt-mix-recent")).forEach(s=>recent(s,feed));
      sections.filter(s=>s.classList.contains("zt-mix-editorial") &&
                          !s.classList.contains("zt-sidebar-editorial")).forEach(s=>editorial(s,feed));
      sections.filter(s=>s.classList.contains("zt-mix-video")).forEach(s=>video(s,feed));
      sections.filter(s=>s.classList.contains("zt-sidebar-editorial")).forEach(s=>editorial(s,feed));
      aside.dataset.ztSidebarLive="2h";
    }
  }
  if(!document.querySelector("aside.zt-side-mix"))return;
  if(typeof fetch!=="function")return;
  fetch("/zt-sidebar-feed.json",{cache:"no-store",credentials:"omit"})
    .then(response=>response.ok?response.json():null)
    .then(apply)
    .catch(()=>{/* Keep valid server-rendered SEO content on network errors. */});
})();