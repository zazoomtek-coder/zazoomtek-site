/**
 * Canonical URL enforcement for ZazoomTek.
 *
 * - www.zazoomtek.it -> zazoomtek.it
 * - /article.html -> /article
 * - /index.html -> /
 *
 * One permanent redirect handles host + path normalization together.
 * Query strings are preserved. Other requests continue unchanged.
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const original = url.toString();

  if (url.hostname.toLowerCase() === "www.zazoomtek.it") {
    url.hostname = "zazoomtek.it";
  }

  if (url.hostname.toLowerCase() === "zazoomtek.it") {
    url.protocol = "https:";

    if (url.pathname.toLowerCase().endsWith(".html")) {
      url.pathname = url.pathname.slice(0, -5);
      if (url.pathname.toLowerCase() === "/index") {
        url.pathname = "/";
      }
    }

    if (url.toString() !== original) {
      return Response.redirect(url.toString(), 301);
    }
  }

  return context.next();
}
