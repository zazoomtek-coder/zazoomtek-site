/* ZazoomTek: pulsante videorecensione verso il video YouTube esatto.
   Regola: una recensione senza video verificato non mostra il box.
   Per le nuove recensioni aggiungere <meta name="zt-review-video-id" content="VIDEO_ID">
   oppure aggiornare la mappa qui sotto. Nessun link generico al canale. */
(function () {
  'use strict';
  var knownVideos = {
    'sesame-street-amici-e-risate-recensione-ps5.html': 'WwGAaKGfoGY',
    'recensione-Ugkx1MzCpfD6F193kzdDtyqQU2ErUHi6FEu1.html': 'fKiuvUW5eKI',
    'recensione-UgkxHri44VrpYrRtskxdyK_msdY_oNiaK4aj.html': '1PlHs05dqQQ',
    'recensione-UgkxPQVLBegGEPWvHmDjVq-rA5b8EwFeFrtk.html': 'RtHYQ7o5Gws',
    'recensione-UgkxUyzI3zn3urxvkpRPcd349swqkNqHFXEK.html': 'X5qvA6u5lvo',
    'recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html': 'XrXF0t5OPtU',
    'recensione-Ugkxq4wPsbAKxSo1aB0OptleaGIR5iyfIuyz.html': 'hp6JW2xqa9Y',
    'recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html': 'by7Qm_XFO8c'
  };

  function addStyle() {
    if (document.getElementById('zt-review-video-style')) return;
    var style = document.createElement('style');
    style.id = 'zt-review-video-style';
    style.textContent = [
      '.zt-review-video-banner{display:flex!important;align-items:center;justify-content:space-between;gap:14px;width:100%;min-height:84px;margin:14px 0 24px!important;padding:11px 15px;background:#f6f6f6!important;border:1px solid #ddd!important;border-top:5px solid #d51232!important;color:#171717!important;text-decoration:none!important;box-shadow:none;cursor:pointer}',
      '.zt-review-video-banner:hover{background:#ededed!important;border-color:#ccc!important;border-top-color:#bd102e!important}',
      '.zt-review-video-banner:focus-visible{outline:3px solid #207eea;outline-offset:3px}',
      '.zt-review-video-copy{display:flex;flex:1;min-width:0;align-items:center;gap:12px}',
      '.zt-review-video-glyph{flex-shrink:0;font:900 25px Arial,sans-serif;line-height:1;color:#171717}',
      '.zt-review-video-title{font:850 clamp(15px,2vw,23px)/1.2 Arial,Helvetica,sans-serif!important;letter-spacing:-.25px;color:#171717!important}',
      '.zt-review-video-thumb{display:block;position:relative;flex:0 0 clamp(95px,22%,145px);width:clamp(95px,22%,145px);aspect-ratio:16/9;overflow:hidden;background:#191919}',
      '.zt-review-video-thumb>img{display:block!important;width:100%!important;height:100%!important;object-fit:cover!important}',
      '.zt-review-video-play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);background:#f21817;color:white;border-radius:10px;padding:6px 16px;font:900 20px Arial,Helvetica,sans-serif;box-shadow:0 2px 8px #0005}',
      '@media(max-width:560px){.zt-review-video-banner{gap:8px;padding:9px 10px;min-height:66px}.zt-review-video-copy{gap:8px}.zt-review-video-glyph{font-size:20px}.zt-review-video-title{font-size:15px!important}.zt-review-video-thumb{flex-basis:90px;width:90px}.zt-review-video-play{font-size:15px;padding:5px 12px}}'
    ].join('');
    document.head.appendChild(style);
  }

  function init() {
    var file = window.location.pathname.split('/').pop();
    var pageMeta = document.querySelector('meta[name="zt-review-video-id"]');
    var declaredId = pageMeta ? pageMeta.getAttribute('content') : '';
    var videoId = (declaredId || knownVideos[file] || '').trim();
    if (!/^[A-Za-z0-9_-]{11}$/.test(videoId)) return;
    if (document.querySelector('.zt-review-video-banner')) return;
    var cover = document.querySelector('main img.article-hero, main img.hero, .content img.hero, article img.article-hero, article img.hero');
    if (!cover) return;
    var following = cover.nextElementSibling;
    var anchor = following && following.matches('.hero-caption, figcaption, small.hero-caption') ? following : cover;
    addStyle();

    var link = document.createElement('a');
    link.className = 'zt-review-video-banner';
    link.href = 'https://www.youtube.com/watch?v=' + encodeURIComponent(videoId);
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.setAttribute('aria-label', 'Guarda la nostra videorecensione su YouTube in una nuova scheda');

    var copy = document.createElement('span');
    copy.className = 'zt-review-video-copy';
    var glyph = document.createElement('span');
    glyph.className = 'zt-review-video-glyph';
    glyph.setAttribute('aria-hidden', 'true');
    glyph.textContent = '▶';
    var title = document.createElement('strong');
    title.className = 'zt-review-video-title';
    title.textContent = 'Guarda la nostra videorecensione';
    copy.appendChild(glyph);
    copy.appendChild(title);

    var thumb = document.createElement('span');
    thumb.className = 'zt-review-video-thumb';
    var image = document.createElement('img');
    image.src = cover.getAttribute('src') || cover.src;
    image.alt = '';
    image.loading = 'lazy';
    thumb.appendChild(image);
    var play = document.createElement('span');
    play.className = 'zt-review-video-play';
    play.setAttribute('aria-hidden', 'true');
    play.textContent = '▶';
    thumb.appendChild(play);
    link.appendChild(copy);
    link.appendChild(thumb);
    anchor.insertAdjacentElement('afterend', link);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
