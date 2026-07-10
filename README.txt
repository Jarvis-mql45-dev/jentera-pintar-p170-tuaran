================================================================================
                  JENTERA PINTAR P170 TUARAN
          Sistem Pengurusan Pengundi & Analisis Pilihan Raya
================================================================================

1. MAKLUMAT AM PROJEK
================================================================================

Nama Projek      : JenteraPintar P170 Tuaran
Versi            : 1.1.0
Platform         : Vercel Serverless + Supabase
Bahasa/Framework : Python (FastAPI), HTML/JavaScript (PWA Frontend)
Tarikh           : Julai 2026

Parlimen P170 Tuaran meliputi 4 kawasan Dewan Undangan Negeri (DUN):
  - N12 Sulaman
  - N13 Pantai Dalit
  - N14 Tamparuli
  - N15 Kiulu

Jumlah Pengundi Berdaftar: 88,709 orang

Sistem ini menyediakan:
  - Paparan dashboard analisis demografi dan sokongan pengundi
  - Pengurusan data pengundi (CRUD) dengan aliran kelulusan (approval queue)
  - Import data Excel secara pukal
  - Survei dan kaji selidik dalam talian
  - Log audit (PDPA compliance) untuk setiap aktiviti pengguna
  - Sistem kawalan akses berdasarkan peranan (Admin, Petugas Padang, Pemerhati)


2. SENI BINA SISTEM SEMASA
================================================================================

  +--------------------+          +-------------------+
  |   Vercel Edge      |          |   Vercel Serverless|
  |   Static Files     |          |   Function         |
  |   (frontend/)      +--------->+   (api/index.py)   |
  +--------------------+          +--------+-----------+
                                           |
                                           v
                                 +-------------------+
                                 |   FastAPI App      |
                                 |   backend/main.py  |
                                 +--------+-----------+
                                           |
                                           v
                                 +-------------------+
                                 |   Supabase         |
                                 |   PostgreSQL       |
                                 |   (DATABASE_URL)   |
                                 +-------------------+

  - Backend: FastAPI dijalankan sebagai Vercel Serverless Function melalui
    api/index.py yang mengimport backend/main.py.
  - Database: Supabase PostgreSQL (bukan SQLite tempatan, bukan Render,
    bukan Neon).
  - Frontend: Static single-page application (PWA) di folder frontend/,
    diserve melalui Vercel.
  - Autentikasi: JWT token-based (python-jose).
  - Routing: Semua laluan /* dihalakan semula ke index.html melalui
    vercel.json untuk menyokong client-side routing.


3. ENVIRONMENT VARIABLES (WAJIB DI VERCEL)
================================================================================

  Berikut adalah senarai pembolehubah persekitaran yang mesti ditetapkan
  di Vercel Project Settings > Environment Variables:

  Nama                   | Wajib | Penerangan
  -----------------------|-------|----------------------------------------------
  DATABASE_URL           | Ya    | Connection string PostgreSQL daripada Supabase.
                          |       | ⚠️ WAJIB menggunakan **Transaction Pooler (Port 6543)**.
                          |       | JANGAN gunakan Direct Connection (Port 5432) kerana
                          |       | infrastruktur Vercel Serverless tidak menyokong
                          |       | sambungan IPv6 asli secara lalai.
                          |       |
                          |       | Format Wajib:
                          |       | postgresql://postgres.[ID]:[PASSWORD]@[HOS-POOLER]:6543/postgres?sslmode=require
  -----------------------|-------|----------------------------------------------
  JENTERA_PRODUCTION     | Ya    | "true" untuk production mode (menghidupkan
                         |       | static file serving, CORS terhad, tiada
                         |       | source maps).
                         |       | "false" atau kosong untuk development.
  -----------------------|-------|----------------------------------------------
  JENTERA_ALLOWED_ORIGINS| Ya    | Senarai asal yang dibenarkan untuk CORS,
                         |       | dipisahkan dengan koma.
                         |       | Contoh: http://localhost:3000,https://
                         |       | jentera-pintar-p170-tuaran.vercel.app
  -----------------------|-------|----------------------------------------------

  NOTA: Fail .env di root folder digunakan untuk pembangunan tempatan
  (development) sahaja. Jangan masukkan .env ke dalam Vercel deployment.


4. LOG SEJARAH PENYELESAIAN ISU UTAMA (BUG FIX HISTORY)
================================================================================

  4.1 Ralat 404 Routing (Client-side Routing)
  --------------------------------------------------------------------
  ISU    : Apabila deploy ke Vercel, halaman selain '/' (contohnya
           /dashboard, /pengundi) memaparkan ralat 404.
  PUNCA  : Vercel tidak mengenali routing client-side SPA. Hanya index.html
           di root yang diserve secara lalai.
  PENYELESAIAN: Menambah konfigurasi rewrites dalam vercel.json untuk
           menghalakan SEMUA laluan (/**) kepada index.html.

  Fail: vercel.json
  Sumber Rujukan: DEPLOYMENT.md


  4.2 Penukaran Kod Render ke Vercel Serverless
  --------------------------------------------------------------------
  ISU    : Sistem asal dibina untuk di-deploy ke Render (Gunicorn + Uvicorn)
           sebagai service berterusan. Vercel memerlukan fungsi serverless.
  PUNCA  : Render menjalankan app sebagai process berterusan, manakala Vercel
           menjalankan fungsi yang di-trigger oleh HTTP request secara individu.
  PENYELESAIAN:
     - Mencipta api/index.py sebagai entry point Vercel Serverless.
     - Memastikan FastAPI app diimport daripada backend/main.py.
     - Menanggalkan kebergantungan kepada Render (render.yaml dipadam).
     - Menyesuaikan konfigurasi CORS dan static file serving untuk
       berfungsi dalam persekitaran serverless.

  Fail: api/index.py, backend/main.py, vercel.json


  4.3 ModuleNotFoundError: No module named 'database' (Python Import Path)
  --------------------------------------------------------------------
  ISU    : Apabila Vercel Serverless Function dijalankan dari root directory,
           Python gagal mencari modul tempatan di dalam folder backend/.
           Ralat: "ModuleNotFoundError: No module named 'database'"
  PUNCA  : backend/main.py menggunakan import relatif (from database import ...,
           from auth import ..., from config import ...) yang tidak berfungsi
           apabila diimport sebagai sebahagian daripada pakej Vercel Serverless.
  PENYELESAIAN:
     - Mencipta backend/__init__.py untuk menjadikan backend/ sebagai pakej
       Python yang sah.
     - Menambah sys.path ke folder backend/ dalam api/index.py sebagai
       laluan fallback tambahan.
     - Menukar SEMUA import dalaman di backend/main.py kepada import mutlak:
         * from database import ...  → from backend.database import ...
         * from auth import ...      → from backend.auth import ...
         * from config import ...    → from backend.config import ...
         * from seed_data import ... → from backend.seed_data import ...

  Fail: backend/__init__.py, api/index.py, backend/main.py
  Commit: 7cbe56a


  4.4 Ralat Kegagalan Startup / Sekatan Rangkaian IPv6 Supabase (Serverless Pooler Fix)
  --------------------------------------------------------------------
  ISU    : Apabila pengguna cuba log masuk, portal memaparkan ralat merah:
           "Unexpected token 'A', \"A server e\"... is not valid JSON"
           dan Log Vercel menunjukkan status "POST 500" dengan mesej
           "Application startup failed. Exiting."
  PUNCA  : Fungsi Vercel Serverless dijalankan di atas persekitaran rangkaian yang
           tidak menyokong IPv6 asli secara lalai. Pautan "Direct Connection" asal
           daripada Supabase (Port 5432) memaksa penggunaan IPv6, menyebabkan
           skrip FastAPI gagal membina jabat tangan (handshake) pangkalan data
           semasa aplikasi dimulakan.
  PENYELESAIAN:
     - Mengubah konfigurasi sambungan di bawah menu "🔌 Connect" di Supabase
       daripada 'Direct connection' kepada 'Transaction pooler'.
     - Menukar alamat hos sambungan kepada kluster IPv4 pooler rasmi
       (aws-0-ap-southeast-1.pooler.supabase.com) dan menukar port ke **6543**.
     - Memastikan parameter `?sslmode=require` diletakkan di penghujung string
       sambungan di dalam fail konfig atau pembolehubah persekitaran Vercel.
     - Menggantikan placeholder teks `[YOUR-PASSWORD]` dengan kata laluan pangkalan
       data pengeluaran (production) yang sah sebelum melakukan proses 'Redeploy'
       di Vercel tanpa cache.

   Fail Terlibat : Vercel Environment Variables (DATABASE_URL), backend/database.py
   Tarikh Isu    : Julai 2026


   4.5 Skrin Putih (Blank Screen) — Template Literal JavaScript Tidak Ditutup
   --------------------------------------------------------------------
   ISU    : Selepas menyuntik kod HTML untuk Canvas N12 Sulaman, dashboard
            menjadi skrin putih sepenuhnya tanpa sebarang ralat di konsol.
   PUNCA  : Template literal `content.innerHTML = \`...\`` tidak ditutup
            dengan backtick (\`) sebelum `setTimeout()`. JavaScript parser
            gagal membaca keseluruhan fungsi renderDashboard(), menghasilkan
            runtime crash senyap.
   PENYELESAIAN: Menambah backtick penutup \`;\` selepas blok HTML N12 card.
            Semua guard clause dan try/catch sedia ada sudah memadai.

   Fail: frontend/index.html
   Commit: 6059f47


   4.6 Ralat "A server error" / "Internal Server Error" — Tiada Global Exception Handler
   --------------------------------------------------------------------
   ISU    : Apabila startup function gagal (contoh sambungan database),
            FastAPI mengembalikan plain text error dan bukannya JSON.
   PUNCA  : Function `startup()` tidak dibalut dengan try/except global.
            Tiada `@app.exception_handler(Exception)` untuk menangkap
            sebarang unhandled exception.
   PENYELESAIAN:
      - Balut keseluruhan `startup()` dalam try/except global.
      - Tambah `@app.exception_handler(Exception)` di backend/main.py
        yang memulangkan JSONResponse dengan status 500.
      - Pastikan route `/api/dashboard/dun/{dun_kod}` return data fallback
        kosong (bukan HTTPException 500) jika database gagal.

   Fail: backend/main.py
   Commit: 83bab66, 5990662, ebf2437


   4.7 Ralat "Cannot assign requested address" — IPv6 Direct Connection Supabase (Port 5432)
   --------------------------------------------------------------------
   ISU    : Vercel Serverless tidak dapat menyambung ke Supabase melalui
            Direct Connection (port 5432) kerana IPv6 tidak disokong.
            Ralat: `psycopg2.OperationalError: Cannot assign requested address`
   PUNCA  : DATABASE_URL menggunakan domain `db.hgweacgibbnynjviocje.supabase.co`
            yang menyelesaikan ke alamat IPv6. Vercel Serverless tidak
            menyokong IPv6 asli.
   PENYELESAIAN:
      - Force replace domain ke pooler IPv4:
        `db.hgweacgibbnynjviocje.supabase.co` → `aws-0-ap-southeast-1.pooler.supabase.com`
      - Force port 6543 (Transaction Pooler) jika port 5432 dikesan.
      - Tambah tenant identifier: username `postgres` → `postgres.<project_ref>`
        untuk elak ralat "ENOIDENTIFIER: no tenant identifier provided".
      - Balut `psycopg2.connect()` dengan try/except untuk log error.
      - Tambah try/except pada `get_pengguna_dari_db()` di backend/auth.py.

   Fail: backend/database.py
   Commit: 5866e4f, 1dfb833, ffae3ec


   4.8 Auth Isolation — Cipta Modul backend/secure_auth.py
   --------------------------------------------------------------------
   ISU    : Logik autentikasi (login, JWT, password verification) bercampur
            dengan kod dashboard dan pengundi dalam backend/main.py. Ini
            meningkatkan risiko regresi keselamatan (bypass login) apabila
            mengubah suai kod dashboard.
   PUNCA  : Endpoint login, fungsi hash, dan verify berada dalam fail yang
            sama dengan endpoint dashboard dan CRUD pengundi.
   PENYELESAIAN:
      - Cipta fail baharu `backend/secure_auth.py` — modul autentikasi
        terpencil yang hanya mengandungi:
          * `login_endpoint()` — satu-satunya fungsi login
          * `hash_kata_laluan()`, `sahkan_kata_laluan()`, `create_access_token()`
          * `get_pengguna_dari_db()` dengan strict fallback
      - Endpoint login di `backend/main.py` cuma 3 baris:
        `def login(req): return login_endpoint(req.username, req.kata_laluan)`
      - Strict fallback: jika database down, HANYA admin/admin123 dibenarkan.
        Selain itu, semua login ditolak dengan 401.
      - Fallback statik kemudian dibuang sepenuhnya demi keselamatan.

   Fail: backend/secure_auth.py, backend/main.py
   Commit: 4189887, 40dec20


   4.9 Frontend Dynamic Canvas — Drag & Resize (Iterasi 3: Interact.js)
   --------------------------------------------------------------------
   ISU    : Tiga percubaan untuk melaksanakan fungsi drag & resize pada
            dashboard card. Setiap percubaan gagal dan memerlukan eliminasi.
   PERCUBAAN 1 (HTML5 Drag & Drop Manual):
      - Gagal kerana canvas Chart.js menghalang resize handle.
   PERCUBAAN 2 (Gridstack.js CDN):
      - Gagal kerana memerlukan perombakan struktur HTML yang terlalu
        mendalam dan merosakkan susunan asal.
   PERCUBAAN 3 (Interact.js CDN) — BERJAYA ✅:
      - Interact.js ringan, tidak memerlukan perubahan struktur HTML.
      - `interact().draggable()` dengan restrictRect dalam container.
      - `interact().resizable()` dengan edges: right, bottom, bottomRight.
      - `chart.resize()` dipanggil dalam event onresize.
      - LocalStorage auto-save: `dashboardInteractLayout`.
      - Butang toggle "✏️ Ubah Susunan / 🔒 Kunci Susunan".
   STATUS: Dilaksanakan di branch `feature/dynamic-canvas` (belum merge ke main).

   Fail: frontend/index.html
   Commit: 4ccc33a, 53b0422


   4.10 Root Cause Analysis — Layout Persistence Interact.js (Belum Selesai)
   --------------------------------------------------------------------
   LAPORAN BEDAH SIASAT RASMI — Masalah layout Interact.js kembali ke asal
   (reset) selepas page refresh walaupun data localStorage wujud.

   PUNCA UTAMA (3 faktor bergabung):
   1. innerHTML Mental: Fungsi renderDashboard() menggunakan
      content.innerHTML = `...` yang memusnahkan SEMUA elemen DOM
      (termasuk inline styles, dataset.x/y, dan Interact.js listeners)
      setiap kali dashboard di-render. Tiada 'diffing' atau 'morphing' —
      DOM dibina semula dari kosong.

   2. CSS Grid vs Transform: Kad dashboard dibalut dalam grid Tailwind
      (grid-cols-1 lg:grid-cols-3). CSS Grid menggunakan positioning
      relatif/static yang tegar. transform: translate(x, y) hanya offset
      visual — grid tetap mengira semula kedudukan asal, meng-override
      transform selepas layout cycle browser.

   3. Timing Init: Interact.js di-init semula selepas innerHTML,
      tetapi data coordinates perlu di-set semula dari localStorage.
      Jika timing init berlaku SEBELUM CSS Grid selesai layout,
      grid akan meng-override style yang baru diset.

   KONFLIK KOD:
   - Interact.js transform: translate() vs CSS Grid positioning rigid
   - innerHTML mental vs Interact.js event listeners (hilang bersama DOM)
   - Data attributes (dataset.x/y) hilang setiap render

   CADANGAN SOLUSI MUTLAK:
   a) ELIMINASI innerHTML: Gunakan DOM manipulation berperingkat
      (appendChild, replaceChild) atau library morphdom untuk patch
      perubahan tanpa memusnahkan elemen sedia ada.
   b) POSITION ABSOLUTE: Gantikan transform: translate() dengan
      position: absolute + left/top dalam edit mode. Grid layout
      tidak akan meng-override positioning absolute.
   c) LAZY INIT: Init Interact.js dalam window.requestAnimationFrame
      + setTimeout(0) untuk memastikan grid layout selesai.
   d) ALTERNATIF LIBRARY: Guna Guizer atau GridStack yang menyokong
      persistence secara native.

   STATUS: Belum selesai — memerlukan refaktor struktur rendering
   dashboard yang signifikan. Ditangguhkan ke Fasa 3.

   Fail: frontend/index.html, frontend/js/dashboard-layout.js


   4.11 Chart Disappearing on SPA Navigation — Destroy ➔ Null ➔ Recreate Pattern
   --------------------------------------------------------------------
   ISU    : Graf donut "N12 Sulaman - Sokongan Mengikut PDM" dan stacked bar
            chart "Status Sokongan × Klasifikasi Umur" hilang (blank/kosong)
            setiap kali pengguna menavigasi ke menu lain (contoh: Senarai
            Pengundi) dan kembali semula ke Dashboard. Graf pie "P170 Tuaran"
            pula kekal stabil.
   PUNCA (4 faktor bergabung):
      (a) Lifecycle Chart.js tidak dikendalikan: Stacked bar chart dimulakan
          dengan `new Chart(ctx3, ...)` tanpa menyimpan rujukan instans untuk
          dimusnahkan (destroy). Apabila renderDashboard() dipanggil semula,
          instans lama tertinggal dalam memori ('orphan Chart instance'),
          menyebabkan konflik dengan canvas baru.
      (b) Corak `.update()` untuk N12 Chart: Kod asal menggunakan pendekatan
          `state.charts['n12'].update()` untuk mengemas kini data chart lama.
          Kaedah ini meninggalkan rujukan canvas yang stale (stale binding)
          apabila innerHTML memadamkan dan mencipta semula elemen <canvas>
          secara total.
      (c) Eksperimen `replaceChild()` awal: Menggunakan `container.replaceChild()`
          untuk 'force-reset' elemen canvas menyebabkan pemutusan total antara
          rujukan DOM dan objek Chart.js, menjadikan chart tidak dapat di-render
          langsung (blank).
      (d) CSS height tidak konsisten: N12 canvas parent menggunakan `min-h-[250px]`
          (minimum sahaja) berbanding P170 yang guna `h-64` (fixed height).
          Tanpa height tetap, Chart.js kadang-kala gagal mengira dimensi layout,
          menghasilkan canvas 0px tinggi.
   PENYELESAIAN MUTLAK (Standard Wajib Projek):
      (a) Destroy semua instans Chart.js SEBELUM innerHTML di renderDashboard():
          ```
          if (state.chart && typeof state.chart.destroy === 'function')
              state.chart.destroy();
          state.chart = null;
          Object.keys(state.charts).forEach(key => {
              if (state.charts[key]?.destroy) state.charts[key].destroy();
              state.charts[key] = null;
          });
          ```
      (b) Wajib guna corak **"Destroy ➔ Null ➔ Recreate"** untuk SEMUA chart:
          ```
          if (state.charts['n12']?.destroy) state.charts['n12'].destroy();
          state.charts['n12'] = null;
          state.charts['n12'] = new Chart(n12Ctx, { ... });
          ```
          ⚠️ JANGAN GUNA `.update()` — ia menyebabkan stale binding.
          ⚠️ JANGAN GUNA `replaceChild()` — ia memutuskan rujukan canvas.
      (c) Standardkan height parent container: guna `h-64` (fixed height 256px)
          untuk semua container canvas. Jangan guna `min-h-*` atau height auto.
      (d) Timing inisialisasi chart:
          ```
          requestAnimationFrame(() => {
              setTimeout(() => {
                  // Init chart di sini — DOM sudah siap dilukis
              }, 50);
          });
          ```
      (e) Destroy block di bahagian ATAS renderDashboard(), SEBELUM innerHTML.
          Init block di bahagian BAWAH renderDashboard(), SELEPAS innerHTML.
   KESAN   : Ketiga-tiga carta (Pie, Stacked Bar, N12 Doughnut) stabil semasa
             navigasi SPA. Tiada lagi blank chart selepas bertukar menu.
   PENGESANAN: Guna VS Code Debugger — letak Breakpoint pada baris
             `const ctx = document.getElementById('sokonganChart')` dan periksa
             jika elemen null. Jika null, canvas tidak wujud dalam DOM.
   Fail   : frontend/index.html (baris ~897 destroy block, baris ~1057 chart init)
   Branch : debug/chartjs-lifecycle
   Status : SELESAI ✅ — digabungkan ke main


   4.12 Service Worker Cache — Pengecualian Aset CDN Luaran
   --------------------------------------------------------------------
   ISU    : Ralat "TypeError: Failed to fetch" pada aset CDN (Chart.js CDN,
            Tailwind CDN, Interact.js CDN) apabila service-worker.js cuba
            memasukkannya ke dalam senarai STATIC_ASSETS semasa fasa install.
   PUNCA  : Service Worker (PWA) cuba pre-cache URL CDN pihak ketiga yang
            tidak berada di origin yang sama. Ini melanggar same-origin policy
            dalam konteks Cache API.
   PENYELESAIAN:
      - SENARAI HITAM: Semua URL yang bermula dengan `https://cdn.`,
        `https://unpkg.com`, atau protokol mutlak TIDAK BOLEH dimasukkan
        dalam tatasusunan STATIC_ASSETS.
      - Guna saringan: `new URL(asset, self.location.origin).origin ===
        self.location.origin` untuk pastikan hanya aset origin sendiri
        di-cache.
      - Aset CDN (Chart.js, Interact.js, Tailwind) dimuatkan terus dari CDN
        melalui tag <script> — ia diuruskan oleh HTTP cache browser, BUKAN
        oleh Service Worker cache.
      - Strategi: "Network First" untuk halaman utama, "Cache First" untuk
        aset statik tempatan (JS, CSS, imej).
   Fail   : frontend/service-worker.js
   Status : SELESAI ✅


5. PELAN PEMBANGUNAN MENYELURUH (OVERALL DEVELOPMENT PLAN)
================================================================================

  --------------------------------------------------------------------
  FASA 1: INFRASTRUKTUR TERAS & KONFIGURASI KAWASAN (SELESAI ✅)
  --------------------------------------------------------------------

  a) Penyediaan Serverless
     Migrasi sepenuhnya backend Python FastAPI dari pelayan Render ke
     Vercel Serverless Functions (@vercel/python) untuk memotong kos
     pelayan.

  b) Integrasi Database
     Menghubungkan sistem FastAPI secara terus dengan pangkalan data
     Supabase PostgreSQL.

  c) Pembersihan & Migrasi Data
     Memadam struktur data lama DUN N05 Matunggung dan menyuntik masuk
     keseluruhan 88,709 data pengundi rasmi P170 Tuaran mengikut
     4 pecahan DUN (N12 Sulaman, N13 Pantai Dalit, N14 Tamparuli,
     N15 Kiulu).

  d) Penjenamaan Visual & Teks
     Mengemas kini teks antaramuka kepada "JenteraPintar P170 Tuaran"
     dan mengubah suai komponen ikon log masuk mengikut warna identiti
     korporat UPKO (Hijau Laut, Emas, Kilat Merah, Gear Perak).

  e) Pembaikan Bug Kritis
     Menyelesaikan ralat 404 Routing pada Vercel dan membetulkan isu
     ralat laluan ModuleNotFoundError pada skrip Python Serverless.


  --------------------------------------------------------------------
   FASA 2: FUNGSI PENGURUSAN & DASHBOARD VISUAL (SELESAI ✅)
   --------------------------------------------------------------------

   a) Dashboard Statistik Dinamik (✅ Selesai)
      - Kad ringkasan (Jumlah Pengundi, Putih, Hitam, Atas Pagar).
      - Pie chart P170 Tuaran dengan filter DUN (N12-N15).
      - Stacked bar chart "Status Sokongan × Klasifikasi Umur".
      - Card N12 Sulaman dengan carta donut dan dropdown PDM.
      - Dynamic Canvas (Interact.js drag & resize) di branch feature/dynamic-canvas.

   b) Modul Carian Pengundi (✅ Selesai)
      - Bar carian dengan multi-filter: PDM, Lokaliti, Sokongan.
      - Pagination dan edit/padam terus dari senarai.

   c) Sistem Log Masuk Petugas Padang (✅ Selesai)
      - JWT token-based authentication dengan python-jose.
      - Role-based access: Admin, Petugas Padang, Pemerhati.
      - Modul auth terpencil: backend/secure_auth.py.
      - Strict fallback jika database down (admin sahaja).


   --------------------------------------------------------------------
   FASA 3: MODUL LAPANGAN & PENGOPTIMUMAN PWA (SEDANG BERJALAN ⏳)
  --------------------------------------------------------------------

  a) Kemas Kini Status Pengundi
     Membina borang interaktif ringkas untuk petugas padang mengemas
     kini kecenderungan politik pengundi (Sokong / Blacklist /
     Atas Pagar / Luar Kawasan) terus ke database semasa lawatan
     rumah ke rumah.

  b) Sokongan Mod Luar Talian (Offline Caching)
     Mengoptimumkan fail service-worker.js PWA bagi membolehkan
     sistem menyimpan data carian asas secara setempat di dalam
     telefon petugas sekiranya kawasan kampung tersebut mengalami
     gangguan liputan internet.

  c) Eksport Laporan Jentera
     Menyediakan fungsi satu klik untuk Ketua Jentera memuat turun
     laporan statistik status sokongan semasa dalam format .csv atau
     .pdf bagi tujuan mesyuarat strategi.


================================================================================
  © 2026 JenteraPintar P170 Tuaran. Hak cipta terpelihara.
================================================================================