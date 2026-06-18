const CACHE_NAME = 'tasks-app-v1';
const URLS_TO_CACHE = [
  '/',
  '/login',
  '/register'
];

// Install service worker and cache pages
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(URLS_TO_CACHE);
    })
  );
});

// Serve from cache when offline
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});