(function(){
  'use strict';
  const root=document.querySelector('[data-zt-comments]');
  if(!root) return;

  const contentId=root.dataset.contentId||location.pathname.replace(/^\//,'');
  const contentType=root.dataset.contentType||'content';
  const API='/api/comments';
  let replyTo=null;
  let comments=[];

  const $=(sel)=>root.querySelector(sel);
  const esc=(s)=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const initials=(name)=>{
    const p=String(name||'Utente').trim().split(/\s+/).filter(Boolean);
    return ((p[0]?.[0]||'U')+(p[1]?.[0]||'')).toUpperCase().slice(0,2);
  };
  const fmtDate=(iso)=>{
    if(!iso) return '';
    const d=new Date(iso);
    if(Number.isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat('it-IT',{dateStyle:'medium',timeStyle:'short'}).format(d);
  };
  const tokenKey=(id)=>'zt_comment_delete_'+id;
  const ownToken=(id)=>{try{return localStorage.getItem(tokenKey(id))||''}catch(_){return ''}};
  const saveToken=(id,token)=>{try{localStorage.setItem(tokenKey(id),token)}catch(_){}};
  const removeToken=(id)=>{try{localStorage.removeItem(tokenKey(id))}catch(_){}};

  function setStatus(msg,type){
    const el=$('.zt-comment-status');
    if(!el) return;
    el.textContent=msg||'';
    el.className='zt-comment-status'+(type?' '+type:'');
  }

  function commentHtml(c,isReply){
    const own=!!ownToken(c.id);
    const tools=[
      !isReply?'<button type="button" data-reply="'+esc(c.id)+'" data-name="'+esc(c.displayName)+'">Rispondi</button>':'',
      '<button type="button" data-report="'+esc(c.id)+'">Segnala</button>',
      own?'<button type="button" data-delete="'+esc(c.id)+'">Elimina</button>':''
    ].join('');
    return '<article class="zt-comment" id="comment-'+esc(c.id)+'">'+
      '<div class="zt-comment-avatar" aria-hidden="true">'+esc(initials(c.displayName))+'</div>'+
      '<div><div class="zt-comment-meta"><span class="zt-comment-name">'+esc(c.displayName)+'</span><span class="zt-comment-date">'+esc(fmtDate(c.createdAt))+'</span></div>'+
      '<div class="zt-comment-text">'+esc(c.text)+'</div>'+
      '<div class="zt-comment-tools">'+tools+'</div></div>'+
      (isReply?'':'<div class="zt-comment-replies" data-replies="'+esc(c.id)+'"></div>')+
      '</article>';
  }

  function render(){
    const list=$('.zt-comments-list');
    const count=$('.zt-comments-count');
    if(!list) return;
    const roots=comments.filter(c=>!c.parentId);
    const replies=comments.filter(c=>c.parentId);
    count.textContent=comments.length===1?'1 commento':comments.length+' commenti';
    if(!comments.length){
      list.innerHTML='<div class="zt-comments-empty">Ancora nessun commento. Puoi essere il primo.</div>';
      return;
    }
    list.innerHTML=roots.map(c=>commentHtml(c,false)).join('');
    replies.forEach(c=>{
      const host=list.querySelector('[data-replies="'+CSS.escape(c.parentId)+'"]');
      if(host) host.insertAdjacentHTML('beforeend',commentHtml(c,true));
    });
  }

  async function load(){
    const list=$('.zt-comments-list');
    if(list) list.innerHTML='<div class="zt-comment-loading">Caricamento commenti…</div>';
    try{
      const res=await fetch(API+'?contentId='+encodeURIComponent(contentId),{headers:{'Accept':'application/json'},cache:'no-store'});
      if(!res.ok) throw new Error('load');
      const data=await res.json();
      comments=Array.isArray(data.comments)?data.comments:[];
      render();
    }catch(_){
      if(list) list.innerHTML='<div class="zt-comments-empty">Commenti temporaneamente non disponibili.</div>';
    }
  }

  function startReply(id,name){
    replyTo=id;
    const box=$('.zt-replying');
    if(box){
      box.classList.add('show');
      box.querySelector('span').textContent='Risposta a '+name;
    }
    const ta=$('textarea[name="comment"]');
    if(ta){ta.focus();ta.scrollIntoView({behavior:'smooth',block:'center'});}
  }
  function cancelReply(){
    replyTo=null;
    const box=$('.zt-replying');
    if(box) box.classList.remove('show');
  }

  async function submitForm(e){
    e.preventDefault();
    const form=e.currentTarget;
    const btn=form.querySelector('.zt-comment-submit');
    const fd=new FormData(form);
    const displayName=String(fd.get('displayName')||'').trim();
    const text=String(fd.get('comment')||'').trim();
    const age=fd.get('age14')==='on';
    const consent=fd.get('consent')==='on';
    const website=String(fd.get('website')||'');

    if(!age||!consent){setStatus('Per pubblicare devi confermare età minima e regole/privacy.','err');return;}
    if(displayName.length<2||displayName.length>40){setStatus('Usa un nome o nickname tra 2 e 40 caratteri.','err');return;}
    if(text.length<3||text.length>1200){setStatus('Il commento deve contenere da 3 a 1200 caratteri.','err');return;}

    btn.disabled=true; setStatus('Invio e controllo automatico in corso…');
    try{
      const res=await fetch(API,{
        method:'POST',
        headers:{'Content-Type':'application/json','Accept':'application/json'},
        body:JSON.stringify({action:'submit',contentId,contentType,displayName,text,parentId:replyTo,acceptedRules:true,age14:true,website})
      });
      const data=await res.json().catch(()=>({}));
      if(!res.ok){
        setStatus(data.message||'Commento non inviato. Riprova più tardi.','err');
        return;
      }
      if(data.status==='approved'){
        if(data.id&&data.deleteToken) saveToken(data.id,data.deleteToken);
        form.reset(); cancelReply();
        setStatus('Commento pubblicato.','ok');
        await load();
      }else{
        setStatus(data.message||'Il commento non può essere pubblicato in questa forma.','err');
      }
    }catch(_){
      setStatus('Servizio commenti temporaneamente non disponibile.','err');
    }finally{btn.disabled=false;}
  }

  async function reportComment(id){
    const reason=prompt('Motivo della segnalazione (es. dati personali, minaccia, contenuto illecito, spam):');
    if(!reason) return;
    try{
      const res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'report',contentId,commentId:id,reason:String(reason).slice(0,300)})});
      const data=await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data.message||'report');
      setStatus('Segnalazione ricevuta. Il commento è stato nascosto in via prudenziale.','ok');
      await load();
    }catch(_){setStatus('Impossibile inviare la segnalazione in questo momento.','err');}
  }

  async function deleteComment(id){
    const token=ownToken(id);
    if(!token) return;
    if(!confirm('Eliminare definitivamente il tuo commento?')) return;
    try{
      const res=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'delete',contentId,commentId:id,deleteToken:token})});
      const data=await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(data.message||'delete');
      removeToken(id);
      setStatus('Commento eliminato.','ok');
      await load();
    }catch(_){setStatus('Non è stato possibile eliminare il commento.','err');}
  }

  root.addEventListener('click',(e)=>{
    const reply=e.target.closest('[data-reply]');
    if(reply){startReply(reply.dataset.reply,reply.dataset.name||'utente');return;}
    const report=e.target.closest('[data-report]');
    if(report){reportComment(report.dataset.report);return;}
    const del=e.target.closest('[data-delete]');
    if(del){deleteComment(del.dataset.delete);return;}
    if(e.target.closest('.zt-reply-cancel')) cancelReply();
  });

  const form=$('.zt-comment-form');
  if(form) form.addEventListener('submit',submitForm);
  load();
})();