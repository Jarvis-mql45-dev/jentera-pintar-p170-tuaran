# Panduan Deployment - JenteraPintar N05 Matunggong

## 📋 Pengenalan

Dokumen ini menerangkan langkah-langkah untuk men-deploy aplikasi **JenteraPintar N05 Matunggong** untuk versi **percubaan (trial)** kepada klien. Ianya merangkumi proses build (minification + obfuscation), deployment, dan langkah-langkah keselamatan.

---

## 🔧 Prasyarat

### Sistem Operasi
- Windows 10/11, Linux (Ubuntu 20.04+), atau macOS
- Minimum 2GB RAM, 1GB ruang storage

### Perisian Diperlukan
| Perisian | Versi Minimum | Tujuan |
|----------|---------------|--------|
| Python | 3.9+ | Backend & Build |
| Node.js | 16+ (optional) | Untuk alternatif minification |
| Git | 2.x (optional) | Version control |

### Pakej Python
```bash
# Pakej utama
pip install fastapi uvicorn python-jose passlib bcrypt pydantic
pip install pandas openpyxl python-multipart

# Pakej untuk build (minification + obfuscation)
pip install html-minifier-terser javascript-obfuscator csscompressor
```

---

## 🏗️ Proses Build

### Langkah 1: Build Frontend

Build script akan:
- ✅ **Minify** HTML, CSS, dan JavaScript
- 🔒 **Obfuscate** JavaScript (logik perniagaan dikaburkan)
- 🗑️ **Buang** semua source maps
- 🛡️ Cipta fail konfigurasi keselamatan (`.htaccess`, `web.config`, `robots.txt`)

#### Command:

```bash
# Build production (dengan obfuscation - disarankan)
python build.py

# Build development (minify saja, tanpa obfuscation)
python build.py --dev

# Build production + terus jalankan backend
python build.py --serve
```

### Langkah 2: Konfigurasi Environment

1. Salin `.env.example` ke `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` dan isi nilai production:
   ```env
   JENTERA_PRODUCTION=true
   JENTERA_SECRET_KEY=<guna-kunci-rawak-32-aksara>
   JENTERA_ALLOWED_ORIGINS=https://domain-klien.com
   ```

   > **💡 Jana kunci rahsia:**
   > - **Windows PowerShell:** `[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))`
   > - **Linux/Mac:** `openssl rand -hex 32`

### Langkah 3: Jalankan Backend

```bash
cd backend
python main.py
```

Backend akan:
- Serve API endpoints di `http://0.0.0.0:8000`
- Dalam production mode, serve static files dari `frontend/dist/`
- Auto-load konfigurasi dari `.env`

---

## 🔒 Perlindungan Hak Cipta Intelek

### 1. Logik Kritikal di Server-Side ✅

| Komponen | Lokasi | Logik |
|----------|--------|-------|
| Pengiraan KPI Dashboard | `backend/main.py` (API `/api/dashboard`) | Server-side |
| Validasi Data Pengundi | `backend/main.py` (API endpoints) | Server-side |
| Approval Workflow | `backend/main.py` (API `/api/approval-queue/*`) | Server-side |
| Import Excel Validation | `backend/main.py` (API `/api/pengundi/import-excel`) | Server-side |
| Audit Trail (PDPA) | `backend/main.py` (setiap endpoint) | Server-side |

### 2. Obfuscation 🔐

Build script menggunakan **javascript-obfuscator** untuk:
- Menukar nama variable kepada nama rawak (contoh: `state` → `_0x2a1b3c`)
- Menyembunyikan string-string sensitif (encoding base64)
- Memecah logik kepada bahagian kecil yang sukar dibaca
- **BUKAN** encryption - tetapi sangat menyukarkan pembacaan kod

### 3. Source Maps 🗺️

Source maps di **PADAM** secara automatik semasa production build.
Ini memastikan:
- ❌ Tiada akses kepada kod sumber asal dari browser
- ❌ Tiada debugging tools boleh melihat kod asal
- ✅ Hanya kod obfuscated yang dihantar ke client

### 4. Konfigurasi Sensitif 🔑

- `SECRET_KEY` JWT tidak lagi hardcoded dalam kod
- Diambil dari environment variables (`.env`)
- Fail `.env` TIDAK termasuk dalam distribution
- Contoh disediakan sebagai `.env.example` sahaja

---

## 📂 Struktur Output Build

Selepas build, folder `frontend/dist/` mengandungi:

```
frontend/dist/
├── index.html              # HTML yang diminify + JS diobfuscate
├── service-worker.js       # Service worker diobfuscate
├── manifest.json           # PWA manifest (asal)
├── icons/                  # Ikon aplikasi
│   ├── icon-192x192.png
│   └── icon-512x512.png
├── .htaccess               # Konfigurasi Apache (blok fail sensitif)
├── web.config              # Konfigurasi IIS
├── robots.txt              # Blok crawlers dari fail sensitif
└── build_info.json         # Info build (metadata)
```

---

## 🚀 Deployment ke Pelayan

### Pilihan A: Deployment Asas (Single Server)

```bash
# 1. Build
python build.py

# 2. Copy ke server
scp -r backend/ user@server:/app/backend/
scp .env user@server:/app/.env

# 3. Di server, set env dan run
cd /app
python backend/main.py
```

### Pilihan B: Deployment dengan Nginx Reverse Proxy

**Nginx Configuration:**
```nginx
server {
    listen 443 ssl;
    server_name domain-klien.com;

    ssl_certificate /etc/ssl/certs/domain.crt;
    ssl_certificate_key /etc/ssl/private/domain.key;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Block source maps
    location ~* \.map$ {
        deny all;
        return 404;
    }

    # Block python files
    location ~* \.py$ {
        deny all;
        return 404;
    }

    # Block database
    location ~* \.db$ {
        deny all;
        return 404;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Static files (production build)
    location / {
        root /app/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

### Pilihan C: Deployment dengan IIS (Windows Server)

1. Pasang **Application Request Routing (ARR)** dan **URL Rewrite** di IIS
2. Buat website pointing ke `frontend/dist/`
3. Konfigurasi reverse proxy untuk `/api/` ke `http://localhost:8000`
4. `web.config` disediakan secara automatik dalam build

---

## ✅ Checklist Sebelum Serah kepada Klien

- [ ] **Build** - `python build.py` berjaya tanpa error
- [ ] **Konfigurasi** - `.env` diisi dengan betul
- [ ] **SECRET_KEY** - Ditukar daripada nilai lalai
- [ ] **CORS** - Hanya domain klien dibenarkan
- [ ] **Source Maps** - Tiada dalam `frontend/dist/`
- [ ] **API Test** - Semua endpoint berfungsi
- [ ] **Login Test** - Akaun demo berfungsi (admin/admin123)
- [ ] **Log Audit** - Aktiviti direkod dengan betul
- [ ] **PWA** - Service worker berdaftar
- [ ] **Mobile View** - Responsif di telefon

---

## ⚠️ Nota Keselamatan Tambahan

1. **Tukar kata laluan lalai** sebaik sahaja deploy
2. **Hadkan akses IP** ke port backend (8000) - hanya localhost
3. **Gunakan HTTPS** - wajib untuk production
4. **Backup database** secara berkala
5. **Pantau audit log** untuk aktiviti mencurigakan
6. **Kemas kini dependensi** secara berkala

---

## 📞 Sokongan

Untuk sebarang isu atau pertanyaan:
- **Dokumentasi teknikal**: Rujuk kod sumber dalam folder `backend/`
- **Hak cipta**: © 2026 Jarvis_KM. Hak cipta terpelihara.

---

*Panduan ini untuk kegunaan deployment versi trial. Pastikan semua langkah keselamatan dipatuhi.*

---

# 🚀 RUNBOOK DEPLOYMENT VERCEL + SUPABASE (Kemas kini 2026-09-22)

> ⚠️ Bahagian di atas adalah panduan **lama** (build/obfuscation/IIS/Nginx/N05 Matunggong).
> Bahagian ini adalah prosedur **SEBENAR** untuk production
> **https://jentera-pintar-p170-tuaran.vercel.app** (Vercel Static + Python serverless + Supabase PostgreSQL).
> Nota: kod yang di-deploy = **working tree lokal** (Vercel CLI), bukan hanya apa yang di-commit.

## 1. Environment Variables di Vercel (Production)

| Nama | Nilai / Nota |
|---|---|
| `DATABASE_URL` | Connection string Supabase. **Salin dari Supabase → Connect → `Transaction pooler`.** Format: `postgresql://postgres.<PROJECT_REF>:<PASSWORD>@<POOLER_HOST>:6543/postgres?sslmode=require`. Projek ini disahkan pada `aws-0-ap-southeast-1.pooler.supabase.com:6543` (2026-09-22). |
| `JENTERA_PRODUCTION` | `true` |
| `JENTERA_SECRET_KEY` | kunci JWT rahsia (jangan kongsi) |
| `JENTERA_TOKEN_EXPIRE_HOURS` | `24` |
| `JENTERA_ALLOWED_ORIGINS` | `https://jentera-pintar-p170-tuaran.vercel.app,http://localhost:3000` |
| `NEXT_PUBLIC_SUPABASE_URL` *(pilihan)* | `https://<PROJECT_REF>.supabase.co` — belum digunakan oleh kod (vanilla JS + FastAPI); simpan untuk rujukan. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` *(pilihan)* | Kunci publishable/anon — selamat didedahkan. RLS (`backend/enable_rls.sql`) menghalang bacaan jadual melalui kunci ini. |

⚠️ **Jangan commit `.env` / `.env.local`** (kedua-duanya dalam `.gitignore`).
`NEXT_PUBLIC_*` **BUKAN** kredential DB — sambungan backend kekal guna `DATABASE_URL`.

## 2. Sahkan sambungan DB SEBELUM deploy (WAJIB)

```bash
python backend/check_db.py             # uji sambungan + bilangan baris setiap jadual
python backend/check_db.py --selftest  # ujian offline parsing DSN (tiada rangkaian)
python backend/check_db.py --init      # hanya untuk DB baharu: bina skema + seed parlimen/dun/pdm
```
Output mesti menunjukkan `✅ SAMBUNGAN DB BERJAYA` sebelum teruskan.

## 3. Deploy ke production

```bash
npx vercel login          # sekali sahaja pada mesin baharu (interaktif)
npx vercel --prod         # deploy working tree lokal ke production
```
Alternatif tanpa login interaktif (token, boleh revoke selepas siap):
```powershell
$env:VERCEL_TOKEN = "<token-dari-vercel.com/account/tokens>"
npx vercel --prod --token $env:VERCEL_TOKEN --yes
Remove-Item Env:\VERCEL_TOKEN   # bersihkan selepas deploy
```

## 4. Kemas kini env var tanpa dashboard

```bash
npx vercel env ls production        # senarai NAMA sahaja (nilai tidak dipaparkan)
npx vercel env rm DATABASE_URL production
"postgresql://postgres.<REF>:<PWD>@<HOST>:6543/postgres?sslmode=require" | npx vercel env add DATABASE_URL production
npx vercel --prod                   # env baru HANYA terpakai pada deployment BAHARU
```

## 5. Pengesahan selepas deploy (PowerShell, tanpa browser)

```powershell
$B = 'https://jentera-pintar-p170-tuaran.vercel.app'
$tok = (curl.exe -s -X POST "$B/api/login" -H "Content-Type: application/json" `
        -d '{\"username\":\"admin\",\"kata_laluan\":\"admin123\"}' | ConvertFrom-Json).access_token
foreach ($ep in @('/api/dashboard','/api/pdm','/api/approval-queue/list?page=1&per_page=1')) {
    curl.exe -sS -o NUL -w "$ep -> %{http_code} | %{size_download} bait | %{time_total}s`n" `
      -H "Authorization: Bearer $tok" "$B$ep"
}
```
**Jangkaan: SEMUA 200.** Rujukan saiz payload sah (2026-09-22): `/api/dashboard` ≈ 8,228 bait ·
`/api/pdm` ≈ 2,779 bait · `/api/approval-queue/list?per_page=1` ≈ 59 bait.

## 6. Ralat lazim & punca (dari kes sebenar 2026-09-22)

| Gejala | Punca | Tindakan |
|---|---|---|
| `500` + `FATAL: (ENOTFOUND) tenant/user postgres.<ref> not found` | Projek Supabase **dipause / dipadam**, ATAU host cluster pooler salah (`aws-0` BUKAN default selamat — projek boleh dapat `aws-1`/`aws-2`) | Unpause projek (Dashboard → Restore). Salin **semula** connection string dari Connect → pooler. Jika ragu, uji beberapa host cluster. |
| `500` + `{"error":"Internal Server Error","details":"...","type":"..."}` | Exception tidak dibalut dalam endpoint (`/api/pdm`, `/api/approval-queue/*`) → ditangkap `@app.exception_handler` di `backend/main.py` | Baca `details` (bukan `detail`). |
| `/api/dashboard` `500` + `{"detail":"OperationalError: ..."}` | Exception dalam endpoint dashboard | Mesej penuh ada dalam `detail`. |
| Login **semua** pengguna `503` + `"Pangkalan data tidak dapat dihubungi..."` | **Dijangka sejak FASA 4** — DB tidak dapat dihubungi; `secure_auth.login_endpoint()` memulangkan 503 dan TIADA token diterbitkan | Betulkan DB (seksyen 1 & 7). Sebelum FASA 4, `admin/admin123` masih "berjaya" log masuk tanpa DB (sesi Admin palsu) — tingkah laku itu telah DIBUANG. |
| Login `401` `"Nama pengguna atau kata laluan tidak sah"` | Kredensial salah **atau** pengguna tidak aktif (`aktif = 1`) | Mesej sengaja generik (elak user enumeration). Semak jadual `users`; akaun lalai disenaraikan dalam `README.md`. |
| Warning `cdn.tailwindcss.com should not be used in production` | Play CDN memang `console.warn()` tanpa syarat — `suppressWarnings: true` **tidak** berkesan | Bukan ralat. Penyelesaian sebenar: bina CSS Tailwind (CLI) dan buang CDN. |
| `UnicodeEncodeError: 'charmap' codec...` semasa `python main.py` | Konsol Windows cp1252 tidak boleh encode emoji yang dicetak ke **stdout** | `python -X utf8 -m uvicorn backend.main:app --port 8000` atau `chcp 65001`. Di Vercel (Linux/UTF-8) tiada masalah. |

## 7. Prosedur jika projek Supabase perlu dibina semula

1. Cipta projek Supabase baharu (region `ap-southeast-1`).
2. Salin connection string `Connect → Transaction pooler` → kemas kini `.env` **dan** env Vercel `DATABASE_URL`.
3. `python backend/check_db.py --init` → bina skema + seed parlimen (P170) + 4 DUN (N12–N15).
4. Buka app sekali (atau hit `/api/login`) → startup event seed pengguna lalai
   (developer/admin/petugas/ketuafamily/pemerhati).
5. Import semula data pengundi melalui menu **Import Excel** (`/api/pengundi/import-excel`)
   dari `DUN N12 SULAMAN/SENARAI PENGUNDI SULAMAN.xlsx` dan seumpamanya.
6. **JANGAN** jalankan `backend/seed_data.py` ke production — ia memasukkan 10 pengundi **DUMMY**.

---

## 8. Tailwind CSS — build statik (FASA 3)

Play CDN (`cdn.tailwindcss.com`) telah **DIBUANG** — ia untuk pembangunan sahaja (amaran konsol
+ ~407 KB JS + JIT di dalam pelayar). Kini CSS dibina secara statik:

| Fail | Peranan |
|---|---|
| `tailwind.config.js` | Konfigurasi: `content` glob (`frontend/index.html` + `frontend/js/**/*.js`) + palet `primary` |
| `frontend/css/input.css` | **Sumber** (`@tailwind base; components; utilities;`) |
| `frontend/css/tailwind.css` | **HASIL BUILD — DI-COMMIT ke repo**, dimuatkan oleh `index.html` (22 KB · 4.9 KB gzip) |

```bash
npm install            # sekali sahaja (devDependencies: tailwindcss 3.4.17 — sama versi seperti CDN dahulu)
npm run css:build      # bina minified → frontend/css/tailwind.css
npm run css:watch      # mod pembangun (auto rebuild)
```

⚠️ **Setiap kali kelas Tailwind diubah** dalam `frontend/index.html` atau `frontend/js/*.js`,
jalankan `npm run css:build` dan **COMMIT** `frontend/css/tailwind.css` — jika tidak, kelas
baharu tidak akan wujud di production (Vercel tiada build step Node untuk aset frontend).

⚠️ Naikkan `?v=` pada `<link rel="stylesheet" href="css/tailwind.css?v=1">` untuk paksa
pelayar/PWA refresh (service worker menggunakan cache-first untuk aset bukan-JS).

⚠️ **POSISI `<link>` itu SENGAJA** diletakkan selepas KEDUA-DUA blok `<style>` dalam `index.html`
(meniru kedudukan Play CDN yang menyuntik CSS-nya di hujung `<head>`) supaya susunan
cascade + preflight kekal **sama** seperti sebelum ini. Jangan pindahkannya ke atas tanpa
ujian A/B visual — susunan preflight boleh mengubah padding input (0px→8px) dan radius.

**Pengesahan (A/B Playwright):** **0.000% perbezaan piksel** pada 7 screenshot (login + dashboard
@ 375/768/1280 px, termasuk full-page desktop) dan semua computed style sama, dengan amaran
konsol Tailwind **hilang**; data 88,208 pengundi + 4 DUN kekal dirender.

