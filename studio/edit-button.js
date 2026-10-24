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
  // Editing rights are enforced by Studio/GitHub, not by the visibility of
  // this navigation link. Showing Modifica does not grant write access.

  const escPath = (raw) => {
    try {
      const u = new URL(raw, location.origin);
      if (u.origin !== location.origin) return null;
      let path = decodeURIComponent(u.pathname).replace(/^\/+/, "").replace(/\/+$/, "");
      // Cloudflare Pages serves article.html as /article (pretty URL).
      // Studio still reads and writes the actual article.html GitHub file.
      if (path && !/\.[a-zA-Z0-9]+$/.test(path)) path += ".html";
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
    // Standard imported news have <main><h1>…</h1><div class="article-copy">,
    // without an <article> wrapper. Only treat these as editorial detail pages.
    const contentPage = !!document.querySelector("main .article-copy,main .article-body,main .zt-watch-article,main .hero,main .article-hero,main .lead");
    // All eligible interior HTML pages have a Studio editing entry point.
    // The Home and Studio remain protected by escPath above.
    const title = detail?.querySelector("h1") ||
      document.querySelector("main.content h1, main.page h1, main h1");
    if (!detail && !contentPage && !title) return;
    if (!title) return;
    const b = document.createElement("a");
    b.id = "zt-studio-edit-title";
    b.textContent = "✎ Modifica";
    b.href = hrefFor(path);
    b.style.cssText = design + ";margin:8px 0 16px";
    b.setAttribute("aria-label", "Modifica questo contenuto nello Studio");
    title.insertAdjacentElement("afterend", b);
  }

  function activate() {
    installTitle();
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