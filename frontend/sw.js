/* BatchTwin service worker.

   Strategy matters here. An earlier version cached everything cache-FIRST,
   including /app and /app.js -- which meant a deployed change was invisible
   until the cache was cleared by hand. That is the wrong trade for an app whose
   code changes: correctness beats offline for the shell.

   So:
     * API + non-GET  -> never touched.
     * Documents & scripts (the code) -> NETWORK-first, cache as fallback.
       You always get the current app when online; offline you still boot.
     * Immutable assets (icons, fonts, vendored libs) -> cache-first.
       They are content-addressed by filename and never change in place.
*/
const VERSION = "v6";
const SHELL_CACHE = "batchtwin-shell-" + VERSION;
const ASSET_CACHE = "batchtwin-assets-" + VERSION;

const SHELL = ["/", "/landing", "/app", "/app.js", "/i18n.js", "/barcode.js", "/qr.js",
               "/floor", "/floor.js", "/vera", "/manifest.webmanifest"];

const IMMUTABLE = (p) => p.startsWith("/icons/") || p.startsWith("/vendor/") ||
                         p.startsWith("/logo/");

self.addEventListener("install", (e) => {
  // Pre-warm the shell but never let one failed URL abort the install.
  e.waitUntil(
    caches.open(SHELL_CACHE)
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== SHELL_CACHE && k !== ASSET_CACHE)
            .map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  // Live batch data is never cached: a stale dossier is worse than no dossier.
  if (url.pathname.startsWith("/api/")) return;

  if (IMMUTABLE(url.pathname)) {
    e.respondWith(
      caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(ASSET_CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }))
    );
    return;
  }

  // Everything else is code: network first, so a deploy is visible immediately.
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then((hit) => hit || caches.match("/app")))
  );
});

// Lets the page force an update without the user clearing site data by hand.
self.addEventListener("message", (e) => {
  if (e.data === "skipWaiting") self.skipWaiting();
});
