/* ZazoomTek — dynamic editorial sidebars, 2026.
   Always selects newest verified stories/videos from /zt-sidebar-feed.json.
   The HTML assembled on Firebase remains a complete SEO-accessible fallback.
   No cookies, visitor identifiers or tracking; never changes article content. */
(function(){
  "use strict";
  // The homepage video sidebar is intentionally owned by its own live-video
  // workflow and must never acquire a duplicate featured-news block.
  if(location.pathname==="/" || location.pathname==="/index.html")return;

  const SIDEBAR_SLOT_MS=24*60*60*1000;
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
    // The feed is sorted newest first at publication time. Never wrap around
    // and show a 15 October item ahead of a still-eligible 16 October item.
    const picks=available.slice(0,count);
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
    const clip=available[0];
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


  // ZT_EDITORIAL_CONTEXT_FILTER_20261015
  // Recommend OTHER topics, never links or headlines already in main content.
  function storySection(url){
    const v=String(url||"").split(/[?#]/)[0].replace(/^.*\//,"").toLowerCase();
    if(v==="tech-today.html"||v.startsWith("tech-impact-"))return "tech";
    if(v==="gaming-today.html"||v.startsWith("gaming-inside-"))return "gaming";
    if(v==="guide.html"||v.startsWith("guida-"))return "guides";
    if(/^recensioni-scritte(?:-\d+)?\.html$/.test(v)||v.startsWith("recensione-")||/(?:^|-)recensione(?:-|\.html)/.test(v))return "reviews";
    if(/^news(?:-\d+)?\.html$/.test(v)||v.startsWith("news-"))return "news";
    if(/^extra(?:-\d+)?\.html$/.test(v))return "extra";
    return null;
  }
  function normalizedHeadline(value){
    return String(value||"").normalize("NFKC")
      .replace(/^(?:news(?:\s+(?:tech|gaming|extra))?|review)\s*:\s*/i,"")
      .replace(/[‘’]/g,"'")
      .replace(/\s+/g," ").trim().toLowerCase();
  }
  function editorialContext(main,filename){
    const topic=storySection(filename);
    const links=new Set([path]);
    const titles=new Set();
    for(const anchor of main.querySelectorAll("a[href]")){
      try{
        const u=new URL(anchor.getAttribute("href"),location.href);
        if(u.origin===location.origin && /^\/[a-zA-Z0-9_%-]+\.html$/.test(u.pathname))
          links.add(u.pathname);
      }catch(error){/* Skip non-web or malformed targets. */}
      const text=normalizedHeadline(anchor.textContent);
      if(text.length>=22)titles.add(text);
    }
    for(const node of main.querySelectorAll("h1,h2,h3")){
      const title=normalizedHeadline(node.textContent);
      if(title.length>=22)titles.add(title);
    }
    return {topic,links,titles};
  }
  function eligibleDiscovery(item,context){
    if(!isStory(item))return false;
    if(context.topic && storySection(item.url)===context.topic)return false;
    if(context.links.has(item.url))return false;
    if(context.titles.has(normalizedHeadline(item.title)))return false;
    return true;
  }

  // ZT_EDITORIAL_HOME_STACK_20261015
  // Approved Home layout on internal pages: 16:9 full-width images, title below.
  // Uses the *actual bottom of the black Community banner* as the limit.
  function upgradeEditorialRail(aside,feed){
    if(!aside.classList.contains("zt-side-mix") ||
       !aside.querySelector(".zt-mix-feature,.zt-mix-editorial,.zt-mix-recent"))return false;
    const filename=path.split("/").pop()||"";
    const parent=aside.parentElement;
    const siblings=[...(parent?.children||[])].filter(node=>node!==aside &&
      node.nodeType===1 && !/^(SCRIPT|STYLE)$/.test(node.tagName));
    const main=siblings.sort((a,b)=>
      b.getBoundingClientRect().height-a.getBoundingClientRect().height)[0];
    if(!main)return false;
    const original=[...aside.childNodes];
    const affiliate=aside.querySelector(":scope > .zt-amazon-partner");
    const kept=[...aside.children].filter(node=>node.tagName==="SECTION" &&
      !node.matches(".zt-mix-feature,.zt-mix-editorial,.zt-mix-recent,.zt-mix-video,.zt-amazon-partner"));
    const selected={
      featured:["News in evidenza","news","/news.html"],
      recent:["Ultimi articoli","news","/news.html"],
      impact:["Tech Impact","tech","/tech-today.html"],
      inside:["Gaming Inside","gaming","/gaming-today.html"],
      editorial:["Dalla redazione","editorial","/news.html"],
      reviews:["Ultime recensioni","reviews","/recensioni-scritte.html"],
      guides:["Guide","guides","/guide.html"]
    };
    let order;
    if(filename.startsWith("tech-impact-"))order=["impact","editorial","inside","featured","reviews","recent","guides"];
    else if(filename.startsWith("gaming-inside-"))order=["inside","editorial","impact","featured","reviews","recent","guides"];
    else if(filename.startsWith("guida-")||filename==="guide.html")order=["guides","editorial","featured","impact","inside","reviews","recent"];
    else if(filename.includes("recensione")||filename.startsWith("test-")||filename.startsWith("unboxing-"))
      order=["reviews","editorial","impact","inside","featured","guides","recent"];
    else if(filename==="tech-today.html")order=["impact","inside","editorial","featured","reviews","recent","guides"];
    else if(filename==="gaming-today.html")order=["inside","impact","editorial","featured","reviews","recent","guides"];
    else if(/^extra(?:-\d+)?\.html$/.test(filename))order=["editorial","featured","impact","inside","reviews","recent","guides"];
    else order=["featured","editorial","impact","inside","reviews","recent","guides"];

    const context=editorialContext(main,filename);
    const topicByKey={featured:"news",recent:"news",impact:"tech",inside:"gaming",
                      reviews:"reviews",guides:"guides"};
    // The mixed Dalla redazione pool must pass the same filter as every box.
    order=order.filter(key=>key==="editorial"||topicByKey[key]!==context.topic);

    const create=(tag,cls)=>{
      const node=document.createElement(tag);
      if(cls)node.className=cls;
      return node;
    };
    function kicker(item){
      if(/^\/tech-impact-/.test(item.url))return "TECH IMPACT";
      if(/^\/gaming-inside-/.test(item.url))return "GAMING INSIDE";
      if(/^\/(?:guida-)/.test(item.url))return "GUIDE";
      if(/^\/(?:recensione-|.*-recensione-)/.test(item.url))return "RECENSIONE";
      return "NEWS";
    }
    function card(item){
      const article=create("article","zt-special-item");
      const photo=create("a","zt-special-thumb");
      photo.href=item.url;photo.setAttribute("aria-label",item.title);
      const image=create("img");
      image.src=item.image;image.alt=item.title;image.loading="lazy";image.decoding="async";
      photo.append(image);
      const category=create("div","zt-story-kicker");
      category.textContent=kicker(item);
      const heading=create("h3");
      const link=create("a");link.href=item.url;link.textContent=item.title;
      heading.append(link);
      article.append(photo,category,heading);
      return article;
    }
    function module(key){
      const [label,group,url]=selected[key];
      const section=create("section","zt-special-box zt-editorial-large-box");
      section.setAttribute("aria-label",label);
      const header=create("header","zt-special-head");
      const title=create("h2");title.textContent=label.toUpperCase();
      const see=create("a");see.href=url;see.textContent="VEDI →";
      header.append(title,see);
      const list=create("div","zt-special-list");
      const footer=create("footer","zt-special-footer");
      const all=create("a");all.href=url;all.textContent="TUTTI GLI ARTICOLI →";
      footer.append(all);
      section.append(header,list,footer);
      return {key,group,section,list};
    }
    function targetAndMode(){
      const a=aside.getBoundingClientRect(),b=main.getBoundingClientRect();
      const desktop=b.width>0 && a.width>0 && a.left>=b.right-5 &&
        a.top < b.bottom-60 && a.left-b.right<150;
      // Community banner is the exact requested stopping point. On pages
      // without it use the bottom of the editorial content column.
      const community=main.querySelector(".zt-community-banner");
      const edge=community?community.getBoundingClientRect().bottom:b.bottom;
      return {desktop,target:Math.round(edge-a.top)-7};
    }
    // No text, metadata, related articles, Home layout or Amazon content edited.
    function fit(){
      const mode=targetAndMode();
      // On a stacked mobile page the sidebar starts AFTER the editorial
      // content, so height matching is neither possible nor appropriate.
      if(mode.desktop && mode.target<540){
        // No room for a full-size picture: keep only the Amazon partner.
        aside.replaceChildren(...[...aside.children].filter(x=>x.classList?.contains("zt-amazon-partner")));
        aside.removeAttribute("data-zt-large-editorial");
        return true;
      }
      const usedLinks=new Set([path]);
      const pool={};
      for(const key of order){
        const group=selected[key][1];
        const all=(Array.isArray(feed[group])?feed[group]:[])
          .filter(item=>eligibleDiscovery(item,context));
        const unique=[];const seen=new Set();
        for(const item of all)if(!seen.has(item.url)){
          seen.add(item.url);unique.push(item);
        }
        // Preserve original publication ranking while removing duplicates.
        pool[key]=unique;
      }
      function next(key){
        return pool[key].find(item=>!usedLinks.has(item.url))||null;
      }
      const height=()=>Math.ceil(aside.getBoundingClientRect().height);
      const aim=mode.desktop?mode.target:Infinity;
      const records=[];
      const first=order.find(key=>next(key));
      if(!first){
        aside.replaceChildren(...(affiliate?[affiliate]:[]),...kept);
        aside.removeAttribute("data-zt-large-editorial");
        return true;
      }
      const start=module(first);
      const initial=next(first);
      start.list.append(card(initial));
      usedLinks.add(initial.url);
      aside.dataset.ztLargeEditorial="three-cards";
      aside.replaceChildren(start.section,...(affiliate?[affiliate]:[]),...kept);
      records.push(start);
      if(height()>aim+3){
        // Preserve only the already-verified, cross-category item.
        aside.dataset.ztAdaptiveRail="minimal-cross-category";
        return true;
      }
      if(!mode.desktop){
        for(const key of order){
          if(records.length>=2)break;
          if(key===first)continue;
          const item=next(key);if(!item)continue;
          const record=module(key);
          record.list.append(card(item));
          usedLinks.add(item.url);
          aside.append(record.section);
          records.push(record);
        }
        for(const r of records){
          while(r.list.children.length<3){
            const item=next(r.key);if(!item)break;
            r.list.append(card(item));usedLinks.add(item.url);
          }
        }
        return true;
      }
      const targetModules=Math.min(order.length,Math.max(1,Math.round(aim/1120)));
      // Populate a modest number of unique headings, then enlarge THEIR
      // picture stacks instead of duplicating a heading further down.
      for(const key of order){
        if(records.length>=targetModules)break;
        if(records.some(r=>r.key===key))continue;
        const item=next(key);if(!item)continue;
        const r=module(key);
        r.list.append(card(item));
        aside.append(r.section);
        if(height()<=aim-6){
          usedLinks.add(item.url);records.push(r);
        }else r.section.remove();
      }
      // Raise every chosen section to two pictures if it actually fits.
      for(const r of records){
        const item=next(r.key);if(!item)continue;
        const entry=card(item);r.list.append(entry);
        if(height()<=aim-5)usedLinks.add(item.url);
        else entry.remove();
      }
      let rounds=0;
      while(rounds++<115){
        const free=aim-height();
        if(free<35)break;
        const proposals=[];
        for(const r of records){
          if(r.list.children.length>=13)continue;
          const item=next(r.key);if(!item)continue;
          const entry=card(item);
          r.list.append(entry);
          const cost=height()-(aim-free);
          entry.remove();
          if(cost>0 && cost<=free-4){
            proposals.push({r,item,cost,score:r.list.children.length*140+Math.abs(free-cost)*.14});
          }
        }
        if(!proposals.length){
          // A long article may need another DISTINCT section if existing
          // pools run out. Repeated category headings are never permitted.
          let added=false;
          for(const key of order){
            if(records.some(r=>r.key===key))continue;
            const item=next(key);if(!item)continue;
            const r=module(key);
            r.list.append(card(item));
            aside.append(r.section);
            if(height()<=aim-6){
              records.push(r);usedLinks.add(item.url);added=true;break;
            }
            r.section.remove();
          }
          if(!added)break;
          continue;
        }
        proposals.sort((a,b)=>a.score-b.score);
        const pick=proposals[0];
        pick.r.list.append(card(pick.item));usedLinks.add(pick.item.url);
      }
      // Small leftover gaps are shared as breathing room between real
      // thumbnails, never empty boxes or stretched/distorted images.
      const extra=aim-height();
      const cards=[...aside.querySelectorAll(".zt-editorial-large-box .zt-special-item")];
      if(extra>3 && cards.length){
        const padding=Math.min(20,Math.floor(extra/(cards.length*2)));
        if(padding>0)for(const entry of cards)
          entry.style.setProperty("--zt-rail-extra-pad",padding+"px");
      }
      // Ultimate guard against a late geometry change: end AT or just above
      // the black Community banner. No blank filler blocks below it.
      let n=0;
      while(height()>aim+3 && n++<30){
        const last=[...records].reverse().find(r=>r.list.children.length>1);
        if(last){last.list.lastElementChild.remove();continue;}
        if(records.length>1){records.pop().section.remove();continue;}
        break;
      }
      aside.dataset.ztAdaptiveRail="community-bottom";
      return true;
    }
    let pending=false;
    function queueFit(){
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;fit();});
    }
    fit();
    window.addEventListener("load",queueFit,{once:true});
    window.addEventListener("resize",queueFit,{passive:true});
    if(typeof ResizeObserver==="function"){
      const observe=new ResizeObserver(queueFit);
      observe.observe(main);
    }
    return true;
  }

  function apply(feed){
    if(!feed || !Array.isArray(feed.news)|| !Array.isArray(feed.reviews))return;
    const asides=document.querySelectorAll("aside.zt-side-mix, aside.sidebar");
    for(const aside of asides){
      if(upgradeEditorialRail(aside,feed)){
        aside.dataset.ztSidebarLive="24h";
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
      aside.dataset.ztSidebarLive="24h";
    }
  }
  if(!document.querySelector("aside.zt-side-mix, aside.sidebar"))return;
  if(typeof fetch!=="function")return;
  fetch("/zt-sidebar-feed.json",{cache:"no-store",credentials:"omit"})
    .then(response=>response.ok?response.json():null)
    .then(apply)
    .catch(()=>{/* Keep valid server-rendered SEO content on network errors. */});
})();