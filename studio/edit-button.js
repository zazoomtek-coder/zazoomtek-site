/* ZazoomTek Studio: quick editing for all supported page layouts and article cards.
   UI visibility is a browser convenience, not authorization: writes are checked
   by GitHub from the logged-in Studio and never use a public browser token. */
(() => {
  "use strict";
  function studioBrowser() {
    try {
      return Number(localStorage.getItem("zt_studio_verified_until") || 0) > Date.now()
        || !!localStorage.getItem("zazoomtek.studio.github.vault.v1");
    } catch (_) { return false; }
  }
  if (!studioBrowser()) return;

  const escPath = (raw) => {
    try {
      const u = new URL(raw, location.origin);
      if (u.origin !== location.origin) return null;
      const path = decodeURIComponent(u.pathname).replace(/^\/+/, "");
      if (!(/^[a-zA-Z0-9_.-]+\.html$/.test(path) || /^watch\/[a-zA-Z0-9_-]{11}\.html$/.test(path))
          || ["index.html", "studio.html"].includes(path)
          || path.includes("..")) return null;
      return path;
    } catch (_) { return null; }
  };
  const hrefFor = (file) => "/studio/?edit=" + encodeURIComponent(file);
  const design = "display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:7px 11px;background:#222;color:#fff;border-left:4px solid #d51232;text-decoration:none;font:800 12px/1.2 Arial,Helvetica,sans-serif;z-index:5";

  function installTitle() {
    const path = escPath(location.href);
    if (!path || document.getElementById("zt-studio-edit-title")) return;
    // Some review templates place H1 in main.content OUTSIDE article.article-main.
    const detail = document.querySelector("article.article-main,article.story,article.zt-main,article.zt-article,article.article-body,article.zt-watch-article,main.content article");
    if (!detail) return;
    const title = detail.querySelector("h1") ||
      document.querySelector("main.content h1, main.page h1, main h1");
    if (!title) return;
    const b = document.createElement("a");
    b.id = "zt-studio-edit-title";
    b.textContent = "✎ Modifica";
    b.href = hrefFor(path);
    b.style.cssText = design + ";margin:8px 0 16px";
    b.setAttribute("aria-label", "Modifica questo contenuto nello Studio");
    title.insertAdjacentElement("afterend", b);
  }

  function installCards() {
    // Card templates are often rendered after initial HTML by zt-home-live.js.
    const selectors = [
      ".ztp-primary-feed a[href]", ".ztp-news-area a[href]",
      ".zt-mix-editorial-row[href]", ".news-card a[href]",
      ".review-card a[href]", ".article-card a[href]",
      ".zt-card a[href]", ".ztp-card a[href]", ".zt-watch-list a[href]"
    ].join(",");
    document.querySelectorAll(selectors).forEach((a) => {
      if (a.dataset.ztEditChecked) return;
      a.dataset.ztEditChecked = "1";
      const path = escPath(a.href);
      if (!path) return; // External RSS publishers are linked, never editable.
      const card = a.closest(".news-card,.review-card,.article-card,.ztp-news-card,.ztp-card,.zt-card,.zt-mix-editorial-row,article,li");
      if (!card || card.querySelector(".zt-studio-card-edit")) return;
      const edit = document.createElement("a");
      edit.className = "zt-studio-card-edit";
      edit.href = hrefFor(path);
      edit.textContent = "✎ Modifica";
      edit.setAttribute("aria-label", "Modifica " + path + " nello Studio");
      edit.style.cssText = design + ";position:relative;font-size:10px;padding:5px 7px;margin:5px 0";
      card.append(edit);
    });
  }

  function activate() {
    installTitle();
    installCards();
  }
  let running = false;
  function schedule() {
    if (running) return;
    running = true;
    requestAnimationFrame(() => { running = false; activate(); });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", activate, { once: true });
  } else activate();
  const mount = document.querySelector("main") || document.body;
  if (mount && window.MutationObserver) {
    const observer = new MutationObserver(schedule);
    observer.observe(mount, { childList: true, subtree: true });
  }
})();