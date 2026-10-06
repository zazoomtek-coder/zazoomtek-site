const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");
const crypto = require("crypto");

admin.initializeApp();
const db = admin.firestore();
const REGION = "europe-west1";
const RULES_VERSION = "2026-10-06";
const MAX_COMMENT_LENGTH = 1200;
const MAX_NAME_LENGTH = 40;
const APPROVED_RETENTION_MS = 1000 * 60 * 60 * 24 * 730;
const REPORTED_RETENTION_MS = 1000 * 60 * 60 * 24 * 30;

function json(res, status, body) {
  res.set("Cache-Control", "no-store");
  res.set("Content-Type", "application/json; charset=utf-8");
  return res.status(status).send(JSON.stringify(body));
}

function hash(value) {
  return crypto.createHash("sha256").update(String(value || "")).digest("hex");
}

function cleanString(value) {
  return String(value || "").replace(/\u0000/g, "").trim();
}

function clientIp(req) {
  const xff = cleanString(req.headers["x-forwarded-for"] || "");
  const first = xff.split(",")[0].trim();
  return first || cleanString(req.ip || req.socket?.remoteAddress || "unknown");
}

function threadKey(contentId) {
  return hash(contentId).slice(0, 40);
}

function validContentId(value) {
  return /^(news-[A-Za-z0-9_-]{10,}\.html|recensione-[A-Za-z0-9_-]{10,}\.html|nba-2k27-recensione-ps5\.html)$/.test(value);
}

function normalize(value) {
  return cleanString(value).normalize("NFKC").replace(/\s+/g, " ").toLowerCase();
}

function moderation(displayName, text) {
  const n = normalize(displayName);
  const t = normalize(text);
  const combined = n + " " + t;

  if (displayName.length < 2 || displayName.length > MAX_NAME_LENGTH) {
    return { ok: false, reason: "Usa un nome o nickname tra 2 e 40 caratteri." };
  }
  if (text.length < 3 || text.length > MAX_COMMENT_LENGTH) {
    return { ok: false, reason: "Il commento deve contenere da 3 a 1200 caratteri." };
  }

  if (/^(admin|administrator|moderatore|moderator|zazoomtek|zazoom tek|staff)$/i.test(displayName.trim())) {
    return { ok: false, reason: "Questo nome è riservato allo staff." };
  }

  const htmlOrCode = /<\/?[a-z][\s\S]*?>|javascript\s*:|data\s*:\s*text\/html/i;
  if (htmlOrCode.test(text)) {
    return { ok: false, reason: "HTML, script o codice incorporato non sono consentiti." };
  }

  const linkPattern = /(https?:\/\/|www\.|\b[a-z0-9][a-z0-9-]{1,62}\.(?:com|it|net|org|io|gg|me|ru|cn|xyz|top|site|online|info|biz)\b)/i;
  const emailPattern = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i;
  const phonePattern = /(?:\+?\d[\s().-]*){8,}/;
  if (linkPattern.test(text) || emailPattern.test(text) || phonePattern.test(text)) {
    return { ok: false, reason: "Per sicurezza non sono consentiti link, email, numeri di telefono o contatti personali." };
  }

  if (/(.)\1{7,}/u.test(text)) {
    return { ok: false, reason: "Riduci le sequenze ripetute di caratteri." };
  }

  const spamWords = [
    "casino","scommesse","betting","bonus senza deposito","crypto giveaway","airdrop",
    "telegram","contattami su whatsapp","seo service","guest post","backlink","viagra",
    "prestito immediato","guadagna online","onlyfans"
  ];
  if (spamWords.some(w => combined.includes(w))) {
    return { ok: false, reason: "Il messaggio è stato bloccato dal filtro antispam." };
  }

  const profanity = [
    "vaffanculo","coglione","cogliona","stronzo","stronza","merda","troia","puttana",
    "bastardo","bastarda","fuck you","motherfucker"
  ];
  if (profanity.some(w => combined.includes(w))) {
    return { ok: false, reason: "Mantieni un linguaggio civile e rispettoso." };
  }

  const threats = [
    /\b(?:ti|vi|lo|la|li|le)\s+(?:ammazzo|uccido|spacco|accoltello|brucio)\b/i,
    /\b(?:devi|dovete)\s+morire\b/i,
    /\bti\s+vengo\s+a\s+cercare\b/i
  ];
  if (threats.some(r => r.test(t))) {
    return { ok: false, reason: "Minacce o incitamenti alla violenza non sono consentiti." };
  }

  const highRiskAccusations = [
    "pedofilo","pedofila","truffatore","truffatrice","criminale","mafioso","mafiosa",
    "ladro","ladra","corrotto","corrotta","stupratore","stupratrice"
  ];
  if (highRiskAccusations.some(w => combined.includes(w))) {
    return { ok: false, reason: "Accuse personali o affermazioni potenzialmente diffamatorie richiedono canali formali e non vengono pubblicate nei commenti." };
  }

  const sensitive = [
    "codice fiscale","carta di credito","iban","password","indirizzo di casa",
    "numero di documento","documento d'identità"
  ];
  if (sensitive.some(w => combined.includes(w))) {
    return { ok: false, reason: "Non pubblicare dati personali, credenziali o informazioni sensibili." };
  }

  return { ok: true };
}

async function enforceRateLimit(req, action, limit = 5, windowMs = 15 * 60 * 1000) {
  const key = hash(clientIp(req) + "|" + action).slice(0, 48);
  const ref = db.collection("comment_rate_limits").doc(key);
  const now = Date.now();

  return db.runTransaction(async tx => {
    const snap = await tx.get(ref);
    let count = 0;
    let startMs = now;
    if (snap.exists) {
      const data = snap.data() || {};
      const started = data.windowStartedAt?.toMillis ? data.windowStartedAt.toMillis() : 0;
      if (started && now - started < windowMs) {
        count = Number(data.count || 0);
        startMs = started;
      }
    }
    if (count >= limit) return false;
    tx.set(ref, {
      count: count + 1,
      windowStartedAt: admin.firestore.Timestamp.fromMillis(startMs),
      expiresAt: admin.firestore.Timestamp.fromMillis(startMs + windowMs + 60000)
    }, { merge: false });
    return true;
  });
}

async function listComments(contentId) {
  const ref = db.collection("comment_threads").doc(threadKey(contentId)).collection("comments");
  const snap = await ref.where("status", "==", "approved").limit(200).get();
  const now = Date.now();
  const visible = [];
  const expiredRefs = [];

  snap.forEach(doc => {
    const d = doc.data() || {};
    const created = d.createdAt?.toMillis ? d.createdAt.toMillis() : 0;
    if (!created || now - created > APPROVED_RETENTION_MS) {
      expiredRefs.push(doc.ref);
      return;
    }
    visible.push({
      id: doc.id,
      displayName: d.displayName || "Utente",
      text: d.text || "",
      parentId: d.parentId || null,
      createdAt: d.createdAt?.toDate ? d.createdAt.toDate().toISOString() : null
    });
  });

  if (expiredRefs.length) {
    const batch = db.batch();
    expiredRefs.slice(0, 100).forEach(r => batch.delete(r));
    await batch.commit().catch(() => {});
  }

  const reported = await ref.where("status", "==", "reported").limit(30).get().catch(() => null);
  if (reported) {
    const old = [];
    reported.forEach(doc => {
      const t = doc.data()?.reportedAt?.toMillis ? doc.data().reportedAt.toMillis() : 0;
      if (t && now - t > REPORTED_RETENTION_MS) old.push(doc.ref);
    });
    if (old.length) {
      const batch = db.batch();
      old.forEach(r => batch.delete(r));
      await batch.commit().catch(() => {});
    }
  }

  visible.sort((a, b) => new Date(a.createdAt || 0) - new Date(b.createdAt || 0));
  return visible;
}

async function submitComment(req, res, body) {
  if (!(await enforceRateLimit(req, "submit", 5))) {
    return json(res, 429, { status: "rejected", message: "Troppi tentativi. Riprova tra qualche minuto." });
  }

  const contentId = cleanString(body.contentId);
  const contentType = cleanString(body.contentType);
  const displayName = cleanString(body.displayName);
  const text = cleanString(body.text);
  const website = cleanString(body.website);
  const parentId = cleanString(body.parentId) || null;

  if (website) return json(res, 200, { status: "rejected", message: "Commento non accettato." });
  if (!validContentId(contentId) || !["news", "review"].includes(contentType)) {
    return json(res, 400, { status: "rejected", message: "Contenuto non valido." });
  }
  if (body.acceptedRules !== true || body.age14 !== true) {
    return json(res, 400, { status: "rejected", message: "Devi accettare regole/privacy e confermare di avere almeno 14 anni." });
  }

  const mod = moderation(displayName, text);
  if (!mod.ok) return json(res, 200, { status: "rejected", message: mod.reason });

  const threadRef = db.collection("comment_threads").doc(threadKey(contentId));
  const commentsRef = threadRef.collection("comments");

  let rootParent = null;
  if (parentId) {
    const parentSnap = await commentsRef.doc(parentId).get();
    if (!parentSnap.exists || parentSnap.data()?.status !== "approved") {
      return json(res, 400, { status: "rejected", message: "Il commento a cui stai rispondendo non è più disponibile." });
    }
    rootParent = parentSnap.data()?.parentId || parentSnap.id;
  }

  const deleteToken = crypto.randomBytes(24).toString("base64url");
  const now = admin.firestore.Timestamp.now();
  const docRef = commentsRef.doc();

  await docRef.set({
    contentId,
    contentType,
    displayName,
    text,
    parentId: rootParent,
    status: "approved",
    createdAt: now,
    consentAt: now,
    acceptedRulesVersion: RULES_VERSION,
    age14Confirmed: true,
    deleteTokenHash: hash(deleteToken),
    moderationVersion: RULES_VERSION
  });

  await threadRef.set({ contentId, contentType, updatedAt: now }, { merge: true });

  return json(res, 201, {
    status: "approved",
    id: docRef.id,
    deleteToken
  });
}

async function reportComment(req, res, body) {
  if (!(await enforceRateLimit(req, "report", 8))) {
    return json(res, 429, { message: "Troppe segnalazioni. Riprova più tardi." });
  }
  const contentId = cleanString(body.contentId);
  const commentId = cleanString(body.commentId);
  const reason = cleanString(body.reason).slice(0, 300);
  if (!validContentId(contentId) || !commentId || reason.length < 3) {
    return json(res, 400, { message: "Segnalazione non valida." });
  }

  const ref = db.collection("comment_threads").doc(threadKey(contentId)).collection("comments").doc(commentId);
  const snap = await ref.get();
  if (!snap.exists) return json(res, 404, { message: "Commento non trovato." });

  await ref.update({
    status: "reported",
    reportedAt: admin.firestore.Timestamp.now(),
    reportReason: reason
  });
  return json(res, 200, { ok: true });
}

async function deleteComment(req, res, body) {
  if (!(await enforceRateLimit(req, "delete", 8))) {
    return json(res, 429, { message: "Troppi tentativi. Riprova più tardi." });
  }
  const contentId = cleanString(body.contentId);
  const commentId = cleanString(body.commentId);
  const token = cleanString(body.deleteToken);
  if (!validContentId(contentId) || !commentId || !token) {
    return json(res, 400, { message: "Richiesta non valida." });
  }

  const commentsRef = db.collection("comment_threads").doc(threadKey(contentId)).collection("comments");
  const ref = commentsRef.doc(commentId);
  const snap = await ref.get();
  if (!snap.exists) return json(res, 404, { message: "Commento non trovato." });
  if (hash(token) !== snap.data()?.deleteTokenHash) {
    return json(res, 403, { message: "Non sei autorizzato a eliminare questo commento." });
  }

  const replies = await commentsRef.where("parentId", "==", commentId).limit(100).get().catch(() => null);
  const batch = db.batch();
  batch.delete(ref);
  if (replies) replies.forEach(d => batch.delete(d.ref));
  await batch.commit();
  return json(res, 200, { ok: true });
}

exports.commentsApi = onRequest(
  { region: REGION, memory: "256MiB", timeoutSeconds: 15, maxInstances: 5 },
  async (req, res) => {
    try {
      if (req.method === "GET") {
        const contentId = cleanString(req.query.contentId);
        if (!validContentId(contentId)) return json(res, 400, { message: "Contenuto non valido." });
        const comments = await listComments(contentId);
        return json(res, 200, { comments });
      }

      if (req.method !== "POST") {
        res.set("Allow", "GET, POST");
        return json(res, 405, { message: "Metodo non consentito." });
      }

      const body = req.body && typeof req.body === "object" ? req.body : {};
      if (body.action === "submit") return await submitComment(req, res, body);
      if (body.action === "report") return await reportComment(req, res, body);
      if (body.action === "delete") return await deleteComment(req, res, body);
      return json(res, 400, { message: "Azione non valida." });
    } catch (err) {
      console.error("commentsApi error", err);
      return json(res, 500, { message: "Servizio commenti temporaneamente non disponibile." });
    }
  }
);