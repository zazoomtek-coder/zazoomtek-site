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

  // ZT_EDITORIAL_ADAPTIVE_20261015: align the last editorial item with
  // the last left-column item using ONLY distinct published articles.
  // No repeated section names, no repeated URL, and no empty spacer blocks.
  function upgradeEditorialRail(aside,feed){
    if(!aside.classList.contains("zt-side-mix") ||
       !aside.querySelector(".zt-mix-feature,.zt-mix-editorial,.zt-mix-recent"))return false;
    const filename=path.split("/").pop()||"";
    const isDetail=aside.classList.contains("article-side") ||
                   !!aside.closest(".detail-grid") ||
                   !!aside.parentElement?.querySelector(":scope > article, :scope > main");
    const types={
      featured:["News in evidenza","news","/news.html"],
      recent:["Ultimi articoli","news","/news.html"],
      impact:["Tech Impact","tech","/tech-today.html"],
      inside:["Gaming Inside","gaming","/gaming-today.html"],
      editorial:["Dalla redazione","editorial","/news.html"],
      reviews:["Ultime recensioni","reviews","/recensioni-scritte.html"],
      guides:["Guide","guides","/guide.html"]
    };
    let order;
    if(filename.startsWith("tech-impact-"))order=["impact","editorial","inside","featured","reviews","guides"];
    else if(filename.startsWith("gaming-inside-"))order=["inside","editorial","impact","featured","reviews","guides"];
    else if(filename.startsWith("guida-")||filename==="guide.html")order=["guides","editorial","featured","impact","inside","reviews"];
    else if(filename.includes("recensione")||filename.startsWith("test-")||filename.startsWith("unboxing-"))
      order=["reviews","editorial","impact","inside","featured","guides"];
    else if(filename==="tech-today.html")order=["impact","inside","editorial","featured","reviews","guides"];
    else if(filename==="gaming-today.html")order=["inside","impact","editorial","featured","reviews","guides"];
    else if(/^extra(?:-\d+)?\.html$/.test(filename))order=["editorial","featured","impact","inside","reviews","guides"];
    else order=["featured","editorial","impact","inside","reviews","guides"];

    // The content column, not the sidebar itself, defines how far down
    // editorial modules should extend. Article grids and archive grids both
    // have the sidebar as a direct sibling of their principal content.
    const parent=aside.parentElement;
    const content=[...(parent?.children||[])].filter(el=>el!==aside &&
      !/^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName));
    const left=content.reduce((best,el)=>{
      if(!best)return el;
      return el.getBoundingClientRect().height>best.getBoundingClientRect().height?el:best;
    },null);
    function targetHeight(){
      if(!left)return 0;
      const a=aside.getBoundingClientRect();
      const b=left.getBoundingClientRect();
      return Math.max(0,Math.round(b.bottom-a.top));
    }
    const singleColumn=window.matchMedia?.("(max-width:980px)").matches || false;
    const height=targetHeight();
    const target=singleColumn?0:height;
    if(!singleColumn && target<200)return false;

    // Show fewer unique sections on short pages; never repeat a heading.
    // Remaining space is handled by adding real stories INSIDE existing
    // sections rather than cloning the whole section.
    const boxLimit=singleColumn?2:Math.min(order.length,Math.max(1,
      target<700?1:target<1150?2:target<1800?3:target<2550?4:target<3500?5:6));
    const initialCount=singleColumn?3:target<500?1:target<1000?2:3;
    const usedUrls=new Set([path]);
    const pools={};
    for(const key of order){
      const group=types[key][1],items=feed[group];
      const valid=(Array.isArray(items)?items:[]).filter(isStory);
      const uniq=[];const seen=new Set();
      for(const item of valid)if(!seen.has(item.url)){seen.add(item.url);uniq.push(item);}
      const start=(hash(path+"|"+key)+slot)%Math.max(uniq.length,1);
      pools[key]=uniq.slice(start).concat(uniq.slice(0,start));
    }
    function next(key){
      for(const item of pools[key]){
        if(!usedUrls.has(item.url)){
          usedUrls.add(item.url);
          return item;
        }
      }
      return null;
    }
    const el=(tag,cls)=>{
      const node=document.createElement(tag);
      if(cls)node.className=cls;
      return node;
    };
    function row(item){
      const article=el("article","zt-special-item");
      const picture=el("a","zt-special-thumb");
      picture.href=item.url;picture.setAttribute("aria-label",item.title);
      const img=el("img");
      img.src=item.image;img.alt=item.title;img.loading="lazy";img.decoding="async";
      picture.append(img);
      const h3=el("h3"),link=el("a");
      link.href=item.url;link.textContent=item.title;
      h3.append(link);article.append(picture,h3);
      return article;
    }
    function module(key,items){
      const [title,group,href]=types[key];
      const box=el("section","zt-special-box zt-editorial-large-box");
      box.setAttribute("aria-label",title);
      const head=el("header","zt-special-head");
      const h2=el("h2");h2.textContent=title.toUpperCase();
      const see=el("a");see.href=href;see.textContent="VEDI →";
      head.append(h2,see);
      const list=el("div","zt-special-list");
      for(const item of items)list.append(row(item));
      const footer=el("footer","zt-special-footer");
      const all=el("a");all.href=href;all.textContent="Tutti gli articoli →";
      footer.append(all);box.append(head,list,footer);
      return {key,group,box,list};
    }
    const currentAmazon=aside.querySelector(":scope > section.zt-amazon-partner");
    const preserved=[...aside.children].filter(node=>
      node.tagName==="SECTION" &&
      !node.matches(".zt-mix-feature,.zt-mix-editorial,.zt-mix-recent,.zt-mix-video,.zt-amazon-partner"));
    const records=[];
    for(const key of order){
      if(records.length>=boxLimit)break;
      const picks=[];
      for(let i=0;i<initialCount;i++){
        const item=next(key);
        if(item)picks.push(item);
      }
      if(picks.length)records.push(module(key,picks));
    }
    if(!records.length)return false;
    const nodes=[];
    records.forEach((r,i)=>{
      nodes.push(r.box);
      if(i===0 && currentAmazon)nodes.push(currentAmazon);
    });
    if(!currentAmazon){
      const existingAmazon=aside.querySelector(":scope > section.zt-amazon-partner");
      if(existingAmazon)nodes.splice(1,0,existingAmazon);
    }
    aside.replaceChildren(...nodes,...preserved);
    aside.dataset.ztLargeEditorial="three-cards";

    // Rebuild from the verified feed only when the MAIN content changes size.
    // Observing the sidebar itself could create an endless feedback loop.
    const MAX_ROWS=target>3700?14:target>2400?11:8;
    function fit(){
      if(singleColumn)return;
      const viewportTarget=targetHeight();
      if(viewportTarget<200)return;
      for(const r of records)for(const card of r.list.children){
        card.style.removeProperty("padding-top");
        card.style.removeProperty("padding-bottom");
      }
      const sideHeight=()=>aside.getBoundingClientRect().height;
      // Prefer trimming existing articles over creating a taller sidebar.
      let guard=0;
      while(sideHeight()>viewportTarget+35 && guard++<80){
        const candidates=records.filter(r=>r.list.children.length>1);
        if(!candidates.length)break;
        candidates.sort((a,b)=>b.list.children.length-a.list.children.length);
        candidates[0].list.lastElementChild.remove();
      }
      // Grow content proportionally, keeping the section names unique.
      // A small number of extra boxes is allowed when the existing ones
      // have already accumulated many thumbnails.
      const stalled=new Set();
      guard=0;
      while(viewportTarget-sideHeight()>62 && guard++<100){
        let options=records.filter(r=>r.list.children.length<MAX_ROWS &&
                                       !stalled.has(r.key));
        options.sort((a,b)=>a.list.children.length-b.list.children.length);
        let chosen=null,added=false;
        for(const r of options){
          const item=next(r.key);
          if(!item){stalled.add(r.key);continue;}
          chosen={r,item};break;
        }
        if(!chosen){
          if(records.length>=order.length)break;
          const nextKey=order.find(k=>!records.some(r=>r.key===k) &&
                                       pools[k].some(x=>!usedUrls.has(x.url)));
          if(!nextKey)break;
          const items=[];
          for(let i=0;i<Math.min(2,initialCount);i++){
            const item=next(nextKey);
            if(item)items.push(item);
          }
          if(!items.length)break;
          const newRecord=module(nextKey,items);
          const before=Math.abs(viewportTarget-sideHeight());
          aside.append(newRecord.box);
          const after=Math.abs(viewportTarget-sideHeight());
          if(after<before || viewportTarget-sideHeight()>0){
            records.push(newRecord);
            stalled.clear();
            added=true;
          }else{
            newRecord.box.remove();
            // Avoid retrying the same unsuccessful category.
            pools[nextKey]=[];
          }
        }else{
          const before=Math.abs(viewportTarget-sideHeight());
          const child=row(chosen.item);
          chosen.r.list.append(child);
          const after=Math.abs(viewportTarget-sideHeight());
          if(after<=before || viewportTarget-sideHeight()>0){
            added=true;stalled.clear();
          }else{
            child.remove();
            stalled.add(chosen.r.key);
          }
        }
        if(!added && stalled.size>=records.length)break;
      }
      // Distribute the final small difference across genuine cards instead
      // of inserting an artificial white spacer at the bottom.
      const remaining=viewportTarget-sideHeight();
      const cards=records.flatMap(r=>[...r.list.children]);
      if(remaining>2 && cards.length){
        const boost=Math.min(20,Math.floor(remaining/(cards.length*2)));
        if(boost>0)for(const card of cards){
          card.style.setProperty("padding-top",(14+boost)+"px","important");
          card.style.setProperty("padding-bottom",(14+boost)+"px","important");
        }
      }
      aside.dataset.ztAdaptiveRail="true";
    }
    fit();
    if(singleColumn)return true;
    let queued=false;
    const scheduleFit=()=>{
      if(queued)return;
      queued=true;
      requestAnimationFrame(()=>{queued=false;fit();});
    };
    window.addEventListener("load",scheduleFit,{once:true});
    window.addEventListener("resize",scheduleFit,{passive:true});
    if(typeof ResizeObserver!=="undefined" && left){
      const observer=new ResizeObserver(scheduleFit);
      observer.observe(left);
    }
    return true;
  }

  function apply(feed){
    if(!feed || !Array.isArray(feed.news)|| !Array.isArray(feed.reviews))return;
    const asides=document.querySelectorAll("aside.zt-side-mix, aside.sidebar");
    for(const aside of asides){
      if(upgradeEditorialRail(aside,feed)){
        aside.dataset.ztSidebarLive="2h";
        continue;
      }
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
  if(!document.querySelector("aside.zt-side-mix, aside.sidebar"))return;
  if(typeof fetch!=="function")return;
  fetch("/zt-sidebar-feed.json",{cache:"no-store",credentials:"omit"})
    .then(response=>response.ok?response.json():null)
    .then(apply)
    .catch(()=>{/* Keep valid server-rendered SEO content on network errors. */});
})();