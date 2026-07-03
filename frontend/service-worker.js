// Nama cache dan versi - tukar versi untuk paksa refresh cache
const CACHE_NAME = 'pengundi-n05-v2';

// Fail statik yang akan di-cache semasa pemasangan
const STATIC_ASSETS = [
    './index.html',
    './manifest.json',
    'https://cdn.tailwindcss.com',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
];

// ===== INSTALL: Cache static assets =====
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Caching static assets...');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// ===== ACTIVATE: Bersihkan cache lama =====
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// ===== FETCH: Strategi Network First untuk API, Cache First untuk static =====
self.addEventListener('fetch', (event) => {
    const requestUrl = event.request.url;

    // Untuk API calls (localhost:8000) - Network First
    if (requestUrl.includes('localhost:8000') || requestUrl.includes('/api/')) {
        event.respondWith(networkFirst(event.request));
        return;
    }

    // Untuk font, CDN, dan fail statik - Cache First
    event.respondWith(cacheFirst(event.request));
});

// Strategi Cache First: guna cache dulu, fallback ke network
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        return new Response('Offline', { status: 503 });
    }
}

// Strategi Network First: cuba network dulu, fallback ke cache
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}