/**
 * Canonical URL enforcement for ZazoomTek.
 * Category-label aliases, host, scheme, .html and trailing slashes share one 301.
 * Historical Community permalinks retain their original path and slash form.
 */
const LEGACY_COMMUNITY = /^\/community-[a-z0-9]+(?:-[a-z0-9]+)*$/i;
const CATEGORY_ROUTE = /^\/(?:recensioni|news|speciali|guide|extra)(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)?\/$/i;
const CATEGORY_PREFIXES = new Set(["recensioni", "news", "speciali", "guide", "extra"]);
const CATEGORY_QUALIFIERS = new Set(["tech", "gaming", "extra", "review", "reviews", "recensione", "recensioni"]);
const REVIEW_LABELS = new Set(["review", "reviews", "recensione", "recensioni"]);

function cleanCategorySlug(value, category) {
  const words = value.toLowerCase().split("-").filter(Boolean);
  let changed = true;
  while (words.length && changed) {
    changed = false;
    if (words[0] === category || CATEGORY_PREFIXES.has(words[0])) {
      words.shift();
      changed = true;
      if (words.length && CATEGORY_QUALIFIERS.has(words[0])) {
        words.shift();
        changed = true;
      }
    }
  }
  if (category === "recensioni") {
    if (words[0] === "review" || words[0] === "reviews" || words[0] === "recensione") {
      words.shift();
      if (words[0] === "gaming" || words[0] === "tech") words.shift();
    }
    return words.filter(word => !REVIEW_LABELS.has(word)).join("-");
  }
  return words.join("-");
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

      const match = url.pathname.match(/^\/(recensioni|news|speciali|guide|extra)\/([a-z0-9]+(?:-[a-z0-9]+)*)(\/?$)/i);
      if (match) {
        const category = match[1].toLowerCase();
        const currentSlug = match[2].toLowerCase();
        const clean = cleanCategorySlug(currentSlug, category);
        if (clean && clean !== currentSlug) {
          url.pathname = "/" + category + "/" + clean;
        } else if (match[3] === "/") {
          url.pathname = "/" + category + "/" + currentSlug;
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
