(function(){
  'use strict';

  // First-party aggregate statistic, independent from consented GA4.
  // No visitor identifier, cookies, IP, fingerprint, query string or referrer
  // is included in the payload; no persistent browser storage is written.
  (function countAnonymousPageView(){
    if(window.__ztAggregateViewSent)return;
    var page=window.location.pathname||'/';
    if(page!=='/'&&page.slice(-5).toLowerCase()!=='.html')return;
    if(window.navigator&&window.navigator.webdriver)return;
    window.__ztAggregateViewSent=true;
    try{
      if(typeof window.fetch==='function'){
        window.fetch('/api/traffic',{
          method:'POST',
          mode:'same-origin',
          credentials:'omit',
          referrerPolicy:'no-referrer',
          cache:'no-store',
          keepalive:true,
          headers:{'Content-Type':'text/plain;charset=UTF-8'},
          body:JSON.stringify({page:page})
        }).catch(function(){});
      }
    }catch(e){}
  })();


  var ID='G-01F6Q4BGTC';
  var KEY='zt_analytics_consent';
  var DATE_KEY='zt_analytics_consent_at';
  var CONSENT_DAYS=185; // at least six calendar months
  var CONSENT_MS=CONSENT_DAYS*24*60*60*1000;
  var loaded=false;

  function validChoice(value){
    return value==='granted'||value==='denied';
  }

  // Technical first-party cookie: remembers only whether Analytics was
  // accepted or refused. Shared between zazoomtek.it and www.zazoomtek.it.
  function readConsentCookie(){
    var parts=document.cookie.split(';');
    for(var i=0;i<parts.length;i++){
      var part=parts[i].trim();
      if(part.indexOf(KEY+'=')===0){
        var value=part.slice(KEY.length+1);
        return validChoice(value)?value:null;
      }
    }
    return null;
  }

  function writeConsentCookie(value){
    if(!validChoice(value)) return;
    var attrs=[
      KEY+'='+value,
      'Max-Age='+(CONSENT_DAYS*24*60*60),
      'Path=/',
      'SameSite=Lax'
    ];
    if(location.protocol==='https:') attrs.push('Secure');
    if(location.hostname==='zazoomtek.it'||location.hostname==='www.zazoomtek.it'){
      attrs.push('Domain=.zazoomtek.it');
    }
    document.cookie=attrs.join('; ');
  }

  function readConsent(){
    var fromCookie=readConsentCookie();
    var fromStorage=null;
    try{
      var value=localStorage.getItem(KEY);
      if(validChoice(value)){
        var stamp=Number(localStorage.getItem(DATE_KEY));
        // Existing preferences used this key without a timestamp.
        // Honour them, assigning a date rather than reopening the banner.
        if(!stamp||!Number.isFinite(stamp)||stamp>Date.now()){
          stamp=Date.now();
          localStorage.setItem(DATE_KEY,String(stamp));
        }
        if(Date.now()-stamp<CONSENT_MS){
          fromStorage=value;
        }else{
          localStorage.removeItem(KEY);
          localStorage.removeItem(DATE_KEY);
        }
      }
    }catch(e){}
    if(fromCookie){
      // The shared cookie is authoritative if the decision changed
      // on the other subdomain and localStorage still holds an older choice.
      if(fromStorage!==fromCookie){
        try{
          localStorage.setItem(KEY,fromCookie);
          localStorage.setItem(DATE_KEY,String(Date.now()));
        }catch(e){}
      }
      return fromCookie;
    }
    if(fromStorage){
      writeConsentCookie(fromStorage);
      return fromStorage;
    }
    return null;
  }

  function saveConsent(value){
    if(!validChoice(value)) return;
    try{
      localStorage.setItem(KEY,value);
      localStorage.setItem(DATE_KEY,String(Date.now()));
    }catch(e){}
    writeConsentCookie(value);
  }

  // Basic consent mode: NEVER contact GA4 until the visitor has accepted.
  // The separate first-party aggregate counter does not depend on this choice.
  function loadGA4(){
    if(loaded)return;
    loaded=true;
    window.dataLayer=window.dataLayer||[];
    window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
    window.gtag('consent','default',{
      analytics_storage:'denied',
      ad_storage:'denied',
      ad_user_data:'denied',
      ad_personalization:'denied'
    });
    window.gtag('consent','update',{analytics_storage:'granted'});
    window.gtag('js',new Date());
    window.gtag('config',ID,{
      send_page_view:true,
      anonymize_ip:true,
      allow_google_signals:false,
      allow_ad_personalization_signals:false
    });
    var script=document.createElement('script');
    script.async=true;
    script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(ID);
    document.head.appendChild(script);
  }

  function css(){
    if(document.getElementById('zt-consent-style')) return;
    var s=document.createElement('style');
    s.id='zt-consent-style';
    s.textContent=
      '#zt-consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:2147483000;max-width:900px;margin:auto;background:#171717;color:#fff;border:1px solid #3a3a3a;border-top:4px solid #d51232;box-shadow:0 12px 38px rgba(0,0,0,.38);padding:18px 20px;font:14px/1.45 Arial,Helvetica,sans-serif}'+
      '#zt-consent strong{display:block;font-size:16px;margin-bottom:6px}#zt-consent p{margin:0 0 12px;color:#e4e4e4}'+
      '#zt-consent a{color:#fff;text-decoration:underline}#zt-consent .zt-actions{display:flex;gap:9px;flex-wrap:wrap}'+
      '#zt-consent button{border:0;padding:10px 16px;font-weight:800;cursor:pointer;border-radius:3px}'+
      '#zt-consent .zt-accept{background:#d51232;color:#fff}#zt-consent .zt-reject{background:#3b3b3b;color:#fff}'+
      '#zt-cookie-settings{position:fixed;left:10px;bottom:10px;z-index:2147482990;border:1px solid #bbb;background:#fff;color:#222;border-radius:4px;padding:6px 9px;font:700 11px Arial,Helvetica,sans-serif;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15)}'+
      '@media(max-width:600px){#zt-consent{left:8px;right:8px;bottom:8px;padding:15px}#zt-consent button{flex:1}}';
    document.head.appendChild(s);
  }

  function removeBanner(){
    var b=document.getElementById('zt-consent');
    if(b) b.remove();
  }

  function showSettingsButton(){
    if(document.getElementById('zt-cookie-settings')) return;
    var b=document.createElement('button');
    b.id='zt-cookie-settings';
    b.type='button';
    b.textContent='Cookie';
    b.setAttribute('aria-label','Gestisci preferenze cookie');
    b.addEventListener('click',function(){
      removeBanner();
      showBanner();
    });
    document.body.appendChild(b);
  }

  function clearAnalyticsCookies(){
    // When an existing acceptance is revoked, expire first-party GA cookies.
    try{
      document.cookie.split(';').forEach(function(pair){
        var name=pair.trim().split('=')[0];
        if(!/^_ga(?:_|$)|^_gid$|^_gat(?:_|$)/.test(name))return;
        document.cookie=name+'=;Max-Age=0;Path=/;SameSite=Lax';
        if(location.hostname==='zazoomtek.it'||location.hostname==='www.zazoomtek.it'){
          document.cookie=name+'=;Max-Age=0;Path=/;Domain=.zazoomtek.it;SameSite=Lax';
        }
      });
    }catch(e){}
  }

  function choose(value){
    if(!validChoice(value))return;
    var previouslyAccepted=readConsent()==='granted';
    saveConsent(value);
    removeBanner();
    showSettingsButton();
    if(value==='granted'){
      loadGA4();
    }else if(previouslyAccepted){
      if(loaded&&typeof window.gtag==='function'){
        window.gtag('consent','update',{analytics_storage:'denied'});
      }
      clearAnalyticsCookies();
      window.location.reload();
    }
  }

  function showBanner(){
    css();
    removeBanner();
    var box=document.createElement('div');
    box.id='zt-consent';
    box.setAttribute('role','dialog');
    box.setAttribute('aria-label','Preferenze cookie');
    box.innerHTML=
      '<p><strong>ZazoomTek utilizza Google Analytics solo se premi ACCETTA. Senza cookie di tracciamento, il sito conta separatamente le visualizzazioni complessive delle pagine a fini statistici. Puoi accettare o rifiutare.</strong></p>'+
      '<p><a href="/cookie.html">Cookie Policy</a></p>'+
      '<div class="zt-actions"><button type="button" class="zt-accept">ACCETTA</button><button type="button" class="zt-reject">RIFIUTA</button></div>';
    box.querySelector('.zt-accept').addEventListener('click',function(){choose('granted');});
    box.querySelector('.zt-reject').addEventListener('click',function(){choose('denied');});
    document.body.appendChild(box);
  }

  function init(){
    css();
    var consent=readConsent();
    if(consent==='granted'){
      loadGA4();
      showSettingsButton();
    }else if(consent==='denied'){
      showSettingsButton();
    }else{
      showBanner();
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',init,{once:true});
  }else{
    init();
  }

  // Banners for review articles are navigation links, not video embeds.
  // Load them independently of analytics consent and only on review pages.
  (function loadReviewVideoLinks(){
    var filename=(window.location.pathname.split('/').pop()||'');
    if(!/(?:^|[-_])(?:recensione|review)(?:[-_.]|$)/i.test(filename)) return;
    var bannerScript=document.createElement('script');
    bannerScript.src='/zt-review-video.js?v=20261012';
    bannerScript.defer=true;
    bannerScript.setAttribute('data-zt-review-video','1');
    document.head.appendChild(bannerScript);
  })();

  window.ZazoomTekCookieSettings=function(){showBanner();};
})();