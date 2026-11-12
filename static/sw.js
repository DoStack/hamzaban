const CACHE = "hamzaban-static-v2";
const FILES = [
  "/static/css/site.css",
  "/static/css/fonts.css",
  "/static/favicon.svg",
  "/static/unfold/fonts/material-symbols/styles.css",
  "/static/unfold/fonts/material-symbols/Material-Symbols-Outlined.woff2",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(FILES)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
