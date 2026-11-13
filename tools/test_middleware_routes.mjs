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

const archive = await request("https://zazoomtek.it/recensioni/");
assert(archive.status === 301, "Category archive trailing slash must redirect");
assert(archive.headers.get("Location") === "https://zazoomtek.it/recensioni",
  "Category archive must normalize without trailing slash");

const htmlAlias = await request("https://zazoomtek.it/guide/come-configurare-wifi.html");
assert(htmlAlias.status === 301, ".html article alias must redirect");
assert(htmlAlias.headers.get("Location") === "https://zazoomtek.it/guide/come-configurare-wifi",
  ".html article alias must resolve directly to category canonical");

for (const url of [
  "https://zazoomtek.it/community-ugkx123456789/",
  "https://zazoomtek.it/community-ugkx123456789"
]) {
  const legacy = await request(url);
  assert(legacy.status === 200, "Historical Community URL must not be redirected: " + url);
  assert(!legacy.headers.has("Location"), "Historical Community URL must retain its original path");
}

console.log("Cloudflare middleware route tests PASS: one-hop category redirects and unchanged Community paths.");
