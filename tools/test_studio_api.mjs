import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { Buffer } from "node:buffer";
import { webcrypto } from "node:crypto";

globalThis.crypto ??= webcrypto;
globalThis.btoa ??= (value) => Buffer.from(value, "binary").toString("base64");
globalThis.atob ??= (value) => Buffer.from(value, "base64").toString("binary");

const source = await readFile(new URL("../functions/api/studio/[[path]].js", import.meta.url), "utf8");
const { onRequest } = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));

const repo = "zazoomtek-coder/zazoomtek-site";
const origin = "https://zazoomtek-spotnews-preview.pages.dev";
const token = "github_pat_test_123456789012345678901234";
const files = new Map();
const writes = [];
let blobNumber = 0;

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

globalThis.fetch = async (input, options = {}) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  const method = options.method || "GET";

  if (url.pathname === "/user") return json({ login: "zazoomtek-coder", id: 333682421 });
  if (url.pathname === "/repos/" + repo) {
    return json({ full_name: repo, permissions: { push: true } });
  }

  const prefix = "/repos/" + repo + "/contents/";
  if (url.pathname.startsWith(prefix)) {
    const path = decodeURIComponent(url.pathname.slice(prefix.length));
    if (method === "GET") {
      const branch = url.searchParams.get("ref") || "main";
      const item = files.get(branch + ":" + path);
      if (!item) return json({ message: "Not Found" }, 404);
      return json({
        sha: item.sha,
        encoding: "base64",
        content: Buffer.isBuffer(item.content)
          ? item.content.toString("base64")
          : Buffer.from(item.content, "utf8").toString("base64"),
      });
    }
    if (method === "PUT") {
      const body = JSON.parse(options.body || "{}");
      const key = body.branch + ":" + path;
      const existing = files.get(key);
      if (body.sha && (!existing || body.sha !== existing.sha)) {
        return json({ message: "sha does not match" }, 409);
      }
      const decoded = Buffer.from(body.content || "", "base64");
      const content = path.startsWith("assets/uploads/") ? decoded : decoded.toString("utf8");
      const sha = "blob-" + (++blobNumber);
      files.set(key, { sha, content });
      writes.push({ path, branch: body.branch, message: body.message, content });
      return json({ content: { sha }, commit: { sha: "commit-" + blobNumber } }, 201);
    }
  }
  return json({ message: "Not Found" }, 404);
};

const env = {
  STUDIO_SESSION_SECRET: "studio-integration-test-secret-with-more-than-32-characters",
  ASSETS: {
    async fetch() {
      return json({ posts: [] });
    },
  },
};

function request(path, method = "GET", body, cookie = "") {
  const headers = {};
  if (cookie) headers.Cookie = cookie;
  if (method === "POST") {
    headers.Origin = origin;
    headers["Content-Type"] = "application/json";
  }
  return new Request(origin + path, {
    method,
    headers,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

const login = await onRequest({
  request: request("/api/studio/login", "POST", { token }),
  env,
});
assert.equal(login.status, 200, "GitHub owner login should succeed");
const cookie = (login.headers.get("Set-Cookie") || "").split(";")[0];
assert.ok(cookie.startsWith("__Host-zzt-studio="), "Session must be an HttpOnly Studio cookie");

const record = {
  slug: "studio-api-integration-check",
  title: "Verifica automatica pubblicazione Studio su main",
  category: "news-tech",
  image: "https://example.com/studio-test-cover.jpg",
  author: "Redazione ZazoomTek",
  body: [{
    type: "paragraph",
    text: "Questo testo di prova verifica il salvataggio editoriale completo su GitHub. " +
      "La procedura deve conservare il contenuto, la copertina e la categoria e deve " +
      "scrivere sul ramo principale senza avviare una pubblicazione immediata di Cloudflare. " +
      "La pagina verrà poi generata dal template editoriale condiviso negli slot previsti.",
  }],
};

const publish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record,
    creating: true,
  }, cookie),
  env,
});
assert.equal(publish.status, 200, "Studio publish endpoint should return success");
const result = await publish.json();
assert.equal(result.ok, true);
assert.equal(result.status, "saved-main");
assert.equal(result.branch, "main");
assert.ok(result.next_slots.includes("16:00"), "16:00 must be an advertised release slot");

const postWrite = writes.find((item) => item.path === "data/studio_posts.json");
assert.ok(postWrite, "A new Studio article must be written to data/studio_posts.json");
assert.equal(postWrite.branch, "main", "Published article must be committed to main");
assert.ok(postWrite.message.startsWith("[CF-Pages-Skip] "), "Studio must not bypass scheduled Cloudflare release");
const stored = JSON.parse(postWrite.content);
assert.equal(stored.posts[0].slug, record.slug);
assert.equal(stored.posts[0].source, "studio-editor");
assert.equal(stored.posts[0].title, record.title);

const pending = await onRequest({
  request: request("/api/studio/v2-pending", "GET", undefined, cookie),
  env,
});
assert.equal(pending.status, 200);
const pendingData = await pending.json();
assert.ok(pendingData.posts.some((item) => item.slug === record.slug),
  "A newly saved main article must immediately appear in the Studio library");

const duplicate = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record,
    creating: true,
  }, cookie),
  env,
});
assert.equal(duplicate.status, 400, "A pending main article must not be silently overwritten as a new article");
assert.equal(writes.filter((item) => item.path === "data/studio_posts.json").length, 1);

const jpeg = Buffer.alloc(80);
jpeg[0] = 0xff; jpeg[1] = 0xd8; jpeg[2] = 0xff;
const upload = await onRequest({
  request: request("/api/studio/upload", "POST", {
    slug: record.slug,
    mime: "image/jpeg",
    base64: "data:image/jpeg;base64," + jpeg.toString("base64"),
  }, cookie),
  env,
});
assert.equal(upload.status, 200, "Studio cover upload should succeed");
const uploaded = await upload.json();
const mediaWrite = writes.find((item) => item.path.startsWith("assets/uploads/"));
assert.ok(mediaWrite, "Cover image must be stored in the repository");
assert.equal(mediaWrite.branch, "main");
assert.ok(mediaWrite.message.startsWith("[CF-Pages-Skip] "));
assert.equal(uploaded.url, "/" + mediaWrite.path);

const media = await onRequest({
  request: request("/api/studio/v2-asset?path=" + encodeURIComponent(mediaWrite.path), "GET", undefined, cookie),
  env,
});
assert.equal(media.status, 200, "The uploaded cover must be readable in Studio preview");
assert.equal(media.headers.get("Content-Type"), "image/jpeg");
assert.equal((await media.arrayBuffer()).byteLength, jpeg.byteLength);

console.log("STUDIO API INTEGRATION PASS: login, publish-to-main, scheduled-release guard, library refresh, duplicate protection, cover upload and preview.");
