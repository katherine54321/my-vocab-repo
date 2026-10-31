// VocabMatrix Service Worker (PWA Offline Support)
const CACHE_NAME = 'vocab-matrix-pwa-v1.0';

const PRECACHE_ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './categories.js',
  './categories.json',
  './data.js',
  './manifest.json',
  './icons/favicon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

// Install: Pre-cache app shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache partial fail, continuing...', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate: Clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Deleting obsolete cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Stale-While-Revalidate for app shell & static assets
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Bypass non-GET requests
  if (req.method !== 'GET') return;

  // Audio files: fetch from network or fallback
  if (url.pathname.endsWith('.mp3') || url.hostname.includes('dictvoice')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        return cached || fetch(req).then((res) => {
          if (res.ok && res.status === 200) {
            const resClone = res.clone();
            caches.open('audio-cache').then((c) => c.put(req, resClone));
          }
          return res;
        }).catch(() => new Response(null, { status: 404 }));
      })
    );
    return;
  }

  // App shell and local static files: Stale-While-Revalidate
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const toCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, toCache));
        }
        return networkResponse;
      }).catch((err) => {
        // Offline fallback
        if (cachedResponse) return cachedResponse;
        if (req.mode === 'navigate') {
          return caches.match('./index.html');
        }
        return new Response(JSON.stringify({ error: 'offline' }), {
          headers: { 'Content-Type': 'application/json' }
        });
      });

      return cachedResponse || fetchPromise;
    })
  );
});
