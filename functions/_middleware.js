/**
 * Canonical URL enforcement for ZazoomTek.
 * Host, scheme, .html and category slash normalization share one 301.
 * Historical Community permalinks retain their original path and slash form.
 */
const LEGACY_COMMUNITY = /^\/community-[a-z0-9]+(?:-[a-z0-9]+)*$/i;
const CATEGORY_ROUTE = /^\/(?:recensioni|news|speciali|guide|extra)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)?\/$/i;

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const original = url.toString();
  const legacyPath = url.pathname.replace(/\/$/, "");
  const legacyCommunity = LEGACY_COMMUNITY.test(legacyPath);

  if (url.hostname.toLowerCase() === "www.zazoomtek.it") {
    url.hostname = "zazoomtek.it";
  }

  if (url.hostname.toLowerCase() === "zazoomtek.it") {
    url.protocol = "https:";

    if (!legacyCommunity) {
      // Also handle the unusual /category/article.html/ spelling in this hop.
      if (/\.html\/$/i.test(url.pathname)) {
        url.pathname = url.pathname.slice(0, -1);
      }
      if (/\.html$/i.test(url.pathname)) {
        url.pathname = url.pathname.slice(0, -5);
        if (url.pathname.toLowerCase() === "/index") url.pathname = "/";
      }
      if (CATEGORY_ROUTE.test(url.pathname)) {
        url.pathname = url.pathname.slice(0, -1);
      }
    }

    if (url.toString() !== original) {
      return Response.redirect(url.toString(), 301);
    }
  }

  return context.next();
}
