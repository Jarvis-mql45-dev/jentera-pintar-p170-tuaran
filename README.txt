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
                         |       | Contoh: postgresql://user:pass@host:5432/db
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


================================================================================
  © 2026 JenteraPintar P170 Tuaran. Hak cipta terpelihara.
================================================================================