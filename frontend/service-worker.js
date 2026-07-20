// Nama cache dan versi - tukar versi untuk paksa refresh cache
// 🔴 v7: BUST CACHE — ringkasan API dibuang, guna renderParlimenMirrorTable()
//          Tukar versi paksa SW lama dibuang dan HTML/app.js baru diambil dari network.
// 🔴 v8: BUST CACHE — tambah kpi.js (PPU Pegawai Penyelaras)
// 🔴 v9: BUST CACHE — PPU layout update: kolum Parlimen/DUN/PDM Mengundi
const CACHE_NAME = 'pengundi-p170-v9';

// Fail statik yang akan di-cache semasa pemasangan (guna sebagai fallback offline)
// NOTA: Jangan masukkan CDN URLs (tailwind, chart.js) — ia perlu di-fetch dari network
//       kerana cache.addAll akan gagal jika mana-mana CDN tidak reachable.
const STATIC_ASSETS = [
    './manifest.json',
    './logo.png',
    './js/dashboard-layout.js',
    './js/app.js',
    './js/kpi.js'
    // index.html TIDAK dimasukkan — guna network-first supaya deploy baru selalu dapat HTML terkini
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
    // TAPIS SKIM: Hanya proses http: dan https:
    // chrome-extension://, data:, blob:, file:, dll. TIDAK disokong oleh SW
    // dan akan menyebabkan Uncaught TypeError jika cuba diproses.
    if (!event.request.url.startsWith('http:') && !event.request.url.startsWith('https:')) {
        return; // Abaikan tanpa kesilapan
    }

    try {
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
    } catch (error) {
        console.warn('[SW] fetch error:', error.message);
        // Graceful fallback: biarkan permintaan diteruskan secara normal
    }
});

// Strategi Cache First: guna cache dulu, fallback ke network
async function cacheFirst(request) {
    try {
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.warn('[SW] cacheFirst error:', error.message);
        // Jangan return 503 untuk semua — biarkan browser fetch secara normal
        return fetch(request);
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
