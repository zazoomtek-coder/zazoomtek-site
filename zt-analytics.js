(function(){
  'use strict';

  var ID='G-01F6Q4BGTC';
  var KEY='zt_analytics_consent';
  var loaded=false;

  function readConsent(){
    try{return localStorage.getItem(KEY);}catch(e){return null;}
  }

  function saveConsent(value){
    try{localStorage.setItem(KEY,value);}catch(e){}
  }

  function loadGA4(){
    if(loaded) return;
    loaded=true;
    window.dataLayer=window.dataLayer||[];
    window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
    window.gtag('js',new Date());
    window.gtag('config',ID,{
      anonymize_ip:true,
      allow_google_signals:false,
      allow_ad_personalization_signals:false
    });
    var s=document.createElement('script');
    s.async=true;
    s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(ID);
    document.head.appendChild(s);
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

  function choose(value){
    saveConsent(value);
    removeBanner();
    showSettingsButton();
    if(value==='granted') loadGA4();
  }

  function showBanner(){
    css();
    removeBanner();
    var box=document.createElement('div');
    box.id='zt-consent';
    box.setAttribute('role','dialog');
    box.setAttribute('aria-label','Preferenze cookie');
    box.innerHTML=
      '<p><strong>ZazoomTek utilizza cookie e tecnologie simili per misurare il traffico e migliorare i contenuti. Puoi accettare o rifiutare.</strong></p>'+
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

  window.ZazoomTekCookieSettings=function(){showBanner();};
})();