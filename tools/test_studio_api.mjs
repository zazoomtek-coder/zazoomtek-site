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
const dispatches = [];
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
  if (url.pathname === "/repos/" + repo + "/actions/workflows/pages-deploy-manual.yml/dispatches" && method === "POST") {
    dispatches.push(JSON.parse(options.body || "{}"));
    return new Response(null, { status: 204 });
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
  score: 8,
  body: [{
    type: "paragraph",
    text: "Questo testo di prova verifica il salvataggio editoriale completo su GitHub. " +
      "La procedura deve conservare il contenuto, la copertina e la categoria e deve " +
      "scrivere sul ramo principale senza attivare il deploy automatico del commit. " +
      "La pagina verrà pubblicata automaticamente al primo slot editoriale disponibile.",
  }],
};

const draftRecord = {
  ...record,
  slug: "studio-api-draft-check",
  title: "Verifica salvataggio bozza remota Studio 2",
  body: [{ type: "paragraph", text: "Questa bozza deve essere conservata su GitHub nel ramo editorial-queue e recuperata dall'endpoint v2-drafts anche senza localStorage." }],
};
const draftSave = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "draft",
    record: draftRecord,
    creating: true,
  }, cookie),
  env,
});
assert.equal(draftSave.status, 200, "Studio draft endpoint should save without local browser storage");
const draftSaveResult = await draftSave.json();
assert.equal(draftSaveResult.ok, true);
assert.equal(draftSaveResult.mode, "draft");
const remoteDrafts = await onRequest({
  request: request("/api/studio/v2-drafts", "GET", undefined, cookie),
  env,
});
assert.equal(remoteDrafts.status, 200, "Studio must read remote drafts from GitHub");
const remoteDraftData = await remoteDrafts.json();
assert.equal(remoteDraftData.drafts[draftRecord.slug].record.title, draftRecord.title,
  "A saved draft must be retrievable from GitHub after a page reload");
const draftWrite = writes.find((item) => item.path === "data/studio_v2_drafts.json");
assert.ok(draftWrite, "Draft must be written to data/studio_v2_drafts.json");
assert.equal(draftWrite.branch, "editorial-queue",
  "Drafts must remain on editorial-queue and must not be published to main");

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
const originalPublicPath = result.record.public_path;
assert.ok(originalPublicPath, "A new article must receive its canonical public URL");
assert.equal(result.status, "saved-main");
assert.equal(result.branch, "main");
assert.equal(result.record.score, 8, "A numeric review score of 8 must be accepted and saved");
assert.deepEqual(result.next_slots, ["12:30", "16:00", "19:30"]);
assert.equal(result.deploy_requested, undefined, "Studio must not request an immediate deployment");
assert.equal(dispatches.length, 0, "Studio must leave publication to the next scheduled editorial slot");

const postWrite = writes.find((item) => item.path === "data/studio_posts.json");
assert.ok(postWrite, "A new Studio article must be written to data/studio_posts.json");
assert.equal(postWrite.branch, "main", "Published article must be committed to main");
assert.ok(postWrite.message.startsWith("[CF-Pages-Skip] "), "Studio must prevent an uncontrolled Pages deploy; the scheduled editorial workflow handles publication");
const stored = JSON.parse(postWrite.content);
assert.equal(stored.posts[0].slug, record.slug);
assert.equal(stored.posts[0].source, "studio-editor");
assert.equal(stored.posts[0].title, record.title);
assert.equal(stored.posts[0].score, 8, "The numeric score must be persisted without formatting loss");

const formattedScoreRecord = {
  ...record,
  slug: "studio-api-formatted-score-check",
  title: "Verifica voto recensione formattato su dieci",
  score: "8/10",
};
const formattedScorePublish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: formattedScoreRecord,
    creating: true,
  }, cookie),
  env,
});
assert.equal(formattedScorePublish.status, 200, "Studio must accept a legacy formatted score such as 8/10");

assert.equal((await formattedScorePublish.json()).record.score, 8,
  "A legacy formatted score must be normalized to the numeric value 8");

// Both review categories must reject publication without a valid final score.
for (const category of ["recensioni-tech", "recensioni-gaming"]) {
  const invalidReview = {
    ...record,
    slug: "studio-api-missing-score-" + category,
    title: "Verifica blocco recensione senza voto " + category,
    category,
    score: "",
  };
  const writesBefore = writes.filter((item) => item.path === "data/studio_posts.json").length;
  const rejected = await onRequest({
    request: request("/api/studio/v2-save", "POST", {
      mode: "publish",
      record: invalidReview,
      creating: true,
    }, cookie),
    env,
  });
  assert.equal(rejected.status, 400, category + " publication without a score must be rejected");
  const rejectedBody = await rejected.json();
  assert.match(rejectedBody.error, /voto finale valido da 0 a 10/,
    "The API must return a clear missing-score error");
  assert.equal(writes.filter((item) => item.path === "data/studio_posts.json").length, writesBefore,
    "A review without a score must not be written to main");
}

// A valid decimal score (including the Italian comma format) must be accepted.
const decimalReview = {
  ...record,
  slug: "studio-api-decimal-review-score",
  title: "Verifica recensione con voto decimale",
  category: "recensioni-tech",
  score: "8,5/10",
};
const decimalReviewPublish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: decimalReview,
    creating: true,
  }, cookie),
  env,
});
assert.equal(decimalReviewPublish.status, 200, "A valid decimal review score must be accepted");
assert.equal((await decimalReviewPublish.json()).record.score, 8.5,
  "A decimal score using comma and /10 must be normalized to 8.5");

// An incomplete review can be saved as a draft, but cannot be published.
const incompleteReviewDraft = {
  ...record,
  slug: "studio-api-incomplete-review-draft",
  title: "Bozza recensione senza voto ancora da completare",
  category: "recensioni-gaming",
  score: "",
};
const incompleteDraftResponse = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "draft",
    record: incompleteReviewDraft,
    creating: true,
  }, cookie),
  env,
});
assert.equal(incompleteDraftResponse.status, 200,
  "An incomplete review must remain savable as a draft");

const pending = await onRequest({
  request: request("/api/studio/v2-pending", "GET", undefined, cookie),
  env,
});
assert.equal(pending.status, 200);
const pendingData = await pending.json();
assert.ok(pendingData.posts.some((item) => item.slug === record.slug),
  "A newly saved main article must immediately appear in the Studio library");

const editedRecord = {
  ...record,
  title: "Verifica automatica modifica articolo Studio già in coda",
  body: [{
    type: "paragraph",
    text: "La modifica di un articolo ancora in coda deve aggiornare il record esistente su main, " +
      "senza creare duplicati e senza chiedere un deploy immediato. Il contenuto aggiornato deve restare visibile nella libreria Studio, conservare lo stesso indirizzo pubblico e mantenere la copertina e gli altri blocchi editoriali. La pubblicazione effettiva deve continuare a dipendere esclusivamente dal primo slot programmato.",
  }],
};
const editPending = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: editedRecord,
    creating: false,
  }, cookie),
  env,
});
assert.equal(editPending.status, 200, "Studio must allow editing an article already waiting in the queue");
const editResult = await editPending.json();
assert.equal(editResult.record.title, editedRecord.title);
assert.equal(editResult.record.public_path, originalPublicPath,
  "Replacing an existing article must preserve its original public URL");
const latestPostWrite = writes.filter((item) => item.path === "data/studio_posts.json").at(-1);
assert.ok(latestPostWrite, "Editing a queued article must update data/studio_posts.json");
assert.equal(JSON.parse(latestPostWrite.content).posts.find((item) => item.slug === record.slug)?.title, editedRecord.title);
const pendingAfterEdit = await onRequest({
  request: request("/api/studio/v2-pending", "GET", undefined, cookie),
  env,
});
const pendingAfterEditData = await pendingAfterEdit.json();
assert.equal(pendingAfterEditData.posts.find((item) => item.slug === record.slug)?.title,
  editedRecord.title, "The edited queued article must remain visible in the Studio library");
assert.equal(dispatches.length, 0, "Editing a queued article must not trigger an immediate deployment");

const duplicate = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record,
    creating: true,
  }, cookie),
  env,
});
assert.equal(duplicate.status, 400, "A pending main article must not be silently overwritten as a new article");
assert.equal(writes.filter((item) => item.path === "data/studio_posts.json").length, 3, "The duplicate attempt must not create an additional write");

const unrestrictedBlocks = {
  ...record,
  slug: "studio-api-unrestricted-text-blocks",
  title: "Verifica blocchi di testo senza limiti individuali",
  body: [
    { type: "paragraph", text: "" },
    { type: "paragraph", text: "Testo lungo. ".repeat(1000) },
  ],
};
const unrestrictedPublish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: unrestrictedBlocks,
    creating: true,
  }, cookie),
  env,
});
assert.equal(unrestrictedPublish.status, 200,
  "Studio must accept empty text blocks and text blocks longer than 12,000 characters");
const unrestrictedResult = await unrestrictedPublish.json();
assert.equal(unrestrictedResult.ok, true);
assert.equal(unrestrictedResult.record.body[0].text, "",
  "An empty text block must be preserved");
assert.ok(unrestrictedResult.record.body[1].text.length > 12000,
  "A text block longer than 12,000 characters must be preserved");


const htmlRecord = {
  ...record,
  slug: "studio-api-html-check",
  title: "Verifica blocco HTML personalizzato Studio",
  body: [
    { type: "paragraph", text: "Testo editoriale sufficiente per la pubblicazione del contenuto HTML personalizzato. ".repeat(5) },
    { type: "html", html: '<p>Scopri il prodotto <a href="https://www.amazon.it/dp/B000000000">su Amazon</a></p>' },
  ],
};
const htmlPublish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: htmlRecord,
    creating: true,
  }, cookie),
  env,
});
assert.equal(htmlPublish.status, 200, "Studio must publish an article containing custom HTML blocks");
const htmlResult = await htmlPublish.json();
assert.equal(htmlResult.record.body[1].type, "html");
assert.equal(htmlResult.record.body[1].html, htmlRecord.body[1].html,
  "Custom HTML must be preserved exactly in the main article record");

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

const imageArticle = {
  ...record,
  slug: "studio-api-image-block-check",
  title: "Verifica pubblicazione articolo con immagine interna",
  body: [
    { type: "paragraph", text: "Questo articolo verifica che un'immagine caricata dal computer venga collegata correttamente al contenuto e salvata su main. Il percorso restituito dal caricamento deve essere riconosciuto dall'API di pubblicazione e conservato nel blocco immagine senza errori." },
    { type: "image", url: uploaded.url.slice(1), alt: "Immagine di prova", caption: "Immagine interna di prova" },
  ],
};
const imagePublish = await onRequest({
  request: request("/api/studio/v2-save", "POST", {
    mode: "publish",
    record: imageArticle,
    creating: true,
  }, cookie),
  env,
});
assert.equal(imagePublish.status, 200, "Studio must publish an article with a freshly uploaded internal image path");
const imageResult = await imagePublish.json();
assert.equal(imageResult.record.body[1].url, uploaded.url,
  "An uploaded image path without a leading slash must be normalized to the canonical public asset URL");
const imagePostWrite = writes.filter((item) => item.path === "data/studio_posts.json").at(-1);
assert.ok(JSON.parse(imagePostWrite.content).posts.some((item) =>
  item.slug === imageArticle.slug && item.body[1].url === uploaded.url),
  "The article and its internal image URL must both be committed to main");

console.log("STUDIO API INTEGRATION PASS: login, publish-to-main, first scheduled slot, library refresh, duplicate protection, cover upload, image blocks and preview.");
