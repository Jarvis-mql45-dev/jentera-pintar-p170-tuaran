# JenteraPintar P170 Tuaran

**Sistem Pengurusan Pengundi & Analisis Pilihan Raya — Parlimen P170 Tuaran**

Single-Page Application (PWA) untuk pengurusan data pengundi, analisis demografi, dan strategi jentera pilihan raya merangkumi 4 kawasan DUN (N12 Sulaman, N13 Pantai Dalit, N14 Tamparuli, N15 Kiulu) dengan jumlah pengundi berdaftar seramai **88,709 orang**.

---

## Technology Stack

| Lapisan | Teknologi |
|---------|-----------|
| **Frontend** | Vanilla JavaScript (SPA dengan Client-Side Rendering), HTML5, CSS3 (Tailwind CDN) |
| **Backend** | Python FastAPI (Vercel Serverless Function) |
| **Database** | Supabase PostgreSQL (Transaction Pooler Port 6543) |
| **Autentikasi** | JWT Token-based (python-jose) |
| **Deployment** | Vercel (Static + Serverless Functions) |
| **PWA** | Service Worker untuk cache offline asas |

## Architecture

```
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
                                  +-------------------+
```

- Backend dijalankan sebagai Vercel Serverless Function melalui `api/index.py` yang mengimport `backend/main.py`.
- Frontend static SPA (PWA) di folder `frontend/`, diserve melalui Vercel.
- Routing client-side disokong melalui konfigurasi `vercel.json` yang menghalakan semua laluan ke `index.html`.

## Role & Access Summary

| Peranan | Akses |
|---------|-------|
| **Developer** | Superuser — full akses sistem |
| **Admin (System Preset)** | Pentadbiran penuh, preset sistem |
| **Admin (Custom)** | Pentadbiran penuh, custom |
| **Petugas 1 (System Preset)** | Urus pengundi & data lapangan |
| **Petugas 1 (Pegawai Penyelaras)** | Urus pengundi & data lapangan |
| **Petugas 2 (Ketua Keluarga)** | Lihat & kemaskini KK |
| **Pemerhati** | Lihat sahaja |

### Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| `developer` | `dev123` | Developer |
| `admin` | `admin123` | Admin (System Preset) |
| `petugas` | `petugas123` | Petugas 1 (System Preset) |
| `ketuafamily` | `family123` | Petugas 2 (Ketua Keluarga) |
| `pemerhati` | `pemerhati123` | Pemerhati |

---

## Local Development

### Prerequisites
- Python 3.9+
- Node.js 16+ (optional, for PWA testing)

### Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/Jarvis-mql45-dev/jentera-pintar-p170-tuaran.git
   cd jentera-pintar-p170-tuaran
   ```

2. **Create virtual environment & install dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate # Linux/Mac
   pip install -r backend/requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env.local
   ```
   Edit `.env.local` with your Supabase credentials:
   ```
   DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require
   JENTERA_SECRET_KEY=<your-secret-key>
   JENTERA_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

4. **Run Backend**
   ```bash
   cd backend
   python main.py
   ```
   Backend akan berjalan di `http://localhost:8000`.

5. **Access Frontend**
   Buka `frontend/index.html` terus di browser atau gunakan live server.

---

## Deployment

### Deploy to Vercel

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Set environment variables in Vercel:
   - `DATABASE_URL` — connection string Supabase (Transaction Pooler port 6543)
   - `JENTERA_PRODUCTION` — `"true"`
   - `JENTERA_ALLOWED_ORIGINS` — comma-separated origins
   - `JENTERA_SECRET_KEY` — random 32-character key

3. Deploy:
   ```bash
   npx vercel --prod
   ```

### Required Environment Variables (Vercel)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Connection string PostgreSQL Supabase (Transaction Pooler Port 6543) |
| `JENTERA_PRODUCTION` | ✅ | `"true"` untuk production mode |
| `JENTERA_ALLOWED_ORIGINS` | ✅ | Senarai asal CORS yang dibenarkan |

---

## Project Structure

```
/
├── api/
│   └── index.py              # Vercel Serverless entry point
├── backend/
│   ├── main.py               # FastAPI application & endpoints
│   ├── database.py           # Database connection & init
│   ├── auth.py               # JWT auth dependency
│   ├── secure_auth.py        # Auth module (login, hash, verify)
│   ├── config.py             # Settings & configuration
│   ├── seed_data.py          # Sample data seeding
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── index.html            # Main SPA (inline CSS/JS)
│   ├── manifest.json         # PWA manifest
│   ├── service-worker.js     # Service worker
│   ├── logo.png              # Application logo
│   └── js/
│       ├── app.js            # Core application logic
│       ├── dashboard-layout.js # Dashboard layout (Interact.js)
│       └── kpi.js            # KPI module
├── .clinerules               # System SOP & debugging rules
├── .gitignore
├── vercel.json               # Vercel deployment config
└── README.md
```

---

## Key Features

- **Dashboard Analitik**: Pie chart, stacked bar chart, donut chart PDM
- **Panel Strategi**: 4 DUN PDM tables + Parlimen Mirror Table dengan live input turnout, multiplier, KK ratio
- **Senarai Pengundi**: Multi-filter carian (PDM, Lokaliti, Sokongan, KK, Pegawai) dengan pagination
- **CRUD Pengundi**: Tambah/Edit/Padam dengan approval queue untuk non-admin
- **Import Excel**: Muat naik data pengundi secara pukal
- **Pengurusan Pengguna**: Role-based access control dengan 7 peringkat hierarki
- **Log Aktiviti**: Audit trail untuk pematuhan PDPA
- **PWA**: Service worker caching untuk offline capability asas
- **Soal Selidik**: Cipta & edar borang survey dalam talian

---

## Development Rules

1. **Branching**: Cipta branch dari `main` sebelum memulakan fungsi baharu atau pembaikan bug. Format: `debug/nama-isu` atau `feature/nama-ciri`.
2. **Debugging**: Gunakan VS Code Debugger (`launch.json`) — `console.log()` dibenarkan hanya untuk debugging aktif.
3. **Data Sensitivity**: Semua data sensitif dan API keys disimpan di `.env.local`, DILARANG push ke GitHub.
4. **Database First**: Gunakan query SQL `JOIN` dari Supabase — elakkan hardcoded mapping.
5. **Safe Refactoring**: Jangan padam objek pemetaan/fungsi fallback secara global tanpa pengesahan modul lain tidak bergantung padanya.

---

## License & Credits

© 2026 JenteraPintar P170 Tuaran. Hak cipta terpelihara.

Powered by **Jarvis_KM** | Contact: jarvis_mql45dev@proton.me | Telegram: [@Jarvis_KM](https://t.me/Jarvis_KM)