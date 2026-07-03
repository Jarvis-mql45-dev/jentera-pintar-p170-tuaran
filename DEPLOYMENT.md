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