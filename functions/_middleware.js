/**
 * Canonical URL enforcement for ZazoomTek.
 * Combine host, scheme, .html and category trailing-slash normalization in one 301.
 * Historical Community paths retain their exact path component.
 */
const LEGACY_COMMUNITY = /^\/community-[a-z0-9]+(?:-[a-z0-9]+)*$/i;
const CATEGORY_ROUTE = /^\/(?:recensioni|news|speciali|guide|extra)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)?\/$/i;

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const original = url.toString();
  const legacyCommunity = LEGACY_COMMUNITY.test(url.pathname.replace(/\/$/, ""));

  if (url.hostname.toLowerCase() === "www.zazoomtek.it") {
    url.hostname = "zazoomtek.it";
  }

  if (url.hostname.toLowerCase() === "zazoomtek.it") {
    url.protocol = "https:";

    if (!legacyCommunity) {
      if (url.pathname.toLowerCase().endsWith(".html")) {
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
