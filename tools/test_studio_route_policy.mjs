import { readFileSync } from "node:fs";

const source = readFileSync("functions/api/studio/[[path]].js", "utf8");
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const { publicSlug, assignPublicRoute } = await import(moduleUrl);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const title = "È arrivata la nuova recensione: Auricolari! 2026";
assert(publicSlug(title) === "arrivata-recensione-auricolari-2026",
  "Studio slug normalization must match the Python route policy");

const record = { title: "Nuovo smartphone", category: "news-tech" };
assignPublicRoute(record, [
  { title: "Smartphone già pubblicato", category: "news-gaming",
    route_version: 2, public_path: "/news/smartphone" }
]);
assert(record.route_version === 2, "New Studio articles must be marked route_version 2");
assert(record.public_slug === "smartphone-2", "Studio must allocate the next category slug");
assert(record.public_path === "/news/smartphone-2", "Studio must persist the immutable category URL");

const review = { title: "Auricolari wireless", category: "recensioni-tech" };
assignPublicRoute(review, [
  { category: "news-tech", route_version: 2, public_path: "/news/auricolari-wireless" }
]);
assert(review.public_path === "/recensioni/auricolari-wireless",
  "The same slug is allowed in a different public category");

console.log("Studio route policy tests PASS: route_version, title slug, category prefix and collision suffix.");
