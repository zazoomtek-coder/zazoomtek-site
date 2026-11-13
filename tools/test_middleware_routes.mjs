import { readFileSync } from "node:fs";

const source = readFileSync("functions/_middleware.js", "utf8");
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const { onRequest } = await import(moduleUrl);

async function request(url) {
  return onRequest({
    request: new Request(url),
    next: async () => new Response("ok", { status: 200 })
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const combined = await request("http://www.zazoomtek.it/news/prova-articolo/?utm_source=test");
assert(combined.status === 301, "Combined host/scheme/category slash must return 301");
assert(combined.headers.get("Location") === "https://zazoomtek.it/news/prova-articolo?utm_source=test",
  "Combined normalization must preserve query and finish at one canonical URL");
const secondHop = await request(combined.headers.get("Location"));
assert(secondHop.status === 200, "Canonical destination must not redirect again");

for (const category of ["recensioni", "news", "speciali", "guide", "extra"]) {
  const canonical = await request("https://zazoomtek.it/" + category);
  assert(canonical.status === 200 && !canonical.headers.has("Location"),
    "Canonical category archive must serve directly without redirect: " + category);
  const trailing = await request("https://zazoomtek.it/" + category + "/");
  assert(trailing.status === 301, "Category archive trailing slash must redirect: " + category);
  assert(trailing.headers.get("Location") === "https://zazoomtek.it/" + category,
    "Category archive must normalize in one hop: " + category);
  const destination = await request(trailing.headers.get("Location"));
  assert(destination.status === 200, "Category archive redirect target must serve HTTP 200: " + category);
}

const htmlAlias = await request("https://zazoomtek.it/guide/come-configurare-wifi.html");
assert(htmlAlias.status === 301, ".html article alias must redirect");
assert(htmlAlias.headers.get("Location") === "https://zazoomtek.it/guide/come-configurare-wifi",
  ".html article alias must resolve directly to category canonical");

const oldReview = await request("https://zazoomtek.it/recensioni/review-gaming-payday-aces-high-recensione-pcvr?utm_source=legacy");
assert(oldReview.status === 301, "Long review slug must redirect permanently");
assert(oldReview.headers.get("Location") === "https://zazoomtek.it/recensioni/payday-aces-high-pcvr?utm_source=legacy",
  "Review alias must point directly to the clean subject/platform slug and preserve query");
const cleanReview = await request(oldReview.headers.get("Location"));
assert(cleanReview.status === 200, "Clean review canonical must not redirect again");

for (const url of [
  "https://zazoomtek.it/community-ugkx123456789/",
  "https://zazoomtek.it/community-ugkx123456789"
]) {
  const legacy = await request(url);
  assert(legacy.status === 200, "Historical Community URL must not be redirected: " + url);
  assert(!legacy.headers.has("Location"), "Historical Community URL must retain its original path");
}

console.log("Cloudflare middleware route tests PASS: review aliases, one-hop normalization and unchanged Community paths.");
