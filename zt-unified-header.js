(function(){
'use strict';
if(document.querySelector('.ticker-video-links'))return;
function mount(){
 var old=document.querySelector('body > header, header.zt-header, header.site-header');
 if(!old||document.getElementById('zt-unified-header'))return;
 fetch('/?zt_header=1',{credentials:'same-origin'}).then(function(r){if(!r.ok)throw Error('Home header unavailable');return r.text()}).then(function(html){
  var doc=new DOMParser().parseFromString(html,'text/html');
  var source=doc.querySelector('body > header');
  if(!source||!source.querySelector('.ticker-video-links'))throw Error('Home header incomplete');
  var node=document.createElement('div');node.id='zt-unified-header';node.innerHTML=source.innerHTML;
  var ticker=node.querySelector('#tickerTrack');if(ticker)ticker.removeAttribute('id');
  node.querySelectorAll('a[href]').forEach(function(a){var href=a.getAttribute('href');if(href&&!href.startsWith('/')&&!href.startsWith('#')&&!/^(https?:|mailto:)/.test(href))a.setAttribute('href','/'+href)});
  var logo=node.querySelector('img.brand-logo-img');if(logo)logo.src='/ChatGPT.png';
  var current=location.pathname.replace(/\\/$/,'')||'/';
  node.querySelectorAll('nav.nav a').forEach(function(a){a.classList.remove('active');a.removeAttribute('aria-current');if(new URL(a.href,location.href).pathname===current){a.classList.add('active');a.setAttribute('aria-current','page')}});
  var existingStrip=old.nextElementSibling;
  if(existingStrip&&existingStrip.matches('.zt-strip,.ticker,.news-ticker,.zt-news-strip'))existingStrip.remove();
  old.replaceWith(node);
  var items=[].slice.call(node.querySelectorAll('.ticker-track a'));var index=items.findIndex(function(a){return a.classList.contains('active')});if(index<0)index=0;
  if(items.length>1)setInterval(function(){items[index].classList.remove('active');index=(index+1)%items.length;items[index].classList.add('active')},4500);
 }).catch(function(e){console.warn('ZazoomTek shared header: original header preserved',e)});
}
var style=document.createElement('style');style.textContent=`
#zt-unified-header{background:#171717;color:#fff;border-top:3px solid #d51232;font:14px Arial,Helvetica,sans-serif}
#zt-unified-header *{box-sizing:border-box}
#zt-unified-header a{text-decoration:none;color:inherit}
#zt-unified-header .shell{width:min(1460px,calc(100% - 28px));margin:auto}
#zt-unified-header .topbar{min-height:78px;display:grid;grid-template-columns:auto minmax(0,1fr) minmax(220px,360px);align-items:stretch}
#zt-unified-header .brand{display:flex;align-items:center;gap:10px;padding:10px 20px 10px 0;border-right:1px solid #333;white-space:nowrap}
#zt-unified-header .brand-logo-img{width:52px;height:52px;object-fit:cover;border-radius:8px}
#zt-unified-header .brand-copy strong,#zt-unified-header .zt-wordmark{display:block;font-weight:900;font-size:1.7rem;letter-spacing:.01em}
#zt-unified-header .zt-mark-blue{color:#51affc}#zt-unified-header .zt-mark-red{color:#e52551}
#zt-unified-header .brand-copy small,#zt-unified-header .zt-brand-tagline{display:block;color:#aaa;font-size:.66rem;margin-top:3px}
#zt-unified-header .nav{display:flex;align-items:stretch;flex-wrap:wrap;min-width:0}
#zt-unified-header .nav a{display:flex;align-items:center;padding:0 clamp(9px,1vw,20px);font-size:.82rem;font-weight:800;text-transform:uppercase;border-right:1px solid #303030}
#zt-unified-header .nav a:hover,#zt-unified-header .nav a.active{background:#d51232;color:#fff}
#zt-unified-header .search-wrap{display:flex;flex-direction:column;justify-content:center;padding-left:16px}
#zt-unified-header .search-box{display:flex;width:100%;background:#303030;border:1px solid #444}
#zt-unified-header .search-box input{min-width:0;flex:1;width:100%;background:transparent;border:0;color:#fff;padding:12px 14px}
#zt-unified-header .search-box button{width:48px;border:0;background:#d51232;color:#fff;cursor:pointer}
#zt-unified-header .top-socials{display:flex;justify-content:flex-end;gap:10px;margin-top:8px}
#zt-unified-header .top-socials a{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;background:#181818;border:1px solid #353535}
#zt-unified-header .top-socials img{display:block;width:27px;height:27px;object-fit:contain}
#zt-unified-header .ticker{background:#222;border-top:1px solid #2c2c2c}
#zt-unified-header .ticker-inner{display:flex;align-items:center;min-height:46px;overflow:hidden}
#zt-unified-header .ticker-label{background:#d51232;font-weight:900;padding:14px 20px;white-space:nowrap}
#zt-unified-header .ticker-track{position:relative;flex:1;min-width:0;height:46px;overflow:hidden}
#zt-unified-header .ticker-track a{position:absolute;inset:0;display:flex;align-items:center;padding:0 16px;opacity:0;transform:translateY(12px);transition:.35s;color:#ddd;font-size:.86rem}
#zt-unified-header .ticker-track a.active{opacity:1;transform:none}
#zt-unified-header .ticker-video-links{flex:0 0 auto;width:max-content;max-width:calc(100% - 220px);min-width:0;height:46px;display:flex;align-items:center;justify-content:flex-end;gap:22px;margin-left:auto;padding:0;white-space:nowrap}
#zt-unified-header .ticker-video-links a{display:flex;align-items:center;justify-content:center;height:46px;padding:0 2px;color:#fff;font-size:clamp(.82rem,.95vw,.96rem);font-weight:900;letter-spacing:.015em;text-transform:uppercase;text-shadow:0 0 2px rgba(255,255,255,.54),0 0 9px rgba(255,255,255,.27)}
#zt-unified-header .ticker-video-links a:hover,#zt-unified-header .ticker-video-links a:focus-visible{color:#d51232;text-shadow:0 0 7px rgba(213,18,50,.5)}
@media(max-width:1240px){#zt-unified-header .topbar{grid-template-columns:auto 1fr}#zt-unified-header .search-wrap{grid-column:1/-1;padding:8px 0 10px}#zt-unified-header .ticker-inner{flex-wrap:wrap}#zt-unified-header .ticker-video-links{flex:0 0 100%;max-width:100%;justify-content:flex-end;border-top:1px solid #303030;padding:0 8px;gap:clamp(12px,2vw,24px)}#zt-unified-header .ticker-video-links a{font-size:clamp(.76rem,1.35vw,.96rem)}}
@media(max-width:650px){#zt-unified-header .topbar{display:block}#zt-unified-header .nav{overflow-x:auto;flex-wrap:nowrap}#zt-unified-header .nav a{white-space:nowrap;min-height:40px}#zt-unified-header .ticker-video-links{justify-content:flex-start;overflow-x:auto;gap:20px}#zt-unified-header .ticker-video-links a{font-size:.88rem}#zt-unified-header .brand{border-right:0}}
`;document.head.appendChild(style);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();