// Nama cache dan versi - tukar versi untuk paksa refresh cache
// 🔴 v4: BUST CACHE — index.html lama yang broken dulu masih disimpan oleh SW v3
//          Tukar versi paksa SW lama dibuang dan HTML baru diambil dari network.
const CACHE_NAME = 'pengundi-p170-v4';

// Fail statik yang akan di-cache semasa pemasangan (guna sebagai fallback offline)
// NOTA: Jangan masukkan CDN URLs (tailwind, chart.js) — ia perlu di-fetch dari network
//       kerana cache.addAll akan gagal jika mana-mana CDN tidak reachable.
const STATIC_ASSETS = [
    './manifest.json',
    './logo.png',
    './js/dashboard-layout.js'
    // 🛡️ index.html TIDAK dimasukkan — guna network-first supaya deploy baru selalu dapat HTML terkini
];

// ===== INSTALL: Cache static assets =====
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Caching static assets...');
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.warn('[SW] Failed to cache some static assets:', err);
            });
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

    // Untuk HTML documents - Network First (supaya selalu dapat deploy terkini)
    if (event.request.mode === 'navigate') {
        event.respondWith(networkFirst(event.request));
        return;
    }

    // Untuk font, CDN, dan fail statik lain - Cache First
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