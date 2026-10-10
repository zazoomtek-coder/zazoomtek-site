/* Progressive visual polish; does not replace the original editorial content. */
(function(){
 'use strict';
 function enhanceHomeSlider(){
  document.querySelectorAll('.news-slide').forEach(function(slide){
   if(slide.querySelector('.zt-slide-overlay,.news-slide-copy'))return;
   var img=slide.querySelector('img[alt]');
   if(!img || !img.alt.trim())return;
   var holder=slide.querySelector('a')||slide;
   var box=document.createElement('div');box.className='zt-slide-overlay';
   var label=document.createElement('span');label.className='zt-kicker';label.textContent='IN EVIDENZA';
   var title=document.createElement('h3');title.textContent=img.alt;
   var cta=document.createElement('span');cta.className='zt-slide-read';cta.textContent='Leggi la notizia completa ›';
   box.append(label,title,cta);
   holder.appendChild(box);
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',enhanceHomeSlider,{once:true});else enhanceHomeSlider();
})();
