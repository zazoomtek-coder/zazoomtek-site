/**
 * Canonical URL enforcement for ZazoomTek.
 * Host, scheme, review aliases, .html and category slash normalization share one 301.
 * Historical Community permalinks retain their original path and slash form.
 */
const LEGACY_COMMUNITY = /^\/community-[a-z0-9]+(?:-[a-z0-9]+)*$/i;
const CATEGORY_ROUTE = /^\/(?:recensioni|news|speciali|guide|extra)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)?\/$/i;
const REVIEW_LABELS = new Set(["review", "reviews", "recensione", "recensioni"]);
const REVIEW_PREFIX_LABELS = new Set(["gaming", "tech"]);

function cleanReviewSlug(value) {
  const words = value.toLowerCase().split("-").filter(Boolean);
  if (words.length && REVIEW_LABELS.has(words[0])) {
    words.shift();
    if (words.length && REVIEW_PREFIX_LABELS.has(words[0])) words.shift();
  } else if (words.length > 1 && REVIEW_PREFIX_LABELS.has(words[0]) && REVIEW_LABELS.has(words[1])) {
    words.splice(0, 2);
  }
  return words.filter(word => !REVIEW_LABELS.has(word)).join("-");
}

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
      if (/\.html\/$/i.test(url.pathname)) {
        url.pathname = url.pathname.slice(0, -1);
      }
      if (/\.html$/i.test(url.pathname)) {
        url.pathname = url.pathname.slice(0, -5);
        if (url.pathname.toLowerCase() === "/index") url.pathname = "/";
      }

      const reviewPath = url.pathname.replace(/\/$/, "");
      const reviewMatch = reviewPath.match(/^\/recensioni\/([a-z0-9]+(?:-[a-z0-9]+)*)$/i);
      if (reviewMatch) {
        const clean = cleanReviewSlug(reviewMatch[1]);
        if (clean && clean !== reviewMatch[1].toLowerCase()) {
          url.pathname = "/recensioni/" + clean;
        } else if (reviewPath !== url.pathname) {
          url.pathname = reviewPath;
        }
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
