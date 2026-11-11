/**
 * Canonical URL enforcement for ZazoomTek.
 *
 * Normalize www, HTTP and .html aliases in a single permanent redirect.
 * Query strings are preserved. Other hosts and paths continue unchanged.
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
