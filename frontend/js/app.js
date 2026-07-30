// ============================================================
// STATE MANAGEMENT
// ============================================================
function safeParse(str, fallback = null) {
    try { return JSON.parse(str); } catch(e) { return fallback; }
}

// NOTE: state is declared in index.html (inline script) — DO NOT redeclare const state here
// The inline script runs first and defines all 22 properties.
// See plan: plans/fix-page-persistence-on-refresh.md

// ============================================================
// PDM-TO-DUN MAPPING untuk P170 Tuaran
// ============================================================
// PDM_BY_DUN, PDM_DUN_MAP, getDunForPdm — diisytiharkan dalam index.html inline script,
// jadi ia global dan tidak perlu diisytiharkan semula di sini.
// ============================================================

function groupPdmByDun(pdmList) {
    const groups = {};
    const order = ["N12 SULAMAN", "N13 PANTAI DALIT", "N14 TAMPARULI", "N15 KIULU"];
    order.forEach(dun => groups[dun] = []);
    pdmList.forEach(pdm => {
        const pdmNama = (typeof pdm === 'string' ? pdm : (pdm.nama || ''));
        const dun = getDunForPdm(pdmNama);
        if (dun && groups[dun] && !groups[dun].includes(pdmNama)) {
            groups[dun].push(pdmNama);
        }
    });
    order.forEach(dun => { if (groups[dun].length === 0) delete groups[dun]; });
    return { groups, order: order.filter(dun => groups[dun]) };
}

function renderGroupedPdmOptions(pdmList, selectedValue, selectedDun) {
    const pdmNames = pdmList.map(p => typeof p === 'string' ? p : p.nama);
    const { groups, order } = groupPdmByDun(pdmList);
    let html = '';
    order.forEach(dun => {
        const dunKod = dun.split(' ')[0]; // "N12 SULAMAN" -> "N12"
        const dunSel = dunKod === selectedDun ? ' selected' : '';
        html += `<option value="${dunKod}"${dunSel} style="font-weight:bold;background:#f3f4f6;">— ${dun} —</option>`;
        groups[dun].forEach(pdmNama => {
            const sel = pdmNama === selectedValue ? ' selected' : '';
            html += `<option value="${pdmNama}"${sel}>&nbsp;&nbsp;${pdmNama}</option>`;
        });
    });
    return html;
}

// ============================================================
// API HELPER — API_BASE diisytiharkan dalam index.html inline script (global)
// ============================================================

async function api(path, options = {}) {
    // 🛡️ POKA-YOKE: Early return jika tiada token — elak 403/401 yang tidak perlu
    if (!state.token) {
        return null;
    }
    const headers = { 'Content-Type': 'application/json' };
    headers['Authorization'] = `Bearer ${state.token}`;
    try {
        const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
        const data = await res.json();
        // POKA-YOKE: Auto-redirect login on 401, 403 or any auth error
        if (!res.ok) {
            const errMsg = data.detail || 'Ralat berlaku';
            // Check for auth failures: 401, 403, or message contains auth keywords
            if (res.status === 401 || res.status === 403 || 
                errMsg.includes('Not authenticated') || 
                errMsg.includes('Token') || 
                errMsg.includes('token') || 
                errMsg.includes('tamat tempoh') ||
                errMsg.includes('Kebenaran') ||
                errMsg.includes('kebenaran')) {
                state.token = null;
                state.user = null;
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                renderLoginPage();
                return null; // NEVER throw - graceful redirect
            }
            throw new Error(errMsg);
        }
        return data;
    } catch (err) {
        // 🛡️ POKA-YOKE: If logout is in progress or token already cleared, silently abort
        if (window._logoutGuard || (!state.token && !state.user)) {
            return null; // Stale callback from before logout — discard silently
        }
        if (err.message.includes('Failed to fetch')) {
            showToast('Gagal menyambung ke pelayan. Pastikan backend sedang berjalan.', 'error');
        }
        // Double-check in catch for any auth-related error text
        if (err.message.includes('Not authenticated') || 
            err.message.includes('Token') || 
            err.message.includes('token') || 
            err.message.includes('tamat tempoh') ||
            err.message.includes('Kebenaran') ||
            err.message.includes('kebenaran')) {
            state.token = null;
            state.user = null;
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            renderLoginPage();
            return null;
        }
        throw err;
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

async function handleLogin(username, password) {
    try {
        const res = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, kata_laluan: password })
        });
        const data = await res.json();
        
        if (!res.ok) {
            throw new Error(data.detail || 'Ralat berlaku');
        }
        
        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        renderApp();
        showToast(`Selamat datang, ${data.user.nama_penuh}!`);
    } catch (err) {
        console.error("❌ Auth error response:", err);
        showToast(err.message, 'error');
    }
}

function handleLogout() {
    // 🛡️ CRITICAL: Set logout guard FIRST to block any stale async callbacks mid-flight
    window._logoutGuard = true;
    // 🛡️ Clear ONLY auth-related keys — preserve layout settings (dashboardInteractLayout, etc.)
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('currentPage');
    // Reset in-memory state to prevent any async callbacks from using stale values
    state.token = null;
    state.user = null;
    state.currentPage = 'dashboard';
    // 🛡️ Use location.href instead of location.reload() to force a NEW navigation request
    window.location.href = '/';
}

function requiresAuth() { return !!(state.token && state.user); }

function checkAdmin() { return state.user?.peranan?.startsWith('Admin') || state.user?.peranan === 'Developer'; }
function checkPemerhati() { return state.user?.peranan === 'Pemerhati'; }
function checkPetugas1() { return state.user?.peranan === 'Petugas 1 (System Preset)' || state.user?.peranan === 'Petugas 1 (Pegawai Penyelaras)'; }
function checkPetugas2() { return state.user?.peranan === 'Petugas 2 (Ketua Keluarga)'; }
function checkDeveloper() { return state.user?.peranan === 'Developer'; }
function checkAdminOrDeveloper() { return checkAdmin() || checkDeveloper(); }

// ============================================================
// RENDER FUNCTIONS
// ============================================================

function renderLoginPage() {
    // 🛡️ LOCK BODY: kill scrollbars, apply CSS class to force full-viewport centering
    document.body.style.overflow = 'hidden';
    const appEl = document.getElementById('app');
    if (appEl) appEl.classList.add('login-active');
    const innerWrapper = appEl?.querySelector('.flex-1');
    // Clear remnant heading text + hide header bar
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) pageTitle.textContent = '';
    const headerBar = document.getElementById('pageTitle')?.closest('.flex.items-center.justify-between');
    if (headerBar) headerBar.style.display = 'none';
    document.getElementById('sidebar').classList.add('hidden');
    const userInfoEl = document.getElementById('userInfo');
    if (userInfoEl) {
        userInfoEl.innerHTML = '';
    } else {
        console.warn("DOM Target 'userInfo' not found!");
    }
    const contentArea = document.getElementById('contentArea');
    if (!contentArea) {
        console.warn("DOM Target 'contentArea' not found!");
        return;
    }
    contentArea.innerHTML = `
        <div class="flex items-center justify-center" style="min-height:100vh;width:100%;">
            <div class="card w-full max-w-[440px] p-10 md:p-12" style="margin:0 auto !important;">
                <div class="text-center mb-8">
                    <img src="logo.png" alt="JenteraPintar Logo" class="w-40 h-40 mx-auto mb-4" onerror="this.style.display='none';">
                    <h2 class="text-2xl font-bold text-gray-800">JenteraPintar</h2>
                    <p class="mt-1" style="font-size:0.95rem;color:#6b7280;">P170 Tuaran</p>
                </div>
                <div class="space-y-5">
                    <div><label class="block mb-1" style="font-size:0.95rem;font-weight:600;color:#374151;">Nama Pengguna</label><input type="text" id="loginUsername" placeholder="Masukkan nama pengguna" value="" autocomplete="off" style="width:100%;padding:12px 16px;font-size:1rem;border:1px solid #d1d5db;border-radius:8px;outline:none;"></div>
                    <div><label class="block mb-1" style="font-size:0.95rem;font-weight:600;color:#374151;">Kata Laluan</label><input type="password" id="loginPassword" placeholder="Masukkan kata laluan" value="" autocomplete="new-password" style="width:100%;padding:12px 16px;font-size:1rem;border:1px solid #d1d5db;border-radius:8px;outline:none;"></div>
                    <button onclick="handleLogin(document.getElementById('loginUsername').value, document.getElementById('loginPassword').value)" class="btn btn-primary w-full" style="height:48px;font-size:1.05rem;font-weight:bold;">Log Masuk</button>
                </div>
                <div class="mt-6 text-center">
                    <p style="font-size:0.85rem;color:#64748b;line-height:1.625;">
                        &copy; 2026 P170 Tuaran. Hak Cipta Terpelihara.<br>
                        Powered by Jarvis_KM | contact: jarvis_mql45dev@proton.me | Telegram: <a href="https://t.me/Jarvis_KM" target="_blank" style="font-size:0.85rem;color:#64748b;" class="hover:text-blue-500 transition">@Jarvis_KM</a>
                    </p>
                </div>
            </div>
        </div>`;
}

function renderSidebar() {
    // Pulihkan body & app container selepas login — remove login centering class
    document.body.style.overflow = '';
    const appEl = document.getElementById('app');
    if (appEl) {
        appEl.classList.remove('login-active');
        appEl.style.display = '';
        appEl.style.justifyContent = '';
        appEl.style.alignItems = '';
        appEl.style.minHeight = '';
        appEl.style.width = '';
        appEl.style.margin = '';
        appEl.style.padding = '';
    }
    const innerWrapper = appEl?.querySelector('.flex-1');
    if (innerWrapper) {
        innerWrapper.style.padding = '';
        innerWrapper.style.display = '';
        innerWrapper.style.justifyContent = '';
        innerWrapper.style.alignItems = '';
        innerWrapper.style.width = '';
    }
    // Pulihkan header bar selepas login
    const headerBar = document.getElementById('pageTitle')?.closest('.flex.items-center.justify-between');
    if (headerBar) headerBar.style.display = '';
    const sidebar = document.getElementById('sidebar');
    const peranan = state.user?.peranan || '';
    sidebar.classList.remove('hidden');
    sidebar.innerHTML = `
        <div class="sidebar-header p-4 border-b">
            <div class="d-flex align-items-center" style="display: flex; align-items: center;">
                <img src="/assets/image_8261c1.png" alt="UPKO Logo" style="height: 42px; margin-right: 10px;" onerror="this.onerror=null; this.src='https://upload.wikimedia.org/wikipedia/ms/3/3d/Logo_UPKO_baru.png';">
                <div>
                    <h1 style="font-size: 16px; font-weight: bold; margin: 0; line-height: 1.2;">JenteraPintar</h1>
                    <small style="font-size: 12px; color: #6c757d; display: block; margin-top: 2px;">P170 Tuaran</small>
                </div>
            </div>
        </div>
        <div class="sidebar-menu p-3">
            <div class="text-xs text-gray-400 uppercase font-semibold mb-2 px-3">Menu Utama</div>
            <button onclick="navigate('dashboard')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='dashboard'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg> Papan Pemuka
            </button>
            <button onclick="navigate('pengundi')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='pengundi'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg> Senarai Pengundi
            </button>
            ${peranan.startsWith('Admin') || peranan==='Developer' ? `
            <button onclick="navigate('approval')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='approval'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Kelulusan Data
                <span id="approvalBadge" class="ml-auto bg-red-500 text-white text-xs px-2 py-0.5 rounded-full hidden">0</span>
            </button>` : ''}
             <!-- PENTADBIRAN: Log Aktiviti & Pengurusan Pengguna – sorok untuk Pemerhati, Petugas 1 & Petugas 2 -->
             ${peranan !== 'Pemerhati' && !checkPetugas1() && !checkPetugas2() ? `
             <div class="text-xs text-gray-400 uppercase font-semibold mb-2 mt-4 px-3">Pentadbiran</div>
             <button onclick="navigate('audit')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='audit'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                 <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg> Log Aktiviti
             </button>
             <button onclick="navigate('users')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='users'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                 <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/></svg> Pengurusan Pengguna
             </button>
             ` : ''}
             <!-- Import Data & Pegawai Penyelaras – tunjuk untuk semua kecuali Petugas 1 & Petugas 2 -->
             ${!peranan.startsWith('Petugas 1') && !checkPetugas2() ? `
             <button onclick="navigate('import')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='import'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                 <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg> Import Data
             </button>
             <button onclick="navigate('pegawai-penyelaras')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='pegawai-penyelaras'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                 <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg> Pegawai Penyelaras
             </button>
             ` : ''}
             <!-- KETUA KELUARGA – tunjuk untuk semua kecuali Petugas 2 -->
             ${!checkPetugas2() ? `
             <button onclick="navigate('ketua-keluarga')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='ketua-keluarga'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                 <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg> Ketua Keluarga
             </button>
             ` : ''}
             <!-- PPU, Soal Selidik, INFO PARTI, SOKONGAN – tunjuk untuk selain Petugas 1 & Petugas 2 -->
             ${!peranan.startsWith('Petugas 1') && !checkPetugas2() ? `
             <button onclick="navigate('kpi')" class="sidebar-item w-full flex items-start gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='kpi'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg> <span style="text-align:left;display:block;line-height:1.4;">Petunjuk Prestasi Utama (PPU)</span>
            </button>
            <div class="text-xs text-gray-400 uppercase font-semibold mb-2 mt-2 px-3">Borang Soal Selidik</div>
            <button onclick="navigate('survey')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='survey'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg> Senarai Soal Selidik
            </button>
            <button onclick="navigate('survey-create')" class="sidebar-item w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='survey-create'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg> Cipta Soal Selidik
            </button>
            <div class="text-xs text-gray-400 uppercase font-semibold mb-2 mt-2 px-3">INFO PARTI</div>
            <button onclick="navigate('berita')" class="sidebar-item w-full flex items-start gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='berita'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/></svg> <span style="text-align:left;display:block;line-height:1.4;">Berita & Amanat</span>
                <span class="ml-auto bg-amber-400 text-amber-900 text-xs px-1.5 py-0.5 rounded-full">Akan Datang</span>
            </button>
            <button onclick="navigate('kalendar')" class="sidebar-item w-full flex items-start gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='kalendar'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg> <span style="text-align:left;display:block;line-height:1.4;">Kalendar Aktiviti</span>
                <span class="ml-auto bg-amber-400 text-amber-900 text-xs px-1.5 py-0.5 rounded-full">Akan Datang</span>
            </button>
            <div class="text-xs text-gray-400 uppercase font-semibold mb-2 mt-2 px-3">SOKONGAN & MAKLUM BALAS</div>
            <button onclick="navigate('aduan')" class="sidebar-item w-full flex items-start gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='aduan'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg> <span style="text-align:left;display:block;line-height:1.4;">Aduan Pengguna</span>
                <span class="ml-auto bg-amber-400 text-amber-900 text-xs px-1.5 py-0.5 rounded-full">Akan Datang</span>
            </button>
            <button onclick="navigate('cadangan')" class="sidebar-item w-full flex items-start gap-3 px-3 py-2.5 rounded-lg mb-1 ${state.currentPage==='cadangan'?'bg-primary-50 text-primary-700 font-medium':'text-gray-600 hover:bg-gray-50'}">
                <svg class="w-5 h-5 flex-shrink-0 mt-0.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg> <span style="text-align:left;display:block;line-height:1.4;">Cadangan Pengguna</span>
                <span class="ml-auto bg-amber-400 text-amber-900 text-xs px-1.5 py-0.5 rounded-full">Akan Datang</span>
            </button>
            ` : ''}
        </div>
        <div class="sidebar-footer border-t p-3">
            <div class="flex items-center gap-3 px-3 py-2">
                <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-sm font-bold text-gray-600">${state.user?.nama_penuh?.charAt(0) || 'U'}</div>
                <div class="flex-1 min-w-0"><p class="text-sm font-medium text-gray-800 truncate">${state.user?.nama_penuh || ''}</p><p class="text-xs text-gray-500">${state.user?.peranan || ''}</p></div>
                <button onclick="handleLogout()" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-red-500" title="Log Keluar">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg></button>
            </div>
            <div class="px-3 py-2 border-t border-gray-100 mt-1">
                <p class="text-xs text-slate-500 text-center leading-relaxed">
                    © 2026 P170 Tuaran. Hak Cipta Terpelihara.<br>
                    Powered by Jarvis_KM | contact: jarvis_mql45dev@proton.me | Telegram: <a href="https://t.me/Jarvis_KM" target="_blank" class="text-xs text-slate-500 hover:text-blue-500 transition">@Jarvis_KM</a>
                </p>
            </div>
        </div>`;
}

function navigate(page) {
    if (!requiresAuth()) { renderLoginPage(); return; }
    
     // 🛡️ ACL ROUTE GUARD: Pemerhati hanya dihalang dari audit (Log Aktiviti) & users (Pengurusan Pengguna)
     if (checkPemerhati()) {
         const blockedPages = ['audit', 'users'];
         if (blockedPages.includes(page)) {
             showToast('Akses Tidak Dibenarkan', 'error');
             page = 'dashboard';
            state.currentPage = page;
            localStorage.setItem('currentPage', page);
        }
    }
    
    // 🛡️ ACL ROUTE GUARD: Petugas 1 hanya boleh akses dashboard, pengundi, ketua-keluarga
    if (checkPetugas1()) {
        const allowedPages = ['dashboard', 'pengundi', 'ketua-keluarga'];
        if (!allowedPages.includes(page)) {
            showToast('Akses Tidak Dibenarkan', 'error');
            page = 'dashboard';
            state.currentPage = page;
            localStorage.setItem('currentPage', page);
        }
    }
    
    // 🛡️ ACL ROUTE GUARD: Petugas 2 hanya boleh akses dashboard & pengundi
    if (checkPetugas2()) {
        const allowedPages = ['dashboard', 'pengundi'];
        if (!allowedPages.includes(page)) {
            showToast('Akses Tidak Dibenarkan', 'error');
            page = 'dashboard';
            state.currentPage = page;
            localStorage.setItem('currentPage', page);
        }
    }
    
    state.currentPage = page;
    localStorage.setItem('currentPage', page);
    renderSidebar();
    document.getElementById('pageTitle').textContent = 
        page==='dashboard'?'Papan Pemuka':page==='pengundi'?'Senarai Pengundi':
        page==='approval'?'Kelulusan Data':page==='audit'?'Log Aktiviti':
        page==='users'?'Pengurusan Pengguna':page==='import'?'Import Data Excel':
        page==='survey'?'Senarai Soal Selidik':page==='survey-create'?'Cipta Soal Selidik':
        page==='survey-view'?'Borang Soal Selidik':
        page==='pegawai-penyelaras'?'Pengurusan Pegawai Penyelaras':
        page==='ketua-keluarga'?'Pengurusan Ketua Keluarga':
        page==='kpi'?'':'Papan Pemuka';
    document.getElementById('sidebar').classList.remove('open');
    if (window.innerWidth < 768) {
        document.getElementById('sidebar').classList.add('closed');
        document.body.classList.remove('no-scroll');
    } else {
        document.getElementById('sidebar').classList.remove('closed');
    }
    
    if (page==='dashboard') {
        try {
            renderDashboard();
        } catch (error) {
            console.error("CRITICAL RENDER CRASH IN APP.JS:", error);
        }
    }
    else if (page==='pengundi') renderPengundi();
    else if (page==='approval') renderApprovalQueue();
    else if (page==='audit') renderAuditLogs();
    else if (page==='users') renderUserManagement();
    else if (page==='import') renderImportData();
    else if (page==='survey') renderSurveyList();
    else if (page==='survey-create') renderCreateSurvey();
    else if (page==='survey-view') renderSurveyView();
    else if (page==='kpi') renderKpi();
    else if (page==='pegawai-penyelaras') renderPegawaiPenyelaras();
    else if (page==='ketua-keluarga') renderKetuaKeluarga();
    else renderComingSoon(page);
}

// ========= SURVEY FUNCTIONS =========

function renderSurveyList() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan senarai...</span></div>';
    api('/api/surveys').then(surveys => {
        const hasSurveys = surveys && surveys.length > 0;
        const html = `
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-gray-800">Senarai Soal Selidik</h3>
                    ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Cipta Baru</button>' : '<button onclick="navigate(\'survey-create\')" class="btn btn-primary text-sm">+ Cipta Baru</button>'}
                </div>
                ${!hasSurveys ? '<div class="text-center py-10 text-gray-400">Tiada soal selidik yet. Klik "Cipta Baru" untuk mulakan.</div>' : `
                <div class="overflow-x-auto">
                    <table>
                        <thead><tr><th>Tajuk</th><th>Penerangan</th><th>Respons</th><th>Dicipta</th><th>Tindakan</th></tr></thead>
                        <tbody>${surveys.map(s => {
                            const qs = typeof s.questions === 'string' ? JSON.parse(s.questions) : (s.questions || []);
                            const qCount = Array.isArray(qs) ? qs.length : 0;
                            return `<tr>
                                <td class="font-medium">${s.title}</td>
                                <td class="text-sm text-gray-500 max-w-xs truncate">${s.description || '-'}</td>
                                <td><span class="badge badge-sah">${s.response_count || 0} respons</span></td>
                                <td class="text-sm">${s.created_at ? new Date(s.created_at).toLocaleDateString('ms-MY') : '-'}</td>
                                <td>
                                    <div class="flex gap-2">
                                        <button onclick="viewSurvey(${s.id})" class="btn btn-primary text-xs py-1 px-2">Lihat</button>
                                        <button onclick="viewSurveyResponses(${s.id})" class="btn btn-outline text-xs py-1 px-2">Respons</button>
                                        <button onclick="copySurveyLink(${s.id})" class="btn btn-warning text-xs py-1 px-2">Salin Pautan</button>
                                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-2 py-1 text-xs border-0">Padam</button>' : '<button onclick="deleteSurvey(' + s.id + ')" class="btn btn-danger text-xs py-1 px-2">Padam</button>'}
                                    </div>
                                </td>
                            </tr>`;
                        }).join('')}</tbody>
                    </table>
                </div>`}
            </div>`;
        requestAnimationFrame(() => {
            content.innerHTML = html;
        });
    }).catch(err => {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    });
}

function viewSurvey(id) {
    state.surveyEditId = id;
    navigate('survey-view');
}

function viewSurveyResponses(id) {
    // OFFLOAD ke setTimeout untuk INP
    setTimeout(() => {
        const content = document.getElementById('contentArea');
        content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan respons...</span></div>';
        Promise.all([
            api(`/api/surveys/${id}`),
            api(`/api/surveys/${id}/responses`)
        ]).then(([survey, responses]) => {
            const qs = typeof survey.questions === 'string' ? JSON.parse(survey.questions) : (survey.questions || []);
            requestAnimationFrame(() => {
                content.innerHTML = `
                    <div class="card">
                        <div class="flex items-center justify-between mb-4">
                            <div><h3 class="font-semibold text-gray-800">Respons: ${survey.title}</h3><p class="text-sm text-gray-500">${responses.length} respons diterima</p></div>
                            <button onclick="navigate('survey')" class="btn btn-outline text-sm">← Kembali</button>
                        </div>
                        ${responses.length === 0 ? '<div class="text-center py-10 text-gray-400">Belum ada respons.</div>' : 
                        responses.map((r, ri) => {
                            const ans = typeof r.answers === 'string' ? JSON.parse(r.answers) : (r.answers || {});
                            return `<div class="mb-4 p-4 bg-gray-50 rounded-lg">
                                <p class="text-xs text-gray-400 mb-2">Respons #${ri+1} · ${r.submitted_at ? new Date(r.submitted_at).toLocaleString('ms-MY') : '-'}</p>
                                ${Array.isArray(qs) ? qs.map(q => `
                                    <div class="mb-2"><p class="text-sm font-medium text-gray-700">${q.question}</p>
                                    <p class="text-sm text-gray-600 ml-2">${ans[q.id] || ans[q.id] === 0 ? (Array.isArray(ans[q.id]) ? ans[q.id].join(', ') : ans[q.id]) : '<span class="text-gray-400">Tiada jawapan</span>'}</p></div>
                                `).join('') : ''}
                            </div>`;
                        }).join('')}
                    </div>`;
            });
        }).catch(err => {
            content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
        });
    }, 0);
}

function copySurveyLink(id) {
    const link = `${window.location.origin}/survey/view/${id}`;
    navigator.clipboard.writeText(link).then(() => {
        showToast('Pautan borang disalin!');
    }).catch(() => {
        setTimeout(() => {
            const textarea = document.createElement('textarea');
            textarea.value = link;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showToast('Pautan borang disalin!');
        }, 0);
    });
}

function deleteSurvey(id) {
    setTimeout(() => {
        if (!confirm('Padamkan soal selidik ini? Semua respons juga akan dipadamkan.')) return;
        api(`/api/surveys/${id}`, { method: 'DELETE' }).then(() => {
            showToast('Soal selidik dipadamkan');
            requestAnimationFrame(() => {
                renderSurveyList();
            });
        }).catch(err => { showToast(err.message, 'error'); });
    }, 0);
}

// ========= CREATE SURVEY =========
// NOTE: surveyDraftQuestions, surveyCreateMode, questionIdCounter — diisytiharkan dalam index.html inline script,
// jadi ia global dan tidak perlu diisytiharkan semula di sini.

function renderCreateSurvey() {
    const content = document.getElementById('contentArea');
    surveyDraftQuestions = [];
    surveyCreateMode = 'manual';
    content.innerHTML = `
        <div class="grid grid-cols-1 gap-6">
            <div class="card">
                <h3 class="font-semibold text-gray-800 mb-4">Cipta Soal Selidik Baru</h3>
                <div class="mb-4"><label class="block text-sm font-medium mb-1">Tajuk</label><input id="surveyTitle" placeholder="Masukkan tajuk soal selidik" class="w-full"></div>
                <div class="mb-4"><label class="block text-sm font-medium mb-1">Penerangan</label><textarea id="surveyDesc" rows="2" placeholder="Penerangan ringkas" class="w-full border border-gray-300 rounded-lg p-2"></textarea></div>
                
                <div class="flex gap-4 mb-6">
                    <label class="flex items-center gap-2 cursor-pointer"><input type="radio" name="surveyMode" value="manual" checked onchange="toggleSurveyMode('manual')" class="w-4 h-4"> <span class="text-sm">Manual</span></label>
                    <label class="flex items-center gap-2 cursor-pointer"><input type="radio" name="surveyMode" value="ai" onchange="toggleSurveyMode('ai')" class="w-4 h-4"> <span class="text-sm">Jana dengan AI</span></label>
                </div>

                <div id="aiSection" class="hidden mb-4">
                    <label class="block text-sm font-medium mb-1">Topik Tinjauan</label>
                    <div class="flex gap-2">
                        <input id="aiPrompt" placeholder="Contoh: Isu air di kawasan P170 Tuaran" class="flex-1">
                        <button onclick="generateWithAI()" class="btn btn-primary">Jana dengan AI</button>
                    </div>
                </div>

                <div id="questionsContainer" class="space-y-4 mb-4">
                    <p class="text-sm text-gray-400 text-center py-4">Belum ada soalan. Tambah soalan secara manual atau guna AI.</p>
                </div>

                <div id="manualAddSection" class="flex gap-2 mb-4">
                    ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Teks Pendek</button><button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Pilihan Tunggal</button><button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Pilihan Pelbagai</button>' : '<button onclick="addQuestion(\'short_text\')" class="btn btn-outline text-sm">+ Teks Pendek</button><button onclick="addQuestion(\'multiple_choice\')" class="btn btn-outline text-sm">+ Pilihan Tunggal</button><button onclick="addQuestion(\'checkboxes\')" class="btn btn-outline text-sm">+ Pilihan Pelbagai</button>'}
                </div>

                ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed w-full rounded-lg px-4 py-2.5 text-sm border-0 font-semibold">Terbitkan Soal Selidik</button>' : '<button onclick="publishSurvey()" class="btn btn-success w-full">Terbitkan Soal Selidik</button>'}
            </div>
        </div>`;
}

function toggleSurveyMode(mode) {
    surveyCreateMode = mode;
    document.getElementById('aiSection').classList.toggle('hidden', mode !== 'ai');
}

async function generateWithAI() {
    const prompt = document.getElementById('aiPrompt').value.trim();
    if (!prompt) { showToast('Sila masukkan topik tinjauan', 'error'); return; }
    try {
        const result = await api('/api/surveys/generate', { method: 'POST', body: JSON.stringify({ prompt }) });
        document.getElementById('surveyTitle').value = result.title;
        document.getElementById('surveyDesc').value = result.description;
        surveyDraftQuestions = result.questions.map((q, i) => ({ ...q, id: `q${i+1}` }));
        renderSurveyQuestions();
        showToast('Soalan berjaya dijana!');
    } catch (err) { showToast(err.message, 'error'); }
}

function addQuestion(type) {
    const qId = `q${questionIdCounter++}`;
    const q = { id: qId, type: type, question: '', required: true, options: type !== 'short_text' ? [''] : undefined };
    surveyDraftQuestions.push(q);
    renderSurveyQuestions();
}

function removeQuestion(id) {
    surveyDraftQuestions = surveyDraftQuestions.filter(q => q.id !== id);
    renderSurveyQuestions();
}

function updateQuestion(id, field, value) {
    const q = surveyDraftQuestions.find(q => q.id === id);
    if (q) q[field] = value;
}

function addOption(qId) {
    const q = surveyDraftQuestions.find(q => q.id === qId);
    if (q && q.options) q.options.push('');
    renderSurveyQuestions();
}

function removeOption(qId, oi) {
    const q = surveyDraftQuestions.find(q => q.id === qId);
    if (q && q.options) q.options.splice(oi, 1);
    renderSurveyQuestions();
}

function renderSurveyQuestions() {
    const container = document.getElementById('questionsContainer');
    if (!container) return;
    if (surveyDraftQuestions.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">Belum ada soalan.</p>';
        return;
    }
    container.innerHTML = surveyDraftQuestions.map((q, qi) => `
        <div class="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div class="flex items-start justify-between mb-2">
                <span class="text-xs font-medium text-gray-500 bg-gray-200 px-2 py-0.5 rounded">Soalan ${qi+1} · ${q.type==='short_text'?'Teks Pendek':q.type==='multiple_choice'?'Pilihan Tunggal':'Pilihan Pelbagai'}</span>
                <button onclick="removeQuestion('${q.id}')" class="text-red-500 hover:text-red-700 text-sm">✕</button>
            </div>
            <input value="${q.question}" onchange="updateQuestion('${q.id}','question',this.value)" placeholder="Taip soalan anda..." class="w-full mb-2">
            <label class="flex items-center gap-2 text-sm text-gray-600 mb-2"><input type="checkbox" ${q.required?'checked':''} onchange="updateQuestion('${q.id}','required',this.checked)"> Wajib diisi</label>
            ${q.options ? q.options.map((opt, oi) => `
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-sm text-gray-400">${oi+1}.</span>
                    <input value="${opt}" onchange="surveyDraftQuestions.find(q=>q.id==='${q.id}').options[${oi}]=this.value" placeholder="Pilihan ${oi+1}" class="flex-1 text-sm">
                    <button onclick="removeOption('${q.id}',${oi})" class="text-red-400 hover:text-red-600 text-xs">✕</button>
                </div>
            `).join('') : ''}
            ${q.options ? `<button onclick="addOption('${q.id}')" class="text-blue-600 text-sm mt-1">+ Tambah Pilihan</button>` : ''}
        </div>
    `).join('');
}

async function publishSurvey() {
    const title = document.getElementById('surveyTitle').value.trim();
    if (!title) { showToast('Sila masukkan tajuk', 'error'); return; }
    if (surveyDraftQuestions.length === 0) { showToast('Sila tambah sekurang-kurangnya satu soalan', 'error'); return; }
    
    const cleanQuestions = surveyDraftQuestions.map(q => {
        if (q.options) q.options = q.options.filter(o => o.trim() !== '');
        return q;
    });

    try {
        const result = await api('/api/surveys', {
            method: 'POST',
            body: JSON.stringify({
                title: title,
                description: document.getElementById('surveyDesc').value.trim(),
                questions: JSON.stringify(cleanQuestions)
            })
        });
        showToast('Soal selidik berjaya diterbitkan!');
        state.surveyEditId = result.id;
        navigate('survey-view');
    } catch (err) { showToast(err.message, 'error'); }
}

// ========= SURVEY VIEW (Google Form Style - Public) =========
function renderSurveyFormHTML(survey, sid) {
    const qs = Array.isArray(survey.questions) ? survey.questions : [];
    let formHtml = qs.map((q, qi) => {
        const req = q.required ? 'required' : '';
        const qId = `ans_${q.id}`;
        if (q.type === 'short_text') {
            return `<div class="mb-6"><label class="block font-medium text-gray-800 mb-1">${qi+1}. ${q.question} ${q.required?'<span class="text-red-500">*</span>':''}</label><input id="${qId}" type="text" ${req} class="w-full border border-gray-300 rounded-lg p-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500" placeholder="Taip jawapan anda..."></div>`;
        } else if (q.type === 'multiple_choice') {
            return `<div class="mb-6"><p class="font-medium text-gray-800 mb-2">${qi+1}. ${q.question} ${q.required?'<span class="text-red-500">*</span>':''}</p>
                ${(q.options||[]).map((opt,oi) => `<label class="flex items-center gap-3 p-3 mb-1 bg-gray-50 rounded-lg cursor-pointer hover:bg-blue-50"><input type="radio" name="${qId}" value="${opt}" ${req} class="w-4 h-4 text-blue-600"><span class="text-sm text-gray-700">${opt}</span></label>`).join('')}</div>`;
        } else if (q.type === 'checkboxes') {
            return `<div class="mb-6"><p class="font-medium text-gray-800 mb-2">${qi+1}. ${q.question} ${q.required?'<span class="text-red-500">*</span>':''}</p>
                ${(q.options||[]).map((opt,oi) => `<label class="flex items-center gap-3 p-3 mb-1 bg-gray-50 rounded-lg cursor-pointer hover:bg-blue-50"><input type="checkbox" name="${qId}" value="${opt}" class="w-4 h-4 text-blue-600"><span class="text-sm text-gray-700">${opt}</span></label>`).join('')}</div>`;
        }
        return '';
    }).join('');

    return `
        <div class="max-w-2xl mx-auto">
            <div class="card mb-4" style="border-top: 8px solid #1e40af;">
                <h2 class="text-xl font-bold text-gray-800 mb-2">${survey.title}</h2>
                <p class="text-sm text-gray-500 mb-4">${survey.description || 'Sila lengkapkan borang di bawah.'}</p>
                <p class="text-xs text-gray-400">Soalan bertanda <span class="text-red-500">*</span> wajib diisi.</p>
            </div>
            <div class="card mb-4">
                <form id="surveyForm" onsubmit="submitSurveyForm(event, ${sid})">
                    ${formHtml}
                    <div class="mt-6 pt-4 border-t">
                        <button type="submit" class="btn btn-primary w-full py-3 text-lg">Hantar</button>
                    </div>
                </form>
            </div>
        </div>`;
}

async function renderSurveyView() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan borang...</span></div>';
    try {
        const sid = state.surveyEditId;
        if (!sid) { content.innerHTML = '<div class="card text-center py-10"><p class="text-red-500">ID borang tidak sah</p></div>'; return; }
        
        const cachedSurvey = localStorage.getItem(`survey_${sid}`);
        let survey;
        
        if (isOnline()) {
            survey = await api(`/api/surveys/${sid}`);
            localStorage.setItem(`survey_${sid}`, JSON.stringify(survey));
        } else if (cachedSurvey) {
            survey = JSON.parse(cachedSurvey);
        } else {
            content.innerHTML = `
                <div class="max-w-2xl mx-auto">
                    <div class="card text-center py-10">
                        <svg class="w-16 h-16 mx-auto text-amber-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                        <p class="text-gray-500">Anda sedang luar talian dan borang ini belum pernah dimuatkan sebelum ini.</p>
                        <p class="text-sm text-gray-400 mt-2">Sila dapatkan sambungan internet untuk memuatkan borang.</p>
                    </div>
                </div>`;
            return;
        }
        
        content.innerHTML = renderSurveyFormHTML(survey, sid);
    } catch (err) {
        const sid = state.surveyEditId;
        if (sid) {
            const cachedSurvey = localStorage.getItem(`survey_${sid}`);
            if (cachedSurvey) {
                content.innerHTML = renderSurveyFormHTML(JSON.parse(cachedSurvey), sid);
                showToast('Memuatkan borang dari cache luar talian. Respons akan disimpan tempatan.', 'success');
                return;
            }
        }
        content.innerHTML = `
            <div class="max-w-2xl mx-auto">
                <div class="card text-center py-10">
                    <svg class="w-16 h-16 mx-auto text-red-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <p class="text-gray-500">Gagal memuatkan borang. Sila semak sambungan internet.</p>
                    <button onclick="renderSurveyView()" class="btn btn-primary mt-4">Cuba Semula</button>
                </div>
            </div>`;
    }
}

// ========= OFFLINE SYNC ENGINE =========
function isOnline() {
    return navigator.onLine;
}

function savePendingSurvey(surveyId, answers) {
    const pending = JSON.parse(localStorage.getItem('pending_surveys') || '[]');
    pending.push({
        survey_id: surveyId,
        answers: JSON.stringify(answers),
        respondent_info: '',
        saved_at: new Date().toISOString()
    });
    localStorage.setItem('pending_surveys', JSON.stringify(pending));
}

async function syncPendingSurveys() {
    if (!isOnline()) return;
    const pending = JSON.parse(localStorage.getItem('pending_surveys') || '[]');
    if (pending.length === 0) return;

    const remaining = [];
    let synced = 0;

    for (const item of pending) {
        try {
            await api('/api/surveys/submit', {
                method: 'POST',
                body: JSON.stringify({
                    survey_id: item.survey_id,
                    answers: item.answers,
                    respondent_info: item.respondent_info || ''
                })
            });
            synced++;
        } catch (e) {
            remaining.push(item);
        }
    }

    if (remaining.length > 0) {
        localStorage.setItem('pending_surveys', JSON.stringify(remaining));
    } else {
        localStorage.removeItem('pending_surveys');
    }

    if (synced > 0) {
        showToast(`${synced} respons luar talian berjaya dihantar secara automatik!`);
    }
}

window.addEventListener('online', () => {
    syncPendingSurveys();
});

async function submitSurveyForm(event, surveyId) {
    event.preventDefault();
    const form = document.getElementById('surveyForm');
    const inputs = form.querySelectorAll('input, textarea, select');
    
    const qElements = {};
    inputs.forEach(inp => {
        const name = inp.name || inp.id;
        if (name && name.startsWith('ans_')) {
            const qId = name.replace('ans_', '');
            if (inp.type === 'radio' || inp.type === 'checkbox') {
                if (inp.checked) {
                    if (!qElements[qId]) qElements[qId] = [];
                    qElements[qId].push(inp.value);
                }
            } else {
                qElements[qId] = inp.value;
            }
        }
    });

    const allRequired = form.querySelectorAll('[required]');
    for (let inp of allRequired) {
        const name = inp.name || inp.id;
        if (name && name.startsWith('ans_')) {
            const qId = name.replace('ans_', '');
            const val = qElements[qId];
            if (!val || (Array.isArray(val) && val.length === 0) || (typeof val === 'string' && !val.trim())) {
                showToast('Sila lengkapkan semua soalan wajib', 'error');
                return;
            }
        }
    }

    if (isOnline()) {
        try {
            await api('/api/surveys/submit', {
                method: 'POST',
                body: JSON.stringify({ survey_id: surveyId, answers: JSON.stringify(qElements), respondent_info: '' })
            });
            showToast('Respons berjaya dihantar! Terima kasih.');
            document.getElementById('surveyForm').innerHTML = `
                <div class="text-center py-8">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </div>
                    <h3 class="text-lg font-bold text-green-700">Terima Kasih!</h3>
                    <p class="text-gray-600 mt-2">Respons anda telah direkodkan.</p>
                </div>`;
        } catch (err) {
            savePendingSurvey(surveyId, qElements);
            showToast('Sistem luar talian. Data telah disimpan dalam peranti dan akan dihantar bila talian pulih.', 'success');
            document.getElementById('surveyForm').innerHTML = `
                <div class="text-center py-8">
                    <div class="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                    </div>
                    <h3 class="text-lg font-bold text-amber-700">Disimpan Luar Talian</h3>
                    <p class="text-gray-600 mt-2">Data anda telah disimpan dengan selamat dalam peranti ini. Akan dihantar secara automatik apabila talian internet kembali.</p>
                </div>`;
        }
    } else {
        savePendingSurvey(surveyId, qElements);
        showToast('Sistem luar talian. Data telah disimpan dalam peranti dan akan dihantar bila talian pulih.', 'success');
        document.getElementById('surveyForm').innerHTML = `
            <div class="text-center py-8">
                <div class="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg class="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
                </div>
                <h3 class="text-lg font-bold text-amber-700">Disimpan Luar Talian</h3>
                <p class="text-gray-600 mt-2">Data anda telah disimpan dengan selamat dalam peranti ini. Akan dihantar secara automatik apabila talian internet kembali.</p>
            </div>`;
    }
}

// ========= DASHBOARD =========
async function renderDashboard() {
    const content = document.getElementById('contentArea');
    if (state.chart && typeof state.chart.destroy === 'function') {
        state.chart.destroy();
    }
    state.chart = null;
    if (state.charts['stackedBar'] && typeof state.charts['stackedBar'].destroy === 'function') {
        state.charts['stackedBar'].destroy();
    }
    state.charts['stackedBar'] = null;
    if (state.charts['n12'] && typeof state.charts['n12'].destroy === 'function') {
        state.charts['n12'].destroy();
    }
    state.charts['n12'] = null;
    Object.keys(state.charts).forEach(key => {
        if (state.charts[key] && typeof state.charts[key].destroy === 'function') {
            state.charts[key].destroy();
        }
        state.charts[key] = null;
    });
    content.innerHTML = `<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan dashboard...</span></div>`;
    try {
        const selectedDun = state.dashboardDm || '';
        
        // 🚀 CONSOLIDATED SINGLE FETCH: Satu panggilan API untuk SEMUA data dashboard
        // (Parlimen summary + ALL DUN PDM data) — menggantikan 5 panggilan berasingan.
        const DUN_PDM_CODES = ['N12', 'N13', 'N14', 'N15'];
        const DUN_PDM_NAMES = { 'N12': 'DUN N12 SULAMAN', 'N13': 'DUN N13 PANTAI DALIT', 'N14': 'DUN N14 TAMPARULI', 'N15': 'DUN N15 KIULU' };
        const data = await api(`/api/dashboard${selectedDun ? `?dun=${selectedDun}` : ''}`).catch(() => ({}));
        console.log("[Dashboard Single Payload]", data);
        state.dashboardData = data;
        
        // 🚀 Extract DUN PDM data from the consolidated payload
        let dunPdmData = data.dun_pdm || {};
        
        // 🚀 SINGLE PAYLOAD ONLY: Use consolidated dun_pdm data directly.
        // 🛡️ POKA-YOKE: If any DUN key is missing/invalid, fallback to empty array
        // in-memory — NO additional HTTP API calls.
        const pdmResults = DUN_PDM_CODES.map(kod => ({
            data: Array.isArray(dunPdmData[kod]) ? dunPdmData[kod] : []
        }));
        console.log("[Dashboard] Using consolidated PDM data from single payload");
        
        // ═══ INNER TRY: SAFE RENDER BLOCK WITH FULL-SCREEN ERROR OVERLAY ═══
        try {
            // 🛡️ Container fallback chain
            const targetContainer = document.getElementById('contentArea') || document.getElementById('dashboard-container') || document.querySelector('.main-content') || document.body;
            if (!targetContainer) throw new Error("Could not find any suitable DOM container (like #contentArea) to inject the HTML.");
            
            if (!state.pdmList || !state.pdmList.length) state.pdmList = await api('/api/pdm');
            // 🛡️ Guarded destructuring with optional chaining to prevent "Cannot read properties of undefined"

        // 🛡️ Build PDM tables HTML FIRST (before any template reference)
        let pdmTablesHtml = '';
        const pdmDunNames = { 'N12': 'DUN N12 SULAMAN', 'N13': 'DUN N13 PANTAI DALIT', 'N14': 'DUN N14 TAMPARULI', 'N15': 'DUN N15 KIULU' };
        DUN_PDM_CODES.forEach((kod, idx) => {
            const pdmData = (pdmResults[idx] && pdmResults[idx].data) || [];
            console.log("Adding PDM Table for:", pdmDunNames[kod], "| Records:", pdmData.length);
            pdmTablesHtml += renderPdmTable(kod, pdmDunNames[kod], pdmData);
        });

        // 🚀 PHASE 3 PERF: DocumentFragment chunked rendering — browser paints between chunks
        const parlimenFragment = document.createDocumentFragment();
        const parlimenContainer = document.createElement('div');
        parlimenContainer.innerHTML = renderParlimenMirrorTable(pdmResults, DUN_PDM_CODES, DUN_PDM_NAMES);
        parlimenFragment.appendChild(parlimenContainer);
        
        // Clear the loading spinner and inject Parlimen Mirror first
        content.innerHTML = '';
        requestAnimationFrame(() => {
            content.appendChild(parlimenFragment);
            
            // 🚀 PHASE 3 PERF: Then schedule PDM tables in a separate rAF tick
            requestAnimationFrame(() => {
                const pdmContainer = document.createElement('div');
                pdmContainer.id = 'pdm-tables';
                pdmContainer.className = 'mt-6';
                pdmContainer.innerHTML = pdmTablesHtml;
                content.appendChild(pdmContainer);
                
                // 🚀 DECOUPLED ARCHITECTURE: Setiap table input recalculate table sendiri sahaja
                requestAnimationFrame(() => {
                    // ───────────────────────────────────────────────
                    // PARLIMEN TABLE: Recalculate JUMLAH footer helper
                    // ───────────────────────────────────────────────
                    function recalcParlimenJumlah() {
                        const parlJumlah = document.querySelector('#parlimenMirrorBody tr:last-child');
                        if (!parlJumlah || !parlJumlah.querySelector('td:first-child')?.textContent?.includes('JUMLAH')) return;
                        const parlJumlahTds = parlJumlah.querySelectorAll('td');
                        let sumBerdaftar = 0, sumAnggaran = 0, sumKKTerkini = 0;
                        document.querySelectorAll('#parlimenMirrorBody tr[data-dun-row]').forEach(tr => {
                            const cells = tr.children;
                            const hasRowspan = tr.querySelector('td[rowspan]') !== null;
                            const berdaftarIdx = hasRowspan ? 2 : 1;
                            const anggaranIdx = hasRowspan ? 3 : 2;
                            const kkTerkiniIdx = hasRowspan ? 8 : 7;
                            sumBerdaftar += parseInt((cells[berdaftarIdx]?.textContent || '0').replace(/,/g, '')) || 0;
                            sumAnggaran += parseInt((cells[anggaranIdx]?.textContent || '0').replace(/,/g, '')) || 0;
                            sumKKTerkini += parseInt((cells[kkTerkiniIdx]?.textContent || '0').replace(/,/g, '')) || 0;
                        });
                        // HORIZONTAL FOOTER: JUMLAH_V7 = Math.round(JUMLAH_V4 * multiplier/100), JUMLAH_V8 = Math.round(JUMLAH_V7 / kkRatio)
                        const multiplier = parseFloat(document.getElementById('inputSasaranUndiMultiplier')?.value) || 100;
                        const kkRatio = parseFloat(document.getElementById('inputKKRatio')?.value) || 13;
                        const sumSasaranUndi = Math.round(sumAnggaran * multiplier / 100);
                        const sumSasaranKK = Math.round(sumSasaranUndi / kkRatio);
                        // JUMLAH row: [0]=colspan2, [1]=Berdaftar, [2]=Anggaran, [3]=PRU, [4]=PRN, [5]=SasaranUndi, [6]=SasaranKK, [7]=KKTerkini
                        if (parlJumlahTds[1]) parlJumlahTds[1].textContent = sumBerdaftar.toLocaleString();
                        if (parlJumlahTds[2]) parlJumlahTds[2].textContent = sumAnggaran.toLocaleString();
                        if (parlJumlahTds[5]) parlJumlahTds[5].textContent = sumSasaranUndi.toLocaleString();
                        const sasaranKKJumlah = parlJumlah.querySelector('.sasaran-kk-pdm');
                        if (sasaranKKJumlah) sasaranKKJumlah.textContent = sumSasaranKK.toLocaleString();
                        if (parlJumlahTds[7]) parlJumlahTds[7].textContent = sumKKTerkini.toLocaleString();
                    }

                    // ───────────────────────────────────────────────
                    // PARLIMEN TABLE INPUT HANDLERS — recalc ONLY Parlimen rows
                    // ───────────────────────────────────────────────

                    // Parlimen Turnout% → recalculate Parlimen rows + JUMLAH
                    const turnoutInput = document.getElementById('inputTurnoutPercentage');
                    if (turnoutInput) {
                        turnoutInput.addEventListener('input', function() {
                            const pct = parseFloat(this.value) || 0;
                            const factor = pct / 100;
                            const kkRatioVal = parseFloat(document.getElementById('inputKKRatio')?.value) || 13;
                            const sasaranUndiMultiplier = parseFloat(document.getElementById('inputSasaranUndiMultiplier')?.value) || 100;

                            document.querySelectorAll('#parlimenMirrorBody tr[data-dun-row]').forEach(row => {
                                const cells = row.children;
                                const hasRowspan = row.querySelector('td[rowspan]') !== null;
                                const berdaftarIdx = hasRowspan ? 2 : 1;
                                const turnoutIdx = hasRowspan ? 3 : 2;
                                const daftar = parseInt((cells[berdaftarIdx]?.textContent || '0').replace(/,/g, '')) || 0;

                                // Column 4 (Anggaran Turun Mengundi)
                                const newAnggaran = Math.round(daftar * factor);
                                if (cells[turnoutIdx]) {
                                    cells[turnoutIdx].textContent = newAnggaran.toLocaleString();
                                    cells[turnoutIdx].dataset.rawAnggaran = newAnggaran;
                                }
                                // Column 7 (Sasaran UNDI)
                                const newSasaranUndi = Math.round(newAnggaran * sasaranUndiMultiplier / 100);
                                const undiCell = row.querySelector('.sasaran-undi-pdm');
                                if (undiCell) {
                                    undiCell.textContent = newSasaranUndi.toLocaleString();
                                    undiCell.dataset.rawSasaranUndi = newAnggaran * sasaranUndiMultiplier / 100;
                                }
                                // Column 8 (Sasaran K.K)
                                const kkCell = row.querySelector('.sasaran-kk-pdm');
                                if (kkCell) {
                                    kkCell.textContent = Math.round(newSasaranUndi / kkRatioVal).toLocaleString();
                                    kkCell.dataset.rawSasaranKk = (newAnggaran * sasaranUndiMultiplier / 100) / kkRatioVal;
                                }
                            });
                            recalcParlimenJumlah();
                        });
                    }

                    // Parlimen KK Ratio → recalculate ONLY Parlimen rows + JUMLAH
                    const kkRatioInput = document.getElementById('inputKKRatio');
                    if (kkRatioInput) {
                        kkRatioInput.addEventListener('input', function() {
                            const ratio = parseFloat(this.value) || 13;
                            document.querySelectorAll('#parlimenMirrorBody tr[data-dun-row] .sasaran-kk-pdm').forEach(kkCell => {
                                const row = kkCell.closest('tr');
                                if (!row) return;
                                const undiCell = row.querySelector('.sasaran-undi-pdm');
                                if (undiCell) {
                                    const undi = parseInt((undiCell.textContent || '0').replace(/,/g, '')) || 0;
                                    kkCell.textContent = Math.round(undi / ratio).toLocaleString();
                                    kkCell.dataset.rawSasaranKk = undi / ratio;
                                }
                            });
                            recalcParlimenJumlah();
                        });
                    }

                    // Parlimen Sasaran UNDI Multiplier → recalculate ONLY Parlimen rows + JUMLAH
                    const sasaranUndiInput = document.getElementById('inputSasaranUndiMultiplier');
                    if (sasaranUndiInput) {
                        sasaranUndiInput.addEventListener('input', function() {
                            const multiplier = parseFloat(this.value) || 100;
                            const mFactor = multiplier / 100;
                            const pct = parseFloat(document.getElementById('inputTurnoutPercentage')?.value) || 75;
                            const tFactor = pct / 100;
                            const kkRatioVal = parseFloat(document.getElementById('inputKKRatio')?.value) || 13;

                            document.querySelectorAll('#parlimenMirrorBody tr[data-dun-row]').forEach(row => {
                                const cells = row.children;
                                const hasRowspan = row.querySelector('td[rowspan]') !== null;
                                const berdaftarIdx = hasRowspan ? 2 : 1;
                                const daftar = parseInt((cells[berdaftarIdx]?.textContent || '0').replace(/,/g, '')) || 0;
                                const anggaranVal = Math.round(daftar * tFactor);
                                const newSasaranUndi = Math.round(anggaranVal * mFactor);
                                const undiCell = row.querySelector('.sasaran-undi-pdm');
                                if (undiCell) {
                                    undiCell.textContent = newSasaranUndi.toLocaleString();
                                    undiCell.dataset.rawSasaranUndi = anggaranVal * mFactor;
                                }
                                const turnoutIdx = hasRowspan ? 3 : 2;
                                if (cells[turnoutIdx]) cells[turnoutIdx].textContent = anggaranVal.toLocaleString();
                                const kkCell = row.querySelector('.sasaran-kk-pdm');
                                if (kkCell) {
                                    kkCell.textContent = Math.round(newSasaranUndi / kkRatioVal).toLocaleString();
                                    kkCell.dataset.rawSasaranKk = (anggaranVal * mFactor) / kkRatioVal;
                                }
                            });
                            recalcParlimenJumlah();
                        });
                    }

                    // ═══════════════════════════════════════════════════════════════
                    // INDEPENDENT PDM TABLE INPUT HANDLERS — recalc ONLY their own table
                    // ═══════════════════════════════════════════════════════════════

                    // Helper: Recalculate a single PDM table's rows + JUMLAH footer
                    // CRITICAL RULE: ONLY modifies Col 4 (Anggaran), Col 7 (Sasaran UNDI), Col 8 (Sasaran K.K)
                    // NEVER writes to Col 5 (PRU15 2022 / .editable-pru-pdm) or Col 6 (PRN 2025 / .editable-prn-pdm)
                    function recalcPdmTableRows(table) {
                        if (!table) return;
                        const card = table.closest('.pdm-table-card');
                        if (!card) return;
                        const turnoutInput = card.querySelector('.input-turnout-pdm');
                        const multiplierInput = card.querySelector('.input-multiplier-pdm');
                        const kkRatioInput = card.querySelector('.input-kkratio-pdm');
                        const tFactor = parseFloat(turnoutInput?.value || 75) / 100;
                        const mFactor = parseFloat(multiplierInput?.value || 100) / 100;
                        const kkRatioVal = parseFloat(kkRatioInput?.value || 13);
                        const rows = table.querySelectorAll('tbody tr');
                        let sumAnggaran = 0;

                        rows.forEach(row => {
                            if (row.querySelector('td:first-child')?.textContent?.includes('JUMLAH')) return;
                            
                            // Read pemilih from data-pemilih attribute OR fallback to Col 3 text content
                            const rawPemilih = row.dataset.pemilih || row.querySelector('td:nth-child(3)')?.textContent || '0';
                            const pemilih = parseInt(String(rawPemilih).replace(/,/g, ''), 10) || 0;
                            // V4 = Math.round(N_daftar * P_turnout/100)
                            const newAnggaran = Math.round(pemilih * tFactor);
                            
                            // Col 4 (Anggaran) - use CLASS-BASED selector ONLY
                            const anggaranCell = row.querySelector('.anggaran-pdm');
                            if (anggaranCell) {
                                anggaranCell.textContent = newAnggaran.toLocaleString();
                                anggaranCell.dataset.rawAnggaran = newAnggaran;
                            }
                            
                            // Col 7 (Sasaran UNDI) = Math.round(V4 * M_sasaran/100) - use CLASS-BASED selector ONLY
                            const newSasaranUndi = Math.round(newAnggaran * mFactor);
                            const undiCell = row.querySelector('.sasaran-undi-pdm');
                            if (undiCell) {
                                undiCell.textContent = newSasaranUndi.toLocaleString();
                                undiCell.dataset.rawSasaranUndi = newAnggaran * mFactor;
                            }
                            
                            // Col 8 (Sasaran K.K) = Math.round(V7 / R_kk) - use CLASS-BASED selector ONLY
                            const kkCell = row.querySelector('.sasaran-kk-pdm');
                            if (kkCell) {
                                kkCell.textContent = Math.round(newSasaranUndi / kkRatioVal).toLocaleString();
                                kkCell.dataset.rawSasaranKk = newSasaranUndi / kkRatioVal;
                            }
                            
                            // NEVER write to Col 5 (.editable-pru-pdm) or Col 6 (.editable-prn-pdm)
                            
                            // HORIZONTAL FOOTER: accumulate V4 only
                            sumAnggaran += newAnggaran;
                        });
                        
                        // HORIZONTAL FOOTER: JUMLAH_V7 = Math.round(JUMLAH_V4 * multiplier/100), JUMLAH_V8 = Math.round(JUMLAH_V7 / kkRatio)
                        const sumUndi = Math.round(sumAnggaran * mFactor);
                        const sumKK = Math.round(sumUndi / kkRatioVal);

                        // Recalculate JUMLAH footer using CLASS-BASED selectors ONLY
                        const lastRow = rows[rows.length - 1];
                        if (lastRow && lastRow.querySelector('td:first-child')?.textContent?.includes('JUMLAH')) {
                            const totalAnggaranCell = lastRow.querySelector('.total-anggaran-pdm');
                            if (totalAnggaranCell) totalAnggaranCell.textContent = sumAnggaran.toLocaleString();
                            
                            const totalUndiCell = lastRow.querySelector('.total-sasaran-undi-pdm');
                            if (totalUndiCell) totalUndiCell.textContent = sumUndi.toLocaleString();
                            
                            const totalKkCell = lastRow.querySelector('.total-sasaran-kk-pdm');
                            if (totalKkCell) totalKkCell.textContent = sumKK.toLocaleString();
                        }
                    }

                    // Bind per-PDM-table input handlers
                    document.querySelectorAll('#pdm-tables .pdm-table-card').forEach(card => {
                        const table = card.querySelector('table');
                        if (!table) return;
                        const bindRecalc = () => recalcPdmTableRows(table);
                        card.querySelector('.input-turnout-pdm')?.addEventListener('input', bindRecalc);
                        card.querySelector('.input-multiplier-pdm')?.addEventListener('input', bindRecalc);
                        card.querySelector('.input-kkratio-pdm')?.addEventListener('input', bindRecalc);
                    });

                    // ───────────────────────────────────────────────
                    // ELECTION LABEL SYNC (visual sahaja — no recalc cascade)
                    // ───────────────────────────────────────────────
                    document.querySelectorAll('.input-election-col1-pdm').forEach(inp => {
                        inp.addEventListener('input', function() {
                            document.querySelectorAll('.input-election-col1-pdm').forEach(other => {
                                if (other !== this) other.value = this.value;
                            });
                        });
                    });
                    document.querySelectorAll('.input-election-col2-pdm').forEach(inp => {
                        inp.addEventListener('input', function() {
                            document.querySelectorAll('.input-election-col2-pdm').forEach(other => {
                                if (other !== this) other.value = this.value;
                            });
                        });
                    });
                    // 🚀 PHASE 3 PERF: Save to cache after rendering completes
                    state.pageCache['dashboard'] = content.innerHTML;
                    state.pageCacheValid['dashboard'] = true;
                });
            });
        });

        // ════════════════════════════════════════════════════
        // [REMOVED] syncPdmJumlahToParlimen() — DECOUPLED ARCHITECTURE
        // Setiap table (Parlimen & PDM) kini recalculate dan
        // JUMLAH footer masing-masing secara INDEPENDEN.
        // Tiada lagi DOM mirroring Parlimen ← PDM JUMLAH.
        // ════════════════════════════════════════════════════

        
        // ═══ END OF INNER TRY (RENDER BLOCK) ═══
    } catch (renderError) {
        console.error("⛔ CRITICAL FRONTEND RENDER CRASH:", renderError);
        
        // 🛡️ FORCE-RENDER A FALLBACK TO THE SCREEN INSTEAD OF A BLANK PAGE
        const existingError = document.getElementById('jentera-crash-overlay');
        if (existingError) existingError.remove();
        
        const errorDisplay = document.createElement('div');
        errorDisplay.id = 'jentera-crash-overlay';
        errorDisplay.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #fff5f5; color: #9b2c2c; padding: 30px; font-family: monospace; z-index: 9999; overflow: auto; border: 5px solid #e53e3e;";
        errorDisplay.innerHTML = `
            <h1 style="font-size: 24px; font-weight: bold; margin-bottom: 15px;">🚨 Frontend Render Error (App is Blocked)</h1>
            <p><strong>Error Message:</strong> ${renderError.message}</p>
            <p><strong>Occurred in:</strong> ${renderError.stack ? renderError.stack.split('\\n')[1] : 'Unknown line'}</p>
            <hr style="border-color: #feb2b2; margin: 20px 0;">
            <pre style="background: #fff; padding: 15px; border-radius: 5px; border: 1px solid #fed7d7; white-space: pre-wrap; word-break: break-all;">${renderError.stack}</pre>
            <p style="margin-top: 20px; font-size: 14px; color: #4a5568;">💡 Jarvis: Check if any element ID (like 'inputElectionCol1', 'inputKKRatio', or the table body container) is missing from index.html or if you tried to map/loop over an undefined array.</p>
        `;
        document.body.appendChild(errorDisplay);
        return; // Stop further execution
    }
    
    } catch (err) {
        const contentArea = document.getElementById('contentArea');
        if (contentArea) {
            contentArea.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
        } else {
            console.error("⛔ CRITICAL API ERROR - contentArea not found:", err);
        }
    }
}

// ========= 4 DUN PDM TABLES LOADER =========
async function loadPdmTables() {
    const DUN_CODES = ['N12', 'N13', 'N14', 'N15'];
    const DUN_NAMES = { 'N12': 'DUN N12 SULAMAN', 'N13': 'DUN N13 PANTAI DALIT', 'N14': 'DUN N14 TAMPARULI', 'N15': 'DUN N15 KIULU' };
    
    let pdmContainer = document.getElementById('pdm-tables');
    if (!pdmContainer) return;
    
    for (const kod of DUN_CODES) {
        try {
            const res = await api(`/api/dashboard/pdm/${kod}`);
            const pdmData = res.data || [];
            console.log("Adding PDM Table for:", DUN_NAMES[kod], "| Records:", pdmData.length);
            const tableHtml = renderPdmTable(kod, DUN_NAMES[kod], pdmData);
            pdmContainer.insertAdjacentHTML('beforeend', tableHtml);
        } catch (e) {
            console.error(`PDM table error for ${kod}:`, e);
            const fallbackHtml = renderPdmTable(kod, DUN_NAMES[kod], []);
            pdmContainer.insertAdjacentHTML('beforeend', fallbackHtml);
        }
    }
}

// ========= 4 DUN PDM TABLES =========
const DUN_PDM_CONFIG = {
    'N12': { nama: 'DUN N12 SULAMAN', kod: 'N12' },
    'N13': { nama: 'DUN N13 PANTAI DALIT', kod: 'N13' },
    'N14': { nama: 'DUN N14 TAMPARULI', kod: 'N14' },
    'N15': { nama: 'DUN N15 KIULU', kod: 'N15' }
};

function renderPdmTable(dunKod, dunNama, pdmData) {
    // 🛡️ Return skeleton card when data is empty
    if (!pdmData || pdmData.length === 0) {
    return `
    <div class="card mb-4 pdm-table-card" data-dun-code="${dunKod}">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-bold text-gray-800">PANEL STRATEGI ${dunNama}</h3>
        </div>
        <div class="overflow-x-auto" style="max-width:100%;">
            <table class="w-full text-xs" style="min-width:1400px;border-collapse:collapse;">
                <thead>
                    <tr class="bg-gray-100">
                        <th colspan="17" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-amber-800" style="background:#fef3c7;">DATA TIDAK TERSEDIA — Tiada rekod PDM untuk ${dunNama}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="17" class="text-center py-4 text-gray-400">Data PDM sedang dimuatkan atau belum tersedia. Sila semak semula kemudian.</td></tr>
                </tbody>
            </table>
        </div>
    </div>`;
    }
    const pdmCount = pdmData ? pdmData.length : 1;
    const turnOutInput = parseFloat(document.getElementById('inputTurnoutPercentage')?.value || '75');
    const factor = turnOutInput / 100;
    const kkRatio = parseFloat(document.getElementById('inputKKRatio')?.value || '13');
    const col1Label = document.getElementById('inputElectionCol1')?.value || 'PRU15 2022';
    const col2Label = document.getElementById('inputElectionCol2')?.value || 'PRN 2025';
    const sasaranUndiMultiplier = parseFloat(document.getElementById('inputSasaranUndiMultiplier')?.value) || 100;
    
    let rows = '';
    let isFirstRow = true;
    let colSums = { berdaftar: 0, turnout: 0, pru15: 0, prn2025: 0, sasaran_undi: 0, kk: 0, kk_terkini: 0, putih: 0, atas: 0, hitam: 0, tidak: 0, meninggal: 0, usia18: 0, usia31: 0, usia60: 0 };
    
    const cleanPdmData = pdmData.filter(p => p.dm !== 'Tidak Diagihkan' && p.dm !== 'ZZ');
    cleanPdmData.forEach(p => {
        const jumlah = p.jumlah || 0;
        // ROW-LEVEL COMPUTATIONS per MANDATORY FORMULA SPEC:
        //   V4 = Math.round(N_daftar * P_turnout / 100)
        const rawAnggaran = jumlah * factor;
        const anggaran = Math.round(rawAnggaran);                     // V4 = rounded
        const rawSasaranUndi = anggaran * sasaranUndiMultiplier / 100;
        const sasaranUndi = Math.round(rawSasaranUndi);               // V7 = Math.round(V4 * M/100)
        const rawSasaranKK = sasaranUndi / kkRatio;
        const sasaranKK = Math.round(rawSasaranKK);                   // V8 = Math.round(V7 / R_kk)
        const kkTerkini = p.jumlah_ketua_keluarga ?? Math.round(jumlah / kkRatio);
        const putih = p.putih || 0;
        const hitam = p.hitam || 0;
        const atas = p.atas_pagar || 0;
        const tidak = p.tidak_dikenali || 0;
        const meninggal = p.meninggal || 0;
        const usia18 = p.usia_18_30 || 0;
        const usia31 = p.usia_31_59 || 0;
        const usia60 = p.usia_60plus || 0;
        
        // Column 1: DUN with rowspan on first row only
        let dunCell = '';
        if (isFirstRow) {
            dunCell = `<td rowspan="${pdmCount}" class="border border-gray-300 px-2 py-1 font-bold text-center text-gray-800 align-middle" style="min-width:65px;">${dunNama}</td>`;
            isFirstRow = false;
        }
        
        rows += `<tr class="hover:bg-blue-50">
            ${dunCell}
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-medium">${p.dm || ''}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-semibold">${jumlah.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-bold text-blue-700" data-raw-anggaran="${rawAnggaran}">${anggaran.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle"><input type="number" value="" class="w-14 text-center text-xs border border-gray-300 rounded px-1 py-0.5" placeholder="0"></td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle"><input type="number" value="" class="w-14 text-center text-xs border border-gray-300 rounded px-1 py-0.5" placeholder="0"></td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-800 font-semibold sasaran-undi-pdm" data-raw-sasaran-undi="${rawSasaranUndi}">${sasaranUndi.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-800 font-semibold sasaran-kk-pdm" data-raw-sasaran-kk="${rawSasaranKK}">${sasaranKK.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle">${kkTerkini.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-green-700 font-medium">${putih.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-yellow-700 font-medium">${atas.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-red-700 font-medium">${hitam.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${tidak.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${meninggal.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${usia18.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${usia31.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${usia60.toLocaleString()}</td>
        </tr>`;
        
        colSums.berdaftar += jumlah; colSums.turnout += anggaran;
        colSums.pru15 += 0; colSums.prn2025 += 0; // editable inputs, not summed
        colSums.kk_terkini += kkTerkini;
        colSums.putih += putih; colSums.atas += atas; colSums.hitam += hitam; colSums.tidak += tidak;
        colSums.meninggal += meninggal;
        colSums.usia18 += usia18; colSums.usia31 += usia31; colSums.usia60 += usia60;
    });
    // HORIZONTAL FOOTER: JUMLAH_V7 = Math.round(JUMLAH_V4 * multiplier/100), JUMLAH_V8 = Math.round(JUMLAH_V7 / kkRatio)
    colSums.sasaran_undi = Math.round(colSums.turnout * sasaranUndiMultiplier / 100);
    colSums.kk = Math.round(colSums.sasaran_undi / kkRatio);
    
    rows += `<tr class="bg-gray-100 font-semibold">
        <td colspan="2" class="border border-gray-300 px-2 py-1 font-bold text-gray-800">JUMLAH</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.berdaftar.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.turnout.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle"></td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle"></td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle sasaran-undi-pdm">${colSums.sasaran_undi.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle sasaran-kk-pdm">${colSums.kk.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.kk_terkini.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-green-700">${colSums.putih.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-yellow-700">${colSums.atas.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-red-700">${colSums.hitam.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${colSums.tidak.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${colSums.meninggal.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia18.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia31.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia60.toLocaleString()}</td>
    </tr>`;
    
    return `
    <div class="card mb-4 pdm-table-card" data-dun-code="${dunKod}">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-bold text-gray-800">PANEL STRATEGI ${dunNama}</h3>
        </div>
        <div class="overflow-x-auto" style="max-width:100%;">
            <table class="w-full text-xs" style="min-width:1400px;border-collapse:collapse;">
                <thead>
                    <tr class="bg-gray-100">
                        <th rowspan="2" class="border border-gray-300 px-2 py-1.5 font-bold text-gray-800 text-center align-middle sticky left-0 bg-gray-100" style="min-width:65px;">DUN</th>
                        <th rowspan="2" class="border border-gray-300 px-2 py-1.5 font-bold text-gray-800 text-center align-middle" style="min-width:100px;">PDM</th>
                        <th colspan="4" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-green-800 align-middle" style="background:#dcfce7;">DATA ASAS</th>
                        <th colspan="8" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-amber-800 align-middle" style="background:#fef3c7;">SASARAN</th>
                        <th colspan="3" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-blue-800 align-middle" style="background:#dbeafe;">PECAHAN PENGUNDI MENGIKUT UMUR</th>
                    </tr>
                    <tr class="bg-gray-50">
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle">Bilangan Pengundi Berdaftar</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Anggaran Peratusan Turun Mengundi <input type="number" class="input-turnout-pdm w-12 text-center font-bold text-black border border-gray-300 rounded px-0.5" value="${turnOutInput}" min="0" max="100" style="display:inline-block;"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle"><input type="text" class="input-election-col1-pdm w-28 text-center bg-white border border-gray-300 rounded-lg px-2 py-1 text-sm font-semibold text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="${col1Label}"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle"><input type="text" class="input-election-col2-pdm w-28 text-center bg-white border border-gray-300 rounded-lg px-2 py-1 text-sm font-semibold text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" value="${col2Label}"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Sasaran UNDI <input type="number" class="input-multiplier-pdm w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" value="${sasaranUndiMultiplier}" min="0" max="200" style="display:inline-block;">%</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Sasaran K.K (1:<input type="number" class="input-kkratio-pdm w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" value="${kkRatio}" min="1" max="50" style="display:inline-block;">)</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle">Jumlah K.K Terkini</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-green-700">PUTIH TERKINI</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-yellow-700">Atas Pagar</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-red-700">HITAM</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-gray-500">Tiada Data</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-gray-500">Meninggal Dunia</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">18 - 30</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">31 - 59</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">60+</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    </div>`;
}

// ============================================================
// PARLIMEN MIRROR TABLE — BOTTOM-UP AGREGASI daripada 4 DUN PDM
// ============================================================
function renderParlimenMirrorTable(pdmResults, dunCodes, dunNames) {
    const allDunCodes = dunCodes || ['N12', 'N13', 'N14', 'N15'];
    const allDunNames = dunNames || { 'N12': 'DUN N12 SULAMAN', 'N13': 'DUN N13 PANTAI DALIT', 'N14': 'DUN N14 TAMPARULI', 'N15': 'DUN N15 KIULU' };
    const DUN_PDM_CODES = ['N12', 'N13', 'N14', 'N15'];

    const turnOutInput = parseFloat(document.getElementById('inputTurnoutPercentage')?.value || '75');
    const factor = turnOutInput / 100;
    const kkRatio = parseFloat(document.getElementById('inputKKRatio')?.value || '13');
    const col1Label = document.getElementById('inputElectionCol1')?.value || 'PRU15 2022';
    const col2Label = document.getElementById('inputElectionCol2')?.value || 'PRN 2025';
    const sasaranUndiMultiplier = parseFloat(document.getElementById('inputSasaranUndiMultiplier')?.value) || 100;

    const pdmCount = allDunCodes.length;
    let rows = '';
    let isFirstRow = true;
    const colSums = { berdaftar: 0, turnout: 0, pru15: 0, prn2025: 0, sasaran_undi: 0, kk: 0, kk_terkini: 0, putih: 0, atas: 0, hitam: 0, tidak: 0, meninggal: 0, usia18: 0, usia31: 0, usia60: 0 };

    allDunCodes.forEach((kod) => {
        const idx = DUN_PDM_CODES.indexOf(kod);
        const pdmData = (pdmResults[idx] && pdmResults[idx].data) || [];
        const cleanData = pdmData.filter(p => p.dm !== 'Tidak Diagihkan' && p.dm !== 'ZZ');

        // 🛡️ ROW-LEVEL FORMULA (raw high-precision → Math.round for display)
        const jumlah = cleanData.reduce((s, p) => s + (p.jumlah || 0), 0);
        const sumKKTerkini = cleanData.reduce((s, p) => s + (p.jumlah_ketua_keluarga || 0), 0);
        
        // ROW-LEVEL COMPUTATIONS per MANDATORY FORMULA SPEC:
        //   V4 = Math.round(N_daftar * P_turnout / 100)
        //   V7 = Math.round(V4 * M_sasaran / 100)
        //   V8 = Math.round(V7 / R_kk)
        const rawAnggaran = jumlah * factor;
        const perPdmAnggaran = Math.round(rawAnggaran);           // V4 = rounded
        const rawSasaranUndi = perPdmAnggaran * sasaranUndiMultiplier / 100;
        const perPdmSasaranUndi = Math.round(rawSasaranUndi);     // V7 = Math.round(V4 * M/100)
        const rawSasaranKK = perPdmSasaranUndi / kkRatio;
        const perPdmSasaranKK = Math.round(rawSasaranKK);         // V8 = Math.round(V7 / R_kk)

        // Raw aggregates (non-calculated columns) still use plain sum
        const agg = {
            nama: allDunNames[kod],
            jumlah: jumlah,
            putih: cleanData.reduce((s, p) => s + (p.putih || 0), 0),
            hitam: cleanData.reduce((s, p) => s + (p.hitam || 0), 0),
            atas_pagar: cleanData.reduce((s, p) => s + (p.atas_pagar || 0), 0),
            tidak_dikenali: cleanData.reduce((s, p) => s + (p.tidak_dikenali || 0), 0),
            meninggal: cleanData.reduce((s, p) => s + (p.meninggal || 0), 0),
            usia_18_30: cleanData.reduce((s, p) => s + (p.usia_18_30 || 0), 0),
            usia_31_59: cleanData.reduce((s, p) => s + (p.usia_31_59 || 0), 0),
            usia_60plus: cleanData.reduce((s, p) => s + (p.usia_60plus || 0), 0),
            jumlah_ketua_keluarga: sumKKTerkini
        };

        let parlimenCell = '';
        if (isFirstRow) {
            parlimenCell = `<td rowspan="${pdmCount}" class="border border-gray-300 px-2 py-1 font-bold text-center text-gray-800 align-middle" style="min-width:65px;">P 170<br>TUARAN</td>`;
            isFirstRow = false;
        }

        rows += `<tr class="hover:bg-blue-50" data-dun-row="${kod}">
            ${parlimenCell}
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-medium">${agg.nama}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-semibold">${agg.jumlah.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle font-bold text-blue-700" data-raw-anggaran="${rawAnggaran}">${perPdmAnggaran.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle"><input type="number" value="" class="w-14 text-center text-xs border border-gray-300 rounded px-1 py-0.5" placeholder="0"></td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle"><input type="number" value="" class="w-14 text-center text-xs border border-gray-300 rounded px-1 py-0.5" placeholder="0"></td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-800 font-semibold sasaran-undi-pdm" data-raw-sasaran-undi="${rawSasaranUndi}">${perPdmSasaranUndi.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-800 font-semibold sasaran-kk-pdm" data-raw-sasaran-kk="${rawSasaranKK}">${perPdmSasaranKK.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle">${agg.jumlah_ketua_keluarga.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-green-700 font-medium">${agg.putih.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-yellow-700 font-medium">${agg.atas_pagar.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-red-700 font-medium">${agg.hitam.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${agg.tidak_dikenali.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${agg.meninggal.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${agg.usia_18_30.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${agg.usia_31_59.toLocaleString()}</td>
            <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${agg.usia_60plus.toLocaleString()}</td>
        </tr>`;

        colSums.berdaftar += agg.jumlah; colSums.turnout += perPdmAnggaran;
        colSums.pru15 += 0; colSums.prn2025 += 0;
        colSums.kk_terkini += agg.jumlah_ketua_keluarga;
        colSums.putih += agg.putih; colSums.atas += agg.atas_pagar; colSums.hitam += agg.hitam;
        colSums.tidak += agg.tidak_dikenali; colSums.meninggal += agg.meninggal;
        colSums.usia18 += agg.usia_18_30; colSums.usia31 += agg.usia_31_59; colSums.usia60 += agg.usia_60plus;
    });
    // HORIZONTAL FOOTER: JUMLAH_V7 = Math.round(JUMLAH_V4 * multiplier/100), JUMLAH_V8 = Math.round(JUMLAH_V7 / kkRatio)
    colSums.sasaran_undi = Math.round(colSums.turnout * sasaranUndiMultiplier / 100);
    colSums.kk = Math.round(colSums.sasaran_undi / kkRatio);

    rows += `<tr class="bg-gray-100 font-semibold">
        <td colspan="2" class="border border-gray-300 px-2 py-1 font-bold text-gray-800">JUMLAH</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.berdaftar.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.turnout.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle"></td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle"></td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle sasaran-undi-pdm">${colSums.sasaran_undi.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle sasaran-kk-pdm">${colSums.kk.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle">${colSums.kk_terkini.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-green-700">${colSums.putih.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-yellow-700">${colSums.atas.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-red-700">${colSums.hitam.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${colSums.tidak.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-gray-500">${colSums.meninggal.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia18.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia31.toLocaleString()}</td>
        <td class="border border-gray-300 px-1 py-1 text-center align-middle text-blue-700">${colSums.usia60.toLocaleString()}</td>
    </tr>`;

    return `
    <div class="card mb-4" id="panelStrategi">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-bold text-gray-800">PANEL STRATEGI PARLIMEN P170 TUARAN</h3>
        </div>
        <div class="overflow-x-auto" style="max-width:100%;">
            <table class="w-full text-xs" style="min-width:1400px;border-collapse:collapse;">
                <thead>
                    <tr class="bg-gray-100">
                        <th rowspan="2" class="border border-gray-300 px-2 py-1.5 font-bold text-gray-800 text-center align-middle sticky left-0 bg-gray-100" style="min-width:65px;">PARLIMEN</th>
                        <th rowspan="2" class="border border-gray-300 px-2 py-1.5 font-bold text-gray-800 text-center align-middle" style="min-width:100px;">DUN</th>
                        <th colspan="4" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-green-800 align-middle" style="background:#dcfce7;">DATA ASAS</th>
                        <th colspan="8" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-amber-800 align-middle" style="background:#fef3c7;">SASARAN</th>
                        <th colspan="3" class="border border-gray-300 px-2 py-1.5 font-bold text-center text-blue-800 align-middle" style="background:#dbeafe;">PECAHAN PENGUNDI MENGIKUT UMUR</th>
                    </tr>
                    <tr class="bg-gray-50">
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle">Bilangan Pengundi Berdaftar</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Anggaran Peratusan Turun Mengundi <input type="number" id="inputTurnoutPercentage" value="75" class="w-12 text-center font-bold text-black border border-gray-300 rounded px-0.5" style="display:inline-block;"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle"><input type="text" id="inputElectionCol1" value="PRU15 2022" class="w-28 text-center bg-white border border-gray-300 rounded-lg px-2 py-1 text-sm font-semibold text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle"><input type="text" id="inputElectionCol2" value="PRN 2025" class="w-28 text-center bg-white border border-gray-300 rounded-lg px-2 py-1 text-sm font-semibold text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"></th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Sasaran UNDI <input type="number" id="inputSasaranUndiMultiplier" value="100" min="0" max="200" class="w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" style="display:inline-block;">%</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle whitespace-nowrap">Sasaran K.K (1:<input type="number" id="inputKKRatio" value="13" min="1" max="50" class="w-10 text-center font-bold text-black border border-gray-300 rounded px-0.5" style="display:inline-block;">)</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle">Jumlah K.K Terkini</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-green-700">PUTIH TERKINI</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-yellow-700">Atas Pagar</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-red-700">HITAM</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-gray-500">Tiada Data</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-gray-500">Meninggal Dunia</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">18 - 30</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">31 - 59</th>
                        <th class="border border-gray-300 px-1 py-1 font-semibold text-center align-middle text-blue-700">60+</th>
                    </tr>
                </thead>
                <tbody id="parlimenMirrorBody">
                    ${rows}
                </tbody>
            </table>
        </div>
    </div>`;
}

// ========= PENGUNDI LIST =========
// NOTE: filterOptions, selectedFilters, activeFilterDropdown — diisytiharkan dalam index.html inline script,
// jadi ia global dan tidak perlu diisytiharkan semula di sini.

function toggleFilterDropdown(type) {
    const existing = document.getElementById('filterDropdown');
    if (existing) existing.remove();
    if (activeFilterDropdown === type) { activeFilterDropdown = null; return; }
    activeFilterDropdown = type;
    
    const idSuffix = type === 'ketua_keluarga' ? 'KetuaKeluarga' : 
                     type === 'pegawai_penyelaras' ? 'PegawaiPenyelaras' : 
                     type.charAt(0).toUpperCase() + type.slice(1);
    const btn = document.getElementById(`filterBtn${idSuffix}`);
    if (!btn) return;
    
    const rect = btn.getBoundingClientRect();
    const isObjectItem = type === 'ketua_keluarga' || type === 'pegawai_penyelaras';
    const filterKey = type === 'pdm' ? 'pdm' : type === 'lokaliti' ? 'lokaliti' : type === 'sokongan' ? 'sokongan' : type;
    const rawItems = (filterOptions && Array.isArray(filterOptions[filterKey])) ? filterOptions[filterKey] : [];
    
    let searchText = '';
    const selected = selectedFilters[type] || [];
    
    const labelMap = {
        'pdm': 'PDM', 'lokaliti': 'Lokaliti', 'sokongan': 'Sokongan',
        'ketua_keluarga': 'Ketua Keluarga', 'pegawai_penyelaras': 'Peg. Penyelaras'
    };
    const label = labelMap[type] || type;
    
    const dropdown = document.createElement('div');
    dropdown.id = 'filterDropdown';
    dropdown.className = 'fixed z-50 bg-white border border-gray-200 rounded-xl shadow-xl p-3 max-h-80 overflow-y-auto';
    dropdown.style.left = Math.min(rect.left, window.innerWidth - 320) + 'px';
    dropdown.style.top = (rect.bottom + 8) + 'px';
    dropdown.style.width = '300px';
    
    const renderDropdown = (filter) => {
        const searchNormalized = searchText.toLowerCase().trim();
        let filteredItems = rawItems;
        if (searchNormalized) {
            filteredItems = rawItems.filter(item => {
                const display = isObjectItem ? (item.nama || item) : item;
                return String(display).toLowerCase().includes(searchNormalized);
            });
        }
        dropdown.innerHTML = `
            <div class="flex items-center justify-between mb-2"><span class="text-sm font-semibold text-gray-700">${label}</span><button onclick="this.closest('#filterDropdown').remove(); activeFilterDropdown=null;" class="text-gray-400 hover:text-red-500 text-lg leading-none">&times;</button></div>
            <input type="text" id="filterSearch" placeholder="Cari..." class="w-full text-sm border rounded-lg px-2 py-1.5 mb-2" value="${searchText}" oninput="window._filterSearchTimeout && clearTimeout(window._filterSearchTimeout); window._filterSearchTimeout=setTimeout(()=>{ const dd=document.getElementById('filterDropdown'); if(dd){ searchText=this.value; renderDropdown(type); } },200)">
            <div class="max-h-48 overflow-y-auto space-y-1">
                ${filteredItems.length === 0 ? '<p class="text-xs text-gray-400 text-center py-2">Tiada pilihan</p>' :
                filteredItems.map(item => {
                    const displayVal = isObjectItem ? item.nama : item;
                    const checkVal = isObjectItem ? item.id : item;
                    const isSelected = selected.includes(String(checkVal));
                    return `<label class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-blue-50 cursor-pointer ${isSelected?'bg-blue-50':''}">
                        <input type="checkbox" ${isSelected?'checked':''} onchange="toggleFilterItem('${type}','${String(checkVal).replace(/'/g,"\\'")}')" class="w-4 h-4 text-blue-600">
                        <span class="text-sm text-gray-700">${displayVal}</span>
                    </label>`;
                }).join('')}
            </div>
            <div class="flex gap-2 mt-2 pt-2 border-t">
                <button onclick="clearFilterType('${type}')" class="btn btn-outline text-xs py-1 px-2 flex-1">Kosongkan</button>
                <button onclick="this.closest('#filterDropdown').remove(); activeFilterDropdown=null; renderPengundi()" class="btn btn-primary text-xs py-1 px-2 flex-1">Guna</button>
            </div>`;
    };
    renderDropdown(type);
    document.body.appendChild(dropdown);
    setTimeout(() => {
        const searchInput = document.getElementById('filterSearch');
        if (searchInput) searchInput.focus();
    }, 100);
}

function toggleFilterItem(type, value) {
    if (!selectedFilters[type]) selectedFilters[type] = [];
    const idx = selectedFilters[type].indexOf(value);
    if (idx > -1) selectedFilters[type].splice(idx, 1);
    else selectedFilters[type].push(value);
}

function clearFilterType(type) {
    selectedFilters[type] = [];
    const dd = document.getElementById('filterDropdown');
    if (dd) {
        const btn = document.querySelector(`[onclick*="toggleFilterDropdown('${type}')"]`);
        if (btn) {
            toggleFilterDropdown(type);
        }
    }
}

function buildFilterParams() {
    const parts = [];
    if (selectedFilters.pdm.length) parts.push(`dm[]=${encodeURIComponent(selectedFilters.pdm.join(','))}`);
    if (selectedFilters.lokaliti.length) parts.push(`lokaliti[]=${encodeURIComponent(selectedFilters.lokaliti.join(','))}`);
    if (selectedFilters.sokongan.length) parts.push(`sokongan[]=${encodeURIComponent(selectedFilters.sokongan.join(','))}`);
    if (selectedFilters.ketua_keluarga.length) parts.push(`ketua_keluarga[]=${encodeURIComponent(selectedFilters.ketua_keluarga.join(','))}`);
    if (selectedFilters.pegawai_penyelaras.length) parts.push(`pegawai_penyelaras[]=${encodeURIComponent(selectedFilters.pegawai_penyelaras.join(','))}`);
    return parts.length ? '&' + parts.join('&') : '';
}

function handlePdmFilterChange(value) {
    if (value === 'N12' || value === 'N13' || value === 'N14' || value === 'N15') {
        state.pengundiDun = value;
        state.pengundiDm = '';
    } else if (value === '') {
        state.pengundiDun = '';
        state.pengundiDm = '';
    } else {
        state.pengundiDm = value;
        state.pengundiDun = '';
    }
    state.pengundiPage = 1;
    renderPengundi();
}

function renderSmartPagination(currentPage, totalPages, pageStateVar, renderFunc) {
    if (totalPages <= 1) return '';
    let html = '';
    html += `<button onclick="${pageStateVar}=1;${renderFunc}()" class="${currentPage===1?'active':''}">1</button>`;
    let startPage = currentPage;
    let endPage = Math.min(currentPage + 9, totalPages);
    if (startPage > 2) {
        html += '<span class="text-sm text-gray-400">...</span>';
    }
    const firstNum = startPage > 1 ? Math.max(startPage, 2) : 2;
    for (let p = firstNum; p <= endPage; p++) {
        html += `<button onclick="${pageStateVar}=${p};${renderFunc}()" class="${currentPage===p?'active':''}">${p}</button>`;
    }
    if (endPage < totalPages - 1) {
        html += '<span class="text-sm text-gray-400">...</span>';
    }
    if (totalPages > 1) {
        html += `<button onclick="${pageStateVar}=${totalPages};${renderFunc}()" class="${currentPage===totalPages?'active':''}">${totalPages}</button>`;
    }
    return html;
}

function clearAllFilters() {
    selectedFilters = { pdm: [], lokaliti: [], sokongan: [], ketua_keluarga: [], pegawai_penyelaras: [] };
    renderPengundi();
}

function hasActiveFilters() {
    return Object.values(selectedFilters).some(arr => arr.length > 0);
}

function getActiveFilterCount() {
    return Object.values(selectedFilters).reduce((sum, arr) => sum + arr.length, 0);
}

async function renderPengundi() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan senarai pengundi...</span></div>';
    try {
        if (!state.pdmList || !state.pdmList.length) state.pdmList = await api('/api/pdm');
        const dmParam = selectedFilters.pdm && selectedFilters.pdm.length
            ? ''
            : (state.pengundiDm ? `&dm[]=${encodeURIComponent(state.pengundiDm)}` : '');
        const dunParam = state.pengundiDun ? `&dun=${encodeURIComponent(state.pengundiDun)}` : '';
        const filterOptsParam = `${dunParam}${dmParam}${buildFilterParams()}`;
        const filterOptsUrl = filterOptsParam ? `/api/pengundi/filter-options?${filterOptsParam.replace(/^&/, '')}` : '/api/pengundi/filter-options';
        const [filterRes, result] = await Promise.all([
            api(filterOptsUrl),
            api(`/api/pengundi?page=${state.pengundiPage}&search=${encodeURIComponent(state.pengundiSearch)}${dmParam}${dunParam}${buildFilterParams()}`)
        ]);
        filterOptions = filterRes;
        state.pengundiData = result;
        const pengundi = result.data || [];
        const column_counts = result.column_counts || {};
        const total = result.total || 0;
        const perPage = result.per_page || 50;
        const totalPages = Math.ceil(total / perPage) || 1;
        const filterCount = getActiveFilterCount();
        const pdmList = state.pdmList || [];

        content.innerHTML = `
            <div class="card">
                <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
                    <h3 class="font-semibold text-gray-800">Senarai Pengundi</h3>
                    <div class="flex items-center gap-2">
                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Tambah Pengundi</button>' : '<button onclick="tambahPengundi()" class="btn btn-primary text-sm">+ Tambah Pengundi</button>'}
                        <span class="text-sm text-gray-500">${total.toLocaleString()} pengundi</span>
                    </div>
                </div>
                <div class="flex items-center gap-2 mb-4 flex-wrap">
                    <div class="relative flex-1 min-w-[200px]"><input type="text" id="pengundiSearch" placeholder="Cari nama, No KP..." value="${state.pengundiSearch}" onkeyup="if(event.key==='Enter'){state.pengundiSearch=this.value;state.pengundiPage=1;renderPengundi();}" class="w-full pl-8 pr-3 py-2 text-sm"><svg class="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg></div>
                    <button onclick="state.pengundiSearch=document.getElementById('pengundiSearch').value;state.pengundiPage=1;renderPengundi();" class="btn btn-primary text-sm py-2 px-3 whitespace-nowrap">Cari</button>
                    <button onclick="document.getElementById('pengundiSearch').value='';state.pengundiSearch='';state.pengundiPage=1;renderPengundi();" class="btn btn-outline text-sm py-2 px-3 whitespace-nowrap">Reset</button>
                    <select id="pdmFilterSelect" onchange="handlePdmFilterChange(this.value)" class="w-auto text-sm"><option value="">P170 Tuaran</option>${renderGroupedPdmOptions(pdmList, state.pengundiDm, state.pengundiDun)}</select>
                    <div class="flex items-center gap-1 ml-2 flex-wrap">
                        <button id="filterBtnPdm" onclick="toggleFilterDropdown('pdm')" class="btn btn-outline text-xs py-1.5 px-2 ${selectedFilters.pdm.length ? 'border-blue-500 bg-blue-50 text-blue-700' : ''}">PDM${selectedFilters.pdm.length ? ' ('+selectedFilters.pdm.length+')' : ''}</button>
                        <button id="filterBtnLokaliti" onclick="toggleFilterDropdown('lokaliti')" class="btn btn-outline text-xs py-1.5 px-2 ${selectedFilters.lokaliti.length ? 'border-blue-500 bg-blue-50 text-blue-700' : ''}">Lokaliti${selectedFilters.lokaliti.length ? ' ('+selectedFilters.lokaliti.length+')' : ''}</button>
                        <button id="filterBtnSokongan" onclick="toggleFilterDropdown('sokongan')" class="btn btn-outline text-xs py-1.5 px-2 ${selectedFilters.sokongan.length ? 'border-blue-500 bg-blue-50 text-blue-700' : ''}">Sokongan${selectedFilters.sokongan.length ? ' ('+selectedFilters.sokongan.length+')' : ''}</button>
                        <button id="filterBtnKetuaKeluarga" onclick="toggleFilterDropdown('ketua_keluarga')" class="btn btn-outline text-xs py-1.5 px-2 ${selectedFilters.ketua_keluarga.length ? 'border-blue-500 bg-blue-50 text-blue-700' : ''}">K. Keluarga${selectedFilters.ketua_keluarga.length ? ' ('+selectedFilters.ketua_keluarga.length+')' : ''}</button>
                        <button id="filterBtnPegawaiPenyelaras" onclick="toggleFilterDropdown('pegawai_penyelaras')" class="btn btn-outline text-xs py-1.5 px-2 ${selectedFilters.pegawai_penyelaras.length ? 'border-blue-500 bg-blue-50 text-blue-700' : ''}">Peg. Penyelaras${selectedFilters.pegawai_penyelaras.length ? ' ('+selectedFilters.pegawai_penyelaras.length+')' : ''}</button>
                        ${filterCount > 0 ? `<button onclick="clearAllFilters()" class="btn btn-outline text-xs py-1.5 px-2 border-red-300 text-red-600">Kosongkan (${filterCount})</button>` : ''}
                    </div>
                </div>
                ${pengundi.length === 0 ? `<div class="text-center py-10 text-gray-400">${state.pengundiSearch ? `"${state.pengundiSearch}" tiada dalam sistem.` : 'Tiada pengundi dijumpai.'}</div>` : `
                    <table>
                        <thead><tr>
                            <th style="width:120px" onclick="sortPengundi('no_kp')">No KP (${(column_counts.no_kp || 0).toLocaleString()})</th>
                            <th style="width:160px" onclick="sortPengundi('nama_penuh')">Nama Penuh (${(column_counts.nama_penuh || 0).toLocaleString()})</th>
                            <th style="width:60px" onclick="sortPengundi('jantina')">Jantina (${(column_counts.jantina || 0).toLocaleString()})</th>
                            <th style="width:60px" onclick="sortPengundi('umur')">Umur (${(column_counts.tahun_lahir || 0).toLocaleString()})</th>
                            <th style="width:120px" onclick="sortPengundi('dm')">DM / PDM (${(column_counts.dm || 0).toLocaleString()})</th>
                            <th style="width:140px" onclick="sortPengundi('lokaliti')">Lokaliti (${(column_counts.lokaliti || 0).toLocaleString()})</th>
                            <th style="width:100px" onclick="sortPengundi('sokongan')">Sokongan (${(column_counts.status_sokongan || 0).toLocaleString()})</th>
                            <th style="width:140px" onclick="sortPengundi('ketua_keluarga')">K. Keluarga (${(column_counts.ketua_keluarga_nama || 0).toLocaleString()})</th>
                            <th style="width:140px" onclick="sortPengundi('pegawai_penyelaras')">Peg. Penyelaras (${(column_counts.pegawai_penyelaras_nama || 0).toLocaleString()})</th>
                            <th style="width:100px">Tindakan</th>
                        </tr></thead>
                        <tbody>${pengundi.map(p => `<tr>
                            <td class="text-xs font-mono">${p.no_kp || '-'}</td>
                            <td class="font-medium whitespace-nowrap text-sm">${p.nama_penuh || '-'}</td>
                            <td class="text-xs">${p.jantina || '-'}</td>
                            <td class="text-xs">${p.tahun_lahir ? (2026 - p.tahun_lahir) : '-'}</td>
                            <td class="text-sm">${p.dm || '-'}</td>
                            <td class="text-sm">${p.lokaliti || '-'}</td>
                            <td class="text-xs">${(function(){
                                const s = p.status_sokongan;
                                if (!s) return '<span class="badge badge-tiada">Tiada Data</span>';
                                const st = String(s).trim();
                                const sl = st.toLowerCase();
                                if (sl === 'putih') return '<span class="badge badge-putih">Putih</span>';
                                if (sl === 'hitam') return '<span class="badge badge-hitam">Hitam</span>';
                                if (sl === 'atas pagar') return '<span class="badge badge-atas">Atas Pagar</span>';
                                return '<span class="badge badge-tiada">Tiada Data</span>';
                            })()}</td>
                            <td class="text-xs">${p.ketua_keluarga_nama || '<span class="text-gray-400">-</span>'}</td>
                            <td class="text-xs">${p.pegawai_penyelaras_nama || '<span class="text-gray-400">-</span>'}</td>
                            <td class="text-xs">${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-1.5 py-1 text-xs border-0 mr-1">Edit</button> <button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-1.5 py-1 text-xs border-0">Padam</button>' : '<button onclick="editPengundi(\'' + p.id + '\')" class="btn btn-primary text-xs py-1 px-1.5">Edit</button> <button onclick="padamPengundi(\'' + p.id + '\')" class="btn btn-outline text-xs py-1 px-1.5 border-red-300 text-red-600 hover:bg-red-50">Padam</button>'}</td>
                        </tr>`).join('')}</tbody>
                    </table>
                <div class="pagination">${renderSmartPagination(state.pengundiPage, totalPages, 'state.pengundiPage', 'renderPengundi')}
                    <span class="text-sm text-gray-500 ml-2">Halaman ${state.pengundiPage}/${totalPages}</span>
                </div>`}
            </div>`;
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

async function editPengundi(id) {
    if (window._editModalBusy) return;
    window._editModalBusy = true;
    try {
        const p = await api(`/api/pengundi/${id}`);
        const overlay = document.createElement('div');
        overlay.id = 'editModalOverlay';
        overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

        let lokalitiList = [];
        try {
            lokalitiList = await api('/api/lokaliti');
        } catch (e) {
            lokalitiList = [];
        }
        const lokalitiOptions = (lokalitiList || []).map(l => `<option value="${l.nama}">${l.nama} (${l.jumlah_pengundi || 0})</option>`).join('');

        const [kkOptions, ppOptions] = await Promise.all([
            fetchKkOptions(''),
            fetchPpOptions('')
        ]);
        const ppSelectedVal = p.pegawai_penyelaras_id ? `${p.pegawai_penyelaras_id} - ${(p.pegawai_penyelaras_nama || '')}` : '';
        const ppOptHtml = ppOptions.map(p2 => {
            const val = `${p2.id} - ${p2.nama_penuh}`;
            const sel = val === ppSelectedVal ? ' selected' : '';
            return `<option value="${val}"${sel}>${p2.nama_penuh}</option>`;
        }).join('');
        const kkSelectedVal = p.ketua_keluarga_id ? `${p.ketua_keluarga_id} - ${(p.ketua_keluarga_nama || '')}` : '';
        const kkOptHtml = kkOptions.map(k => {
            const val = `${k.id} - ${k.nama_penuh}`;
            const sel = val === kkSelectedVal ? ' selected' : '';
            return `<option value="${val}"${sel}>${k.nama_penuh}</option>`;
        }).join('');

        let dunList = [];
        try {
            dunList = await api('/api/dun');
        } catch (e) {
            dunList = [];
        }

        const dunKod = p.dun || '';
        if (!state.pdmList || !state.pdmList.length) {
            try { state.pdmList = await api('/api/pdm'); } catch (e) { state.pdmList = []; }
        }
        const pdmOptions = renderDunPdmDataList(dunKod, p.dm || '')
            .split('</option>')
            .filter(o => o.trim())
            .map(o => o + '</option>')
            .join('');

        overlay.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
                <div class="flex items-center justify-between p-4 border-b">
                    <h3 class="text-lg font-semibold text-gray-800">Edit Pengundi</h3>
                    <button onclick="this.closest('#editModalOverlay').remove()" class="text-gray-400 hover:text-red-500 text-2xl leading-none">&times;</button>
                </div>
                <div class="p-4 space-y-3">
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">Parlimen</label>
                        <select id="editParlimen" class="w-full px-3 py-2 text-sm border rounded-lg bg-gray-100 text-gray-500" disabled>
                            <option value="P170" selected>P170 Tuaran</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">DUN <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <select id="editDun" onchange="editDunChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                                <option value="">- Pilih DUN -</option>
                                <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                                ${dunList.map(d => `<option value="${d.kod}" ${d.kod === p.dun ? 'selected' : ''}>${d.nama} (${d.jumlah_pengundi || 0})</option>`).join('')}
                            </select>
                            <button id="editBtnHapusDun" onclick="editHapusDun()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam DUN">🗑️</button>
                        </div>
                    </div>
                    <div id="editDunBaruContainer" style="display:none;">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Nama DUN Baru <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <input type="text" id="editDunBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: N16 - BANGGI">
                            <button onclick="editTambahDunBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah DUN</button>
                        </div>
                        <p class="text-xs text-gray-400 mt-0.5">Masukkan kod dan nama DUN baru, cth: N16 - BANGGI. Klik "Tambah DUN" untuk create.</p>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">PDM <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <select id="editDm" onchange="editPdmChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                                <option value="">- Pilih PDM -</option>
                                <option value="TAMBAH_PDM" style="color:#2563eb;font-weight:600;">➕ Tambah PDM Baru</option>
                                ${pdmOptions}
                            </select>
                            <button id="editBtnHapusPdm" onclick="editHapusPdm()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam PDM">🗑️</button>
                        </div>
                        <div id="editPdmBaruContainer" style="display:none;" class="mt-2">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Nama PDM Baru <span class="text-red-500">*</span></label>
                            <div class="flex gap-2">
                                <input type="text" id="editPdmBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: BARU-BARU">
                                <button onclick="editTambahPdmBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah PDM</button>
                            </div>
                            <p class="text-xs text-gray-400 mt-0.5">Masukkan nama PDM baru. Klik "Tambah PDM" untuk create.</p>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">Lokaliti <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <select id="editLokaliti" onchange="editLokalitiChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                                <option value="">- Pilih Lokaliti -</option>
                                <option value="TAMBAH_LOKALITI" style="color:#2563eb;font-weight:600;">➕ Tambah Lokaliti Baru</option>
                                ${lokalitiOptions}
                            </select>
                            <button id="editBtnHapusLokaliti" onclick="editHapusLokaliti()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam Lokaliti">🗑️</button>
                        </div>
                        <div id="editLokalitiBaruContainer" style="display:none;" class="mt-2">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Nama Lokaliti Baru <span class="text-red-500">*</span></label>
                            <div class="flex gap-2">
                                <input type="text" id="editLokalitiBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: KAMPUNG BARU">
                                <button onclick="editTambahLokalitiBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah Lokaliti</button>
                            </div>
                            <p class="text-xs text-gray-400 mt-0.5">Masukkan nama Lokaliti baru. Klik "Tambah Lokaliti" untuk create.</p>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">Pegawai Penyelaras</label>
                        <select id="editPegawai" class="w-full px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Tiada / Kosong -</option>
                            ${ppOptHtml}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">Ketua Keluarga</label>
                        <select id="editKetuaKeluarga" class="w-full px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Tiada / Kosong -</option>
                            ${kkOptHtml}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">Nama Penuh <span class="text-red-500">*</span></label>
                        <input type="text" id="editNama" value="${(p.nama_penuh || '').replace(/"/g, '"')}" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="Nama penuh tanpa singkatan">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-600 mb-1">No KP</label>
                        <input type="text" id="editNoKp" value="${(p.no_kp || '').replace(/"/g, '"')}" class="w-full px-3 py-2 text-sm border rounded-lg bg-gray-100 text-gray-500" disabled placeholder="000101-01-0001">
                    </div>
                    ${(() => { const dob = parseIcToDob(p.no_kp || ''); return `
                    <div class="flex gap-2">
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Hari Lahir</label>
                            <input type="text" id="editHariLahir" value="${dob.hari}" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="DD">
                        </div>
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Bulan Lahir</label>
                            <input type="text" id="editBulanLahir" value="${dob.bulan}" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="MM">
                        </div>
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Tahun Lahir</label>
                            <input type="text" id="editTahunLahir" value="${p.tahun_lahir || dob.tahun}" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="YYYY">
                        </div>
                    </div>`; })()}
                    <div class="flex gap-3">
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Jantina</label>
                            <select id="editJantina" class="w-full px-3 py-2 text-sm border rounded-lg">
                                <option value="">- Pilih -</option>
                                <option value="L" ${p.jantina === 'L' || p.jantina === 'Lelaki' ? 'selected' : ''}>Lelaki</option>
                                <option value="P" ${p.jantina === 'P' || p.jantina === 'Perempuan' ? 'selected' : ''}>Perempuan</option>
                            </select>
                        </div>
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">No Telefon</label>
                            <input type="text" id="editNoTelefon" value="${(p.no_telefon || '').replace(/"/g, '"')}" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="012-3456789">
                        </div>
                    </div>
                    <div class="flex gap-3">
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Status Sokongan</label>
                            <select id="editSokongan" class="w-full px-3 py-2 text-sm border rounded-lg">
                                <option value="">- Pilih -</option>
                                <option value="Putih" ${p.status_sokongan === 'Putih' ? 'selected' : ''}>Putih</option>
                                <option value="Hitam" ${p.status_sokongan === 'Hitam' ? 'selected' : ''}>Hitam</option>
                                <option value="Atas Pagar" ${p.status_sokongan === 'Atas Pagar' ? 'selected' : ''}>Atas Pagar</option>
                                <option value="Tiada" ${p.status_sokongan === 'Tiada' || !p.status_sokongan ? 'selected' : ''}>Tiada Data</option>
                            </select>
                        </div>
                        <div class="flex-1">
                            <label class="block text-sm font-medium text-gray-600 mb-1">Status Fizikal</label>
                            <select id="editFizikal" class="w-full px-3 py-2 text-sm border rounded-lg">
                                <option value="Hidup" ${p.status_fizikal === 'Hidup' || !p.status_fizikal ? 'selected' : ''}>Hidup</option>
                                <option value="Meninggal" ${p.status_fizikal === 'Meninggal' ? 'selected' : ''}>Meninggal</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="flex gap-2 p-4 border-t">
                    <button onclick="this.closest('#editModalOverlay').remove()" class="btn btn-outline flex-1">Batal</button>
                    <button onclick="savePengundi('${p.id}')" class="btn btn-primary flex-1">Simpan</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        
        const editLokalitiSelect = document.getElementById('editLokaliti');
        if (editLokalitiSelect && p.lokaliti) {
            const matchingOption = Array.from(editLokalitiSelect.options).find(o => o.value === p.lokaliti);
            if (matchingOption) {
                editLokalitiSelect.value = p.lokaliti;
                const btnHapus = document.getElementById('editBtnHapusLokaliti');
                if (btnHapus) btnHapus.classList.remove('hidden');
            }
        }
        
        const editDunSelect = document.getElementById('editDun');
        const editBtnHapus = document.getElementById('editBtnHapusDun');
        if (editDunSelect && editBtnHapus) {
            const coreDuns = ['N12', 'N13', 'N14', 'N15'];
            editDunSelect.addEventListener('change', function() {
                if (coreDuns.includes(this.value)) {
                    editBtnHapus.classList.add('hidden');
                } else if (this.value && this.value !== 'TAMBAH_DUN') {
                    editBtnHapus.classList.remove('hidden');
                } else {
                    editBtnHapus.classList.add('hidden');
                }
            });
            if (coreDuns.includes(editDunSelect.value)) {
                editBtnHapus.classList.add('hidden');
            } else if (editDunSelect.value && editDunSelect.value !== 'TAMBAH_DUN') {
                editBtnHapus.classList.remove('hidden');
            }
        }
    } catch (err) {
        showToast('Gagal memuat data pengundi: ' + err.message, 'error');
    } finally {
        window._editModalBusy = false;
    }
}

async function savePengundi(id) {
    const pegawaiVal = document.getElementById('editPegawai').value.trim();
    const kkVal = document.getElementById('editKetuaKeluarga').value.trim();
    const data = {
        nama_penuh: document.getElementById('editNama').value.trim(),
        jantina: document.getElementById('editJantina').value || null,
        tahun_lahir: parseInt(document.getElementById('editTahunLahir').value) || null,
        dm: document.getElementById('editDm').value.trim(),
        lokaliti: document.getElementById('editLokaliti').value.trim() || null,
        no_telefon: document.getElementById('editNoTelefon').value.trim() || null,
        status_sokongan: document.getElementById('editSokongan').value || null,
        status_fizikal: document.getElementById('editFizikal').value || null,
        dun: document.getElementById('editDun').value || null,
        ketua_keluarga_id: parsePengundiId(kkVal),
        pegawai_penyelaras_id: parsePengundiId(pegawaiVal)
    };
    Object.keys(data).forEach(k => { if (data[k] === '') data[k] = null; });
    try {
        await api(`/api/pengundi/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        document.getElementById('editModalOverlay')?.remove();
        showToast('Pengundi berjaya dikemaskini', 'success');
        renderPengundi();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

function editDunChanged() {
    const dunKod = document.getElementById('editDun').value;
    const dmInput = document.getElementById('editDm');
    const dunBaruContainer = document.getElementById('editDunBaruContainer');
    const btnHapusPdm = document.getElementById('editBtnHapusPdm');
    
    if (dunKod === 'TAMBAH_DUN') {
        if (dunBaruContainer) dunBaruContainer.style.display = 'block';
        return;
    } else {
        if (dunBaruContainer) dunBaruContainer.style.display = 'none';
    }
    
    const editBtnHapus = document.getElementById('editBtnHapusDun');
    const coreDuns = ['N12', 'N13', 'N14', 'N15'];
    if (editBtnHapus) {
        if (coreDuns.includes(dunKod)) {
            editBtnHapus.classList.add('hidden');
        } else if (dunKod && dunKod !== 'TAMBAH_DUN') {
            editBtnHapus.classList.remove('hidden');
        } else {
            editBtnHapus.classList.add('hidden');
        }
    }
    
    if (btnHapusPdm) btnHapusPdm.classList.add('hidden');
    
    if (dmInput) {
        const pdmOptions = renderDunPdmDataList(dunKod || '')
            .split('</option>')
            .filter(o => o.trim())
            .map(o => o + '</option>')
            .join('');
        dmInput.innerHTML = '<option value="">- Pilih PDM -</option>' +
            '<option value="TAMBAH_PDM" style="color:#2563eb;font-weight:600;">➕ Tambah PDM Baru</option>' +
            pdmOptions;
        dmInput.value = '';
    }
    refreshEditLokaliti(dunKod, '');
}

function editPdmChanged() {
    const pdmVal = document.getElementById('editDm').value;
    const pdmBaruContainer = document.getElementById('editPdmBaruContainer');
    const btnHapus = document.getElementById('editBtnHapusPdm');
    const dunKod = document.getElementById('editDun').value;
    
    if (pdmVal === 'TAMBAH_PDM' || pdmVal === '') {
        if (pdmBaruContainer) pdmBaruContainer.style.display = pdmVal === 'TAMBAH_PDM' ? 'block' : 'none';
        if (btnHapus) btnHapus.classList.add('hidden');
        return;
    }
    
    if (pdmBaruContainer) pdmBaruContainer.style.display = 'none';
    document.getElementById('editPdmBaru').value = '';
    if (btnHapus) btnHapus.classList.remove('hidden');
    
    refreshEditLokaliti(dunKod, pdmVal);
}

function editLokalitiChanged() {
    const lokalitiVal = document.getElementById('editLokaliti').value;
    const lokalitiBaruContainer = document.getElementById('editLokalitiBaruContainer');
    const btnHapus = document.getElementById('editBtnHapusLokaliti');
    
    if (lokalitiVal === 'TAMBAH_LOKALITI' || lokalitiVal === '') {
        if (lokalitiBaruContainer) lokalitiBaruContainer.style.display = lokalitiVal === 'TAMBAH_LOKALITI' ? 'block' : 'none';
        if (btnHapus) btnHapus.classList.add('hidden');
        return;
    }
    
    if (lokalitiBaruContainer) lokalitiBaruContainer.style.display = 'none';
    document.getElementById('editLokalitiBaru').value = '';
    if (btnHapus) btnHapus.classList.remove('hidden');
}

function editTambahLokalitiBaruSekarang() {
    const lokalitiInput = document.getElementById('editLokalitiBaru');
    const lokalitiVal = lokalitiInput.value.trim();
    const dm = document.getElementById('editDm').value;
    if (!lokalitiVal) {
        showToast('Sila masukkan nama Lokaliti baru', 'error');
        return;
    }
    if (!dm) {
        showToast('Sila pilih PDM dahulu sebelum tambah Lokaliti', 'error');
        return;
    }
    api('/api/lokaliti', {
        method: 'POST',
        body: JSON.stringify({ nama: lokalitiVal, dm: dm })
    }).then(result => {
        showToast(`Lokaliti ${lokalitiVal} berjaya ditambah!`, 'success');
        lokalitiInput.value = '';
        document.getElementById('editLokalitiBaruContainer').style.display = 'none';
        const lokalitiSelect = document.getElementById('editLokaliti');
        lokalitiSelect.innerHTML += `<option value="${lokalitiVal.toUpperCase()}">${lokalitiVal.toUpperCase()}</option>`;
        lokalitiSelect.value = lokalitiVal.toUpperCase();
        editLokalitiChanged();
    }).catch(err => {
        showToast('Gagal cipta Lokaliti baru: ' + err.message, 'error');
    });
}

function editHapusLokaliti() {
    const lokalitiVal = document.getElementById('editLokaliti').value;
    if (!lokalitiVal || lokalitiVal === 'TAMBAH_LOKALITI') return;
    if (!confirm(`Anda pasti mahu memadamkan Lokaliti ${lokalitiVal}? Tindakan ini tidak boleh dikembalikan.`)) return;
    api(`/api/lokaliti/${encodeURIComponent(lokalitiVal)}`, { method: 'DELETE' }).then(result => {
        showToast(`Lokaliti ${lokalitiVal} berjaya dipadamkan!`, 'success');
        const lokalitiSelect = document.getElementById('editLokaliti');
        Array.from(lokalitiSelect.options).forEach((opt, i) => {
            if (opt.value === lokalitiVal) lokalitiSelect.remove(i);
        });
        lokalitiSelect.value = '';
        document.getElementById('editBtnHapusLokaliti').classList.add('hidden');
    }).catch(err => {
        showToast(err.message, 'error');
    });
}

function editTambahDunBaruSekarang() {
    const dunBaruInput = document.getElementById('editDunBaru');
    const dunBaruVal = dunBaruInput.value.trim();
    if (!dunBaruVal) {
        showToast('Sila masukkan nama DUN baru (cth: N16 - BANGGI)', 'error');
        return;
    }
    const dashIdx = dunBaruVal.indexOf('-');
    let dunKod = '', dunNama = '';
    if (dashIdx > -1) {
        dunKod = dunBaruVal.substring(0, dashIdx).trim().toUpperCase();
        dunNama = dunBaruVal.substring(dashIdx + 1).trim().toUpperCase();
    } else {
        dunKod = dunBaruVal.trim().toUpperCase();
        dunNama = dunKod;
    }
    if (!dunKod) {
        showToast('Format DUN baru tidak sah. Guna format: N16 - BANGGI', 'error');
        return;
    }
    api('/api/dun', {
        method: 'POST',
        body: JSON.stringify({ kod: dunKod, nama: dunNama })
    }).then(result => {
        showToast(`DUN ${dunKod} - ${dunNama} berjaya ditambah!`, 'success');
        dunBaruInput.value = '';
        document.getElementById('editDunBaruContainer').style.display = 'none';
        api('/api/dun').then(dunList => {
            const dunSelect = document.getElementById('editDun');
            dunSelect.innerHTML = `
                <option value="">- Pilih DUN -</option>
                <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                ${dunList.map(d => `<option value="${d.kod}" ${d.kod === result.kod ? 'selected' : ''}>${d.nama} (${d.jumlah_pengundi || 0})</option>`).join('')}
            `;
            editDunChanged();
        });
    }).catch(err => {
        showToast('Gagal cipta DUN baru: ' + err.message, 'error');
    });
}

function editHapusDun() {
    const dunKod = document.getElementById('editDun').value;
    if (!dunKod || dunKod === 'TAMBAH_DUN') return;
    if (!confirm(`Anda pasti mahu memadamkan DUN ${dunKod}? Tindakan ini tidak boleh dikembalikan.`)) return;
    api(`/api/dun/${dunKod}`, { method: 'DELETE' }).then(result => {
        showToast(`DUN ${dunKod} berjaya dipadamkan!`, 'success');
        api('/api/dun').then(dunList => {
            const dunSelect = document.getElementById('editDun');
            dunSelect.innerHTML = `
                <option value="">- Pilih DUN -</option>
                <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                ${dunList.map(d => `<option value="${d.kod}">${d.nama} (${d.jumlah_pengundi || 0})</option>`).join('')}
            `;
            dunSelect.value = '';
            document.getElementById('editBtnHapusDun').classList.add('hidden');
            editDunChanged();
        });
    }).catch(err => {
        showToast(err.message, 'error');
    });
}

let editPengundiSearchTimeout = null;

function cariEditPegawaiPenyelaras(input) {
    clearTimeout(editPengundiSearchTimeout);
    const q = input.value.trim();
    if (q.length < 1) return;
    editPengundiSearchTimeout = setTimeout(async () => {
        const results = await fetchPpOptions(q);
        const dl = document.getElementById('editPegawaiList');
        if (dl) dl.innerHTML = results.map(p => `<option value="${p.id} - ${p.nama_penuh}">`).join('');
    }, 300);
}

function cariEditKetuaKeluarga(input) {
    clearTimeout(editPengundiSearchTimeout);
    const q = input.value.trim();
    if (q.length < 1) return;
    editPengundiSearchTimeout = setTimeout(async () => {
        const results = await fetchKkOptions(q);
        const dl = document.getElementById('editKkList');
        if (dl) dl.innerHTML = results.map(p => `<option value="${p.id} - ${p.nama_penuh}">`).join('');
    }, 300);
}

async function padamPengundi(id) {
    setTimeout(() => {
        if (!confirm('Anda pasti mahu memadamkan rekod pengundi ini? Tindakan ini tidak boleh dikembalikan.')) return;
        api(`/api/pengundi/${id}`, { method: 'DELETE' }).then(result => {
            showToast(result.message || 'Pengundi berjaya dipadamkan', 'success');
            requestAnimationFrame(() => {
                renderPengundi();
            });
        }).catch(err => {
            showToast('Ralat: ' + err.message, 'error');
        });
    }, 0);
}

const DUN_OPTIONS = [
    { kod: 'N12', nama: 'N12 SULAMAN' },
    { kod: 'N13', nama: 'N13 PANTAI DALIT' },
    { kod: 'N14', nama: 'N14 TAMPARULI' },
    { kod: 'N15', nama: 'N15 KIULU' }
];

function parseIcToDob(ic) {
    const digits = ic.replace(/\D/g, '');
    if (digits.length < 6) return { hari: '', bulan: '', tahun: '' };
    const yy = parseInt(digits.substring(0, 2), 10);
    const mm = digits.substring(2, 4);
    const dd = digits.substring(4, 6);
    const yyyy = yy < 30 ? 2000 + yy : 1900 + yy;
    return { hari: dd, bulan: mm, tahun: String(yyyy) };
}

function getPdmListForDun(dunKod) {
    if (!dunKod) {
        const all = [];
        Object.values(PDM_BY_DUN).forEach(list => all.push(...list));
        return all.filter((v, i, a) => a.indexOf(v) === i);
    }
    return PDM_BY_DUN[dunKod] || [];
}

function renderDunPdmDataList(dunKod, selectedDm) {
    const pdmNames = getPdmListForDun(dunKod);
    return pdmNames.map(nama => {
        const found = (state.pdmList || []).find(p => p.nama === nama);
        const count = found ? found.jumlah_pengundi : 0;
        const sel = nama === selectedDm ? ' selected' : '';
        return `<option value="${nama}"${sel}>${nama} (${count.toLocaleString()})</option>`;
    }).join('');
}

let cachedLokaliti = null;

async function getLokalitiList(dunKod) {
    try {
        const url = dunKod ? `/api/lokaliti?dun=${encodeURIComponent(dunKod)}` : '/api/lokaliti';
        const res = await api(url);
        return res || [];
    } catch {
        return [];
    }
}

async function tambahPengundi() {
    if (window._tambahModalBusy) return;
    window._tambahModalBusy = true;

    const existingOverlay = document.getElementById('tambahModalOverlay');
    if (existingOverlay) existingOverlay.remove();
    
    const overlay = document.createElement('div');
    overlay.id = 'tambahModalOverlay';
    overlay.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `<div class="bg-white rounded-xl p-6 text-center shadow-lg font-medium">Memuatkan borang tambah pengundi...</div>`;
    document.body.appendChild(overlay);

    try {
        const lokalitiList = await getLokalitiList();
        const lokalitiOptions = (lokalitiList || []).map(l => `<option value="${l.nama}">${l.nama} (${l.jumlah_pengundi || 0})</option>`).join('');

        const [kkOptions, ppOptions] = await Promise.all([
            fetchKkOptions(''),
            fetchPpOptions('')
        ]);
        const kkOptHtml = kkOptions.map(k => `<option value="${k.id} - ${k.nama_penuh}">${k.nama_penuh}</option>`).join('');
        const ppOptHtml = ppOptions.map(p => `<option value="${p.id} - ${p.nama_penuh}">${p.nama_penuh}</option>`).join('');

        let dunList = [];
        try {
            dunList = await api('/api/dun');
        } catch (e) {
            dunList = DUN_OPTIONS;
        }

        const defaultDun = '';
        const initialPdmOptions = renderDunPdmDataList(defaultDun);

        overlay.innerHTML = `
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div class="flex items-center justify-between p-4 border-b">
                <h3 class="text-lg font-semibold text-gray-800">Tambah Pengundi Baru</h3>
                <button onclick="this.closest('#tambahModalOverlay').remove()" class="text-gray-400 hover:text-red-500 text-2xl leading-none">&times;</button>
            </div>
            <div class="p-4 space-y-3">
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Parlimen</label>
                    <select id="tambahParlimen" class="w-full px-3 py-2 text-sm border rounded-lg bg-gray-100 text-gray-500" disabled>
                        <option value="P170" selected>P170 Tuaran</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">DUN <span class="text-red-500">*</span></label>
                    <div class="flex gap-2">
                        <select id="tambahDun" onchange="tambahDunChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Pilih DUN -</option>
                            <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                        ${dunList.map(d => `<option value="${d.kod}">${d.nama} (${d.jumlah_pengundi || 0})</option>`).join('')}
                        </select>
                        <button id="btnHapusDun" onclick="hapusDun()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam DUN">🗑️</button>
                    </div>
                </div>
                <div id="tambahDunBaruContainer" style="display:none;">
                    <label class="block text-sm font-medium text-gray-600 mb-1">Nama DUN Baru <span class="text-red-500">*</span></label>
                    <div class="flex gap-2">
                        <input type="text" id="tambahDunBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: N16 - BANGGI">
                        <button onclick="tambahDunBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah DUN</button>
                    </div>
                    <p class="text-xs text-gray-400 mt-0.5">Masukkan kod dan nama DUN baru, cth: N16 - BANGGI. Klik "Tambah DUN" untuk create.</p>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">PDM <span class="text-red-500">*</span></label>
                    <div class="flex gap-2">
                        <select id="tambahDm" onchange="tambahPdmChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Pilih PDM -</option>
                            <option value="TAMBAH_PDM" style="color:#2563eb;font-weight:600;">➕ Tambah PDM Baru</option>
                            ${initialPdmOptions.split('</option>').filter(o => o.trim()).map(o => o + '</option>').join('') || ''}
                        </select>
                        <button id="btnHapusPdm" onclick="hapusPdm()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam PDM">🗑️</button>
                    </div>
                    <div id="tambahPdmBaruContainer" style="display:none;" class="mt-2">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Nama PDM Baru <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <input type="text" id="tambahPdmBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: BARU-BARU">
                            <button onclick="tambahPdmBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah PDM</button>
                        </div>
                        <p class="text-xs text-gray-400 mt-0.5">Masukkan nama PDM baru. Klik "Tambah PDM" untuk create.</p>
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Lokaliti <span class="text-red-500">*</span></label>
                    <div class="flex gap-2">
                        <select id="tambahLokaliti" onchange="tambahLokalitiChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Pilih Lokaliti -</option>
                            <option value="TAMBAH_LOKALITI" style="color:#2563eb;font-weight:600;">➕ Tambah Lokaliti Baru</option>
                            ${lokalitiOptions}
                        </select>
                        <button id="btnHapusLokaliti" onclick="hapusLokaliti()" class="btn btn-outline text-sm px-2 py-1 text-red-600 border-red-300 hover:bg-red-50 hidden" title="Padam Lokaliti">🗑️</button>
                    </div>
                    <div id="tambahLokalitiBaruContainer" style="display:none;" class="mt-2">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Nama Lokaliti Baru <span class="text-red-500">*</span></label>
                        <div class="flex gap-2">
                            <input type="text" id="tambahLokalitiBaru" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Contoh: KAMPUNG BARU">
                            <button onclick="tambahLokalitiBaruSekarang()" class="btn btn-primary whitespace-nowrap text-sm px-3">➕ Tambah Lokaliti</button>
                        </div>
                        <p class="text-xs text-gray-400 mt-0.5">Masukkan nama Lokaliti baru. Klik "Tambah Lokaliti" untuk create.</p>
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Pegawai Penyelaras</label>
                    <select id="tambahPegawai" class="w-full px-3 py-2 text-sm border rounded-lg">
                        <option value="">- Tiada / Kosong -</option>
                        ${ppOptions.map(p => {
                            const val = `${p.id} - ${p.nama_penuh}`;
                            return `<option value="${val}">${p.nama_penuh}</option>`;
                        }).join('')}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Ketua Keluarga</label>
                    <select id="tambahKetuaKeluarga" class="w-full px-3 py-2 text-sm border rounded-lg">
                        <option value="">- Tiada / Kosong -</option>
                        ${kkOptHtml}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">Nama Penuh <span class="text-red-500">*</span></label>
                    <input type="text" id="tambahNama" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="Nama penuh tanpa singkatan">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-600 mb-1">No KP</label>
                    <input type="text" id="tambahNoKp" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="000101-01-0001">
                </div>
                <div class="flex gap-2">
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Hari Lahir</label>
                        <input type="text" id="tambahHariLahir" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="DD">
                    </div>
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Bulan Lahir</label>
                        <input type="text" id="tambahBulanLahir" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="MM">
                    </div>
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Tahun Lahir</label>
                        <input type="text" id="tambahTahunLahir" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="YYYY">
                    </div>
                </div>
                <div class="flex gap-3">
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Jantina</label>
                        <select id="tambahJantina" class="w-full px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Pilih -</option>
                            <option value="L">Lelaki</option>
                            <option value="P">Perempuan</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">No Telefon</label>
                        <input type="text" id="tambahNoTelefon" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="012-3456789">
                    </div>
                </div>
                <div class="flex gap-3">
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Status Sokongan</label>
                        <select id="tambahSokongan" class="w-full px-3 py-2 text-sm border rounded-lg">
                            <option value="">- Pilih -</option>
                            <option value="Putih">Putih</option>
                            <option value="Hitam">Hitam</option>
                            <option value="Atas Pagar">Atas Pagar</option>
                            <option value="Tiada">Tiada Data</option>
                        </select>
                    </div>
                    <div class="flex-1">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Status Fizikal</label>
                        <select id="tambahFizikal" class="w-full px-3 py-2 text-sm border rounded-lg">
                            <option value="Hidup">Hidup</option>
                            <option value="Meninggal">Meninggal</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="flex gap-2 p-4 border-t">
                <button onclick="this.closest('#tambahModalOverlay').remove()" class="btn btn-outline flex-1">Batal</button>
                <button onclick="simpanPengundiBaru()" class="btn btn-primary flex-1">Daftar Pengundi</button>
            </div>
        </div>
    `;
        document.body.appendChild(overlay);
    } catch (err) {
        showToast('Gagal: ' + err.message, 'error');
    } finally {
        window._tambahModalBusy = false;
    }
}

async function fetchKkOptions(query) {
    try {
        const result = await api(`/api/ketua-keluarga/search?q=${encodeURIComponent(query)}&per_page=200`);
        return result.data || [];
    } catch {
        return [];
    }
}

async function fetchPpOptions(query) {
    try {
        const result = await api(`/api/pegawai-penyelaras/search?q=${encodeURIComponent(query)}&per_page=200`);
        return result.data || [];
    } catch {
        return [];
    }
}

function parsePengundiId(inputValue) {
    if (!inputValue) return null;
    const match = inputValue.match(/^(\d+)\s*-\s*/);
    return match ? parseInt(match[1], 10) : null;
}

let pengundiSearchTimeout = null;

function cariPegawaiPenyelaras(input) {
    clearTimeout(pengundiSearchTimeout);
    const q = input.value.trim();
    if (q.length < 1) return;
    pengundiSearchTimeout = setTimeout(async () => {
        const results = await fetchPpOptions(q);
        const dl = document.getElementById('tambahPegawaiList');
        if (dl) dl.innerHTML = results.map(p => `<option value="${p.id} - ${p.nama_penuh}">`).join('');
    }, 300);
}

function cariKetuaKeluarga(input) {
    clearTimeout(pengundiSearchTimeout);
    const q = input.value.trim();
    if (q.length < 1) return;
    pengundiSearchTimeout = setTimeout(async () => {
        const results = await fetchKkOptions(q);
        const dl = document.getElementById('tambahKkList');
        if (dl) dl.innerHTML = results.map(p => `<option value="${p.id} - ${p.nama_penuh}">`).join('');
    }, 300);
}

function tambahPdmChanged() {
    const pdmVal = document.getElementById('tambahDm').value;
    const pdmBaruContainer = document.getElementById('tambahPdmBaruContainer');
    const btnHapus = document.getElementById('btnHapusPdm');
    
    if (pdmVal === 'TAMBAH_PDM' || pdmVal === '') {
        if (pdmBaruContainer) pdmBaruContainer.style.display = pdmVal === 'TAMBAH_PDM' ? 'block' : 'none';
        if (btnHapus) btnHapus.classList.add('hidden');
        return;
    }
    
    if (pdmBaruContainer) pdmBaruContainer.style.display = 'none';
    document.getElementById('tambahPdmBaru').value = '';
    if (btnHapus) btnHapus.classList.remove('hidden');
    
    const dunKod = document.getElementById('tambahDun').value;
    refreshTambahLokaliti(dunKod, pdmVal);
}

function tambahPdmBaruSekarang() {
    const pdmInput = document.getElementById('tambahPdmBaru');
    const pdmVal = pdmInput.value.trim();
    const dunKod = document.getElementById('tambahDun').value;
    if (!pdmVal) {
        showToast('Sila masukkan nama PDM baru', 'error');
        return;
    }
    api('/api/pdm', {
        method: 'POST',
        body: JSON.stringify({ nama: pdmVal, dun_kod: dunKod })
    }).then(result => {
        showToast(`PDM ${pdmVal} berjaya ditambah!`, 'success');
        pdmInput.value = '';
        document.getElementById('tambahPdmBaruContainer').style.display = 'none';
        const pdmSelect = document.getElementById('tambahDm');
        pdmSelect.innerHTML += `<option value="${pdmVal}">${pdmVal}</option>`;
        pdmSelect.value = pdmVal;
        tambahPdmChanged();
        refreshTambahLokaliti(dunKod, pdmVal);
    }).catch(err => {
        showToast('Gagal cipta PDM baru: ' + err.message, 'error');
    });
}

function hapusPdm() {
    const pdmVal = document.getElementById('tambahDm').value;
    if (!pdmVal || pdmVal === 'TAMBAH_PDM') return;
    if (!confirm(`Anda pasti mahu memadamkan PDM ${pdmVal}? Tindakan ini tidak boleh dikembalikan.`)) return;
    api(`/api/pdm/${encodeURIComponent(pdmVal)}`, { method: 'DELETE' }).then(result => {
        showToast(`PDM ${pdmVal} berjaya dipadamkan!`, 'success');
        const pdmSelect = document.getElementById('tambahDm');
        Array.from(pdmSelect.options).forEach((opt, i) => {
            if (opt.value === pdmVal) pdmSelect.remove(i);
        });
        pdmSelect.value = '';
        document.getElementById('btnHapusPdm').classList.add('hidden');
    }).catch(err => {
        showToast(err.message, 'error');
    });
}

function tambahLokalitiChanged() {
    const lokalitiVal = document.getElementById('tambahLokaliti').value;
    const lokalitiBaruContainer = document.getElementById('tambahLokalitiBaruContainer');
    const btnHapus = document.getElementById('btnHapusLokaliti');
    const dmVal = document.getElementById('tambahDm').value;
    
    if (lokalitiVal === 'TAMBAH_LOKALITI' || lokalitiVal === '') {
        if (lokalitiBaruContainer) lokalitiBaruContainer.style.display = lokalitiVal === 'TAMBAH_LOKALITI' ? 'block' : 'none';
        if (btnHapus) btnHapus.classList.add('hidden');
        return;
    }
    
    if (lokalitiBaruContainer) lokalitiBaruContainer.style.display = 'none';
    document.getElementById('tambahLokalitiBaru').value = '';
    if (btnHapus) btnHapus.classList.remove('hidden');
}

function tambahLokalitiBaruSekarang() {
    const lokalitiInput = document.getElementById('tambahLokalitiBaru');
    const lokalitiVal = lokalitiInput.value.trim();
    const dm = document.getElementById('tambahDm').value;
    if (!lokalitiVal) {
        showToast('Sila masukkan nama Lokaliti baru', 'error');
        return;
    }
    if (!dm) {
        showToast('Sila pilih PDM dahulu sebelum tambah Lokaliti', 'error');
        return;
    }
    api('/api/lokaliti', {
        method: 'POST',
        body: JSON.stringify({ nama: lokalitiVal, dm: dm })
    }).then(result => {
        showToast(`Lokaliti ${lokalitiVal} berjaya ditambah!`, 'success');
        lokalitiInput.value = '';
        document.getElementById('tambahLokalitiBaruContainer').style.display = 'none';
        const lokalitiSelect = document.getElementById('tambahLokaliti');
        lokalitiSelect.innerHTML += `<option value="${lokalitiVal.toUpperCase()}">${lokalitiVal.toUpperCase()}</option>`;
        lokalitiSelect.value = lokalitiVal.toUpperCase();
        tambahLokalitiChanged();
    }).catch(err => {
        showToast('Gagal cipta Lokaliti baru: ' + err.message, 'error');
    });
}

function hapusLokaliti() {
    const lokalitiVal = document.getElementById('tambahLokaliti').value;
    if (!lokalitiVal || lokalitiVal === 'TAMBAH_LOKALITI') return;
    if (!confirm(`Anda pasti mahu memadamkan Lokaliti ${lokalitiVal}? Tindakan ini tidak boleh dikembalikan.`)) return;
    api(`/api/lokaliti/${encodeURIComponent(lokalitiVal)}`, { method: 'DELETE' }).then(result => {
        showToast(`Lokaliti ${lokalitiVal} berjaya dipadamkan!`, 'success');
        const lokalitiSelect = document.getElementById('tambahLokaliti');
        Array.from(lokalitiSelect.options).forEach((opt, i) => {
            if (opt.value === lokalitiVal) lokalitiSelect.remove(i);
        });
        lokalitiSelect.value = '';
        document.getElementById('btnHapusLokaliti').classList.add('hidden');
    }).catch(err => {
        showToast(err.message, 'error');
    });
}

async function refreshTambahLokaliti(dunKod, dmValue) {
    let params = '';
    if (dunKod) params += `dun=${encodeURIComponent(dunKod)}`;
    if (dmValue) params += (params ? '&' : '') + `dm=${encodeURIComponent(dmValue)}`;
    const url = params ? `/api/lokaliti?${params}` : '/api/lokaliti';
    try {
        const res = await api(url);
        const lokalitiSelect = document.getElementById('tambahLokaliti');
        if (lokalitiSelect) {
            const currentVal = lokalitiSelect.value;
            lokalitiSelect.innerHTML = `
                <option value="">- Pilih Lokaliti -</option>
                <option value="TAMBAH_LOKALITI" style="color:#2563eb;font-weight:600;">➕ Tambah Lokaliti Baru</option>
                ${(res || []).map(l => `<option value="${l.nama}">${l.nama} (${l.jumlah_pengundi || 0})</option>`).join('')}
            `;
            if (currentVal && Array.from(lokalitiSelect.options).some(o => o.value === currentVal)) {
                lokalitiSelect.value = currentVal;
            }
        }
    } catch (e) {
    }
}

async function refreshEditLokaliti(dunKod, dmValue) {
    let params = '';
    if (dunKod) params += `dun=${encodeURIComponent(dunKod)}`;
    if (dmValue) params += (params ? '&' : '') + `dm=${encodeURIComponent(dmValue)}`;
    const url = params ? `/api/lokaliti?${params}` : '/api/lokaliti';
    try {
        const res = await api(url);
        const lokalitiSelect = document.getElementById('editLokaliti');
        if (lokalitiSelect) {
            const currentVal = lokalitiSelect.value;
            lokalitiSelect.innerHTML = `
                <option value="">- Pilih Lokaliti -</option>
                <option value="TAMBAH_LOKALITI" style="color:#2563eb;font-weight:600;">➕ Tambah Lokaliti Baru</option>
                ${(res || []).map(l => `<option value="${l.nama}">${l.nama} (${l.jumlah_pengundi || 0})</option>`).join('')}
            `;
            if (currentVal && Array.from(lokalitiSelect.options).some(o => o.value === currentVal)) {
                lokalitiSelect.value = currentVal;
            }
        }
    } catch (e) {
    }
}

function tambahDunBaruSekarang() {
    const dunBaruInput = document.getElementById('tambahDunBaru');
    const dunBaruVal = dunBaruInput.value.trim();
    if (!dunBaruVal) {
        showToast('Sila masukkan nama DUN baru (cth: N16 - BANGGI)', 'error');
        return;
    }
    const dashIdx = dunBaruVal.indexOf('-');
    let dunKod = '', dunNama = '';
    if (dashIdx > -1) {
        dunKod = dunBaruVal.substring(0, dashIdx).trim().toUpperCase();
        dunNama = dunBaruVal.substring(dashIdx + 1).trim().toUpperCase();
    } else {
        dunKod = dunBaruVal.trim().toUpperCase();
        dunNama = dunKod;
    }
    if (!dunKod) {
        showToast('Format DUN baru tidak sah. Guna format: N16 - BANGGI', 'error');
        return;
    }
    api('/api/dun', {
        method: 'POST',
        body: JSON.stringify({ kod: dunKod, nama: dunNama })
    }).then(result => {
        showToast(`DUN ${dunKod} - ${dunNama} berjaya ditambah!`, 'success');
        dunBaruInput.value = '';
        document.getElementById('tambahDunBaruContainer').style.display = 'none';
        api('/api/dun').then(dunList => {
            const dunSelect = document.getElementById('tambahDun');
            dunSelect.innerHTML = `
                <option value="">- Pilih DUN -</option>
                <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                ${dunList.map(d => `<option value="${d.kod}">${d.nama} (${d.jumlah_pengundi || 0})</option>`).join('')}
            `;
            dunSelect.value = result.kod;
            tambahDunChanged();
            const dmDiv = document.getElementById('tambahDm')?.closest('div');
            const lokalitiDiv = document.getElementById('tambahLokaliti')?.closest('div');
            if (dmDiv) dmDiv.style.display = 'block';
            if (lokalitiDiv) lokalitiDiv.style.display = 'block';
            const pdmDl = document.getElementById('pdmList');
            if (pdmDl) pdmDl.innerHTML = '';
            document.getElementById('tambahDm').value = '';
            refreshTambahLokaliti(result.kod, '');
        });
    }).catch(err => {
        showToast('Gagal cipta DUN baru: ' + err.message, 'error');
    });
}

function hapusDun() {
    const dunKod = document.getElementById('tambahDun').value;
    if (!dunKod || dunKod === 'TAMBAH_DUN') return;
    if (!confirm(`Anda pasti mahu memadamkan DUN ${dunKod}? Tindakan ini tidak boleh dikembalikan.`)) return;
    api(`/api/dun/${dunKod}`, { method: 'DELETE' }).then(result => {
        showToast(`DUN ${dunKod} berjaya dipadamkan!`, 'success');
        api('/api/dun').then(dunList => {
            const dunSelect = document.getElementById('tambahDun');
            dunSelect.innerHTML = `
                <option value="">- Pilih DUN -</option>
                <option value="TAMBAH_DUN" style="color:#2563eb;font-weight:600;">➕ Tambah DUN Baru</option>
                ${dunList.map(d => `<option value="${d.kod}">${d.nama}</option>`).join('')}
            `;
            dunSelect.value = '';
            document.getElementById('btnHapusDun').classList.add('hidden');
        });
    }).catch(err => {
        showToast(err.message, 'error');
    });
}

function tambahDunChanged() {
    const dunKod = document.getElementById('tambahDun').value;
    const dunBaruContainer = document.getElementById('tambahDunBaruContainer');
    const dmDiv = document.getElementById('tambahDm')?.closest('div');
    const lokalitiDiv = document.getElementById('tambahLokaliti')?.closest('div');
    const btnHapus = document.getElementById('btnHapusDun');
    
    if (dunKod === 'TAMBAH_DUN' || dunKod === '') {
        if (dunBaruContainer) dunBaruContainer.style.display = dunKod === 'TAMBAH_DUN' ? 'block' : 'none';
        if (dmDiv) dmDiv.style.display = 'none';
        if (lokalitiDiv) lokalitiDiv.style.display = 'none';
        if (btnHapus) btnHapus.classList.add('hidden');
        if (dunKod === 'TAMBAH_DUN') document.getElementById('tambahDun').value = 'TAMBAH_DUN';
        return;
    }
    
    if (dunBaruContainer) {
        dunBaruContainer.style.display = 'none';
        document.getElementById('tambahDunBaru').value = '';
    }
    if (dmDiv) dmDiv.style.display = 'block';
    if (lokalitiDiv) lokalitiDiv.style.display = 'block';
    
    const coreDuns = ['N12', 'N13', 'N14', 'N15'];
    if (btnHapus) {
        if (coreDuns.includes(dunKod)) {
            btnHapus.classList.add('hidden');
        } else {
            btnHapus.classList.remove('hidden');
        }
    }
    
    const pdmList = getPdmListForDun(dunKod);
    const dmSelect = document.getElementById('tambahDm');
    dmSelect.innerHTML = '<option value="">- Pilih PDM -</option>' +
        '<option value="TAMBAH_PDM" style="color:#2563eb;font-weight:600;">➕ Tambah PDM Baru</option>' +
        renderDunPdmDataList(dunKod);
    dmSelect.value = '';
    document.getElementById('btnHapusPdm').classList.add('hidden');
    refreshTambahLokaliti(dunKod, '');
}

async function simpanPengundiBaru() {
    const nama_penuh = document.getElementById('tambahNama').value.trim();
    let dun = document.getElementById('tambahDun').value;
    const dm = document.getElementById('tambahDm').value.trim();
    const lokaliti = document.getElementById('tambahLokaliti').value.trim();
    const pegawaiVal = document.getElementById('tambahPegawai').value.trim();
    const kkVal = document.getElementById('tambahKetuaKeluarga').value.trim();
    const pegawaiId = parsePengundiId(pegawaiVal);
    const kkId = parsePengundiId(kkVal);
    const pegawaiNamaBaru = (!pegawaiId && pegawaiVal) ? pegawaiVal : null;
    const kkNamaBaru = (!kkId && kkVal) ? kkVal : null;

    if (dun === 'TAMBAH_DUN') {
        const dunBaruVal = document.getElementById('tambahDunBaru').value.trim();
        if (!dunBaruVal) {
            showToast('Sila masukkan nama DUN baru (cth: N16 - BANGGI)', 'error');
            return;
        }
        const dashIdx = dunBaruVal.indexOf('-');
        let dunKod = '', dunNama = '';
        if (dashIdx > -1) {
            dunKod = dunBaruVal.substring(0, dashIdx).trim().toUpperCase();
            dunNama = dunBaruVal.substring(dashIdx + 1).trim().toUpperCase();
        } else {
            dunKod = dunBaruVal.trim().toUpperCase();
            dunNama = dunKod;
        }
        if (!dunKod) {
            showToast('Format DUN baru tidak sah. Guna format: N16 - BANGGI', 'error');
            return;
        }
        try {
            const result = await api('/api/dun', {
                method: 'POST',
                body: JSON.stringify({ kod: dunKod, nama: dunNama })
            });
            dun = result.kod;
        } catch (err) {
            showToast('Gagal cipta DUN baru: ' + err.message, 'error');
            return;
        }
    }

    if (!nama_penuh || !dun || !dm || !lokaliti) {
        showToast('Sila isi ruangan wajib: DUN, PDM, Lokaliti, dan Nama Penuh', 'error');
        return;
    }

    const no_kp = document.getElementById('tambahNoKp').value.trim() || null;
    const tahunLahirInput = document.getElementById('tambahTahunLahir').value.trim();
    const tahunLahir = tahunLahirInput ? parseInt(tahunLahirInput, 10) : null;

    const data = {
        no_kp,
        nama_penuh,
        dun,
        dm,
        lokaliti,
        ketua_keluarga_id: kkId,
        pegawai_penyelaras_id: pegawaiId,
        ketua_keluarga_nama_baru: kkNamaBaru,
        pegawai_penyelaras_nama_baru: pegawaiNamaBaru,
        jantina: document.getElementById('tambahJantina').value || null,
        tahun_lahir: tahunLahir,
        no_telefon: document.getElementById('tambahNoTelefon').value.trim() || null,
        status_sokongan: document.getElementById('tambahSokongan').value || null,
        status_fizikal: document.getElementById('tambahFizikal').value || 'Hidup'
    };

    Object.keys(data).forEach(k => { if (data[k] === '') data[k] = null; });

    try {
        const result = await api('/api/pengundi', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        document.getElementById('tambahModalOverlay')?.remove();
        showToast(result.message || 'Pengundi baru berjaya didaftarkan', 'success');
        renderPengundi();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

let sortPengundiDir = { no_kp:'asc', nama_penuh:'asc', jantina:'asc', umur:'asc', dm:'asc', lokaliti:'asc', sokongan:'asc', ketua_keluarga:'asc', pegawai_penyelaras:'asc' };
function sortPengundi(field) {
    showToast('Fungsi susun sedang dalam pembangunan', 'success');
}

// ========= APPROVAL QUEUE =========
// NOTE: importFile — diisytiharkan dalam index.html inline script,
// jadi ia global dan tidak perlu diisytiharkan semula di sini.

async function renderApprovalQueue() {
    if (!checkAdmin()) { showToast('Akses ditolak. Hanya Admin dibenarkan.', 'error'); navigate('dashboard'); return; }
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan data kelulusan...</span></div>';
    try {
const result = await api(`/api/approval-queue/list?page=${state.approvalPage}`);
        const data = result.data || [];
        const total = result.total || 0;
        const perPage = result.per_page || 50;
        const totalPages = Math.ceil(total / perPage) || 1;
        content.innerHTML = `
            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-gray-800">Kelulusan Data</h3>
                    <span class="text-sm text-gray-500">${total} menunggu kelulusan</span>
                </div>
                ${data.length === 0 ? '<div class="text-center py-10 text-gray-400">Tiada data menunggu kelulusan.</div>' : `
                <div class="overflow-x-auto">
                    <table>
                        <thead><tr><th>Jenis</th><th>Data</th><th>Dimohon oleh</th><th>Tarikh</th><th>Tindakan</th></tr></thead>
                        <tbody>${data.map(q => {
                            const payload = q.data_payload || {};
                            const nama = payload.nama_penuh || payload.nama || '-';
                            const no_kp = payload.no_kp || '-';
                            const dm = payload.dm || '-';
                            const lok = payload.lokaliti || '-';
                            const detailText = 'KP: '+no_kp+', Nama: '+nama+', DM: '+dm+', Lok: '+lok;
                            return '<tr>'+
                            '<td><span class="badge badge-primary">'+(q.action_type||'-')+'</span><br><small class="text-xs text-gray-400">'+(q.target_table||'-')+'</small></td>'+
                            '<td class="text-xs max-w-xs truncate" title="'+detailText+'">'+detailText+'</td>'+
                            '<td class="text-sm">'+(q.requested_by||'-')+'</td>'+
                            '<td class="text-sm">'+(q.requested_at?new Date(q.requested_at).toLocaleDateString('ms-MY'):'-')+'</td>'+
                            '<td><div class="flex gap-2"><button onclick="approvePengundi('+q.id+')" class="btn btn-success text-xs py-1 px-2">Lulus</button><button onclick="rejectPengundi('+q.id+')" class="btn btn-danger text-xs py-1 px-2">Tolak</button></div></td>'+
                        '</tr>';}).join('')}</tbody>
                    </table>
                </div>
                <div class="pagination">${Array.from({length: Math.min(totalPages,10)},(_,i)=>i+1).map(p => '<button onclick="state.approvalPage='+p+';renderApprovalQueue()" class="'+(state.approvalPage===p?'active':'')+'">'+p+'</button>').join('')}
                    ${totalPages > 10 ? '<span class="text-sm text-gray-400">... '+totalPages+'</span>' : ''}</div>`}
            </div>`;
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

async function approvePengundi(id) {
    try {
        await api(`/api/approval-queue/${id}/approve`, { method: 'POST' });
        showToast('Data diluluskan!');
        renderApprovalQueue();
        updateApprovalBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

async function rejectPengundi(id) {
    try {
        await api(`/api/approval-queue/${id}/reject`, { method: 'POST' });
        showToast('Data ditolak');
        renderApprovalQueue();
        updateApprovalBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

async function updateApprovalBadge() {
    try {
const result = await api('/api/approval-queue/list?page=1&per_page=1');
        const badge = document.getElementById('approvalBadge');
        if (badge) {
            if (result.total > 0) { badge.textContent = result.total; badge.classList.remove('hidden'); }
            else badge.classList.add('hidden');
        }
    } catch (e) {}
}

// ========= AUDIT LOGS =========
async function renderAuditLogs() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan log aktiviti...</span></div>';
    try {
        const res = await api('/api/audit-logs?page=1&per_page=100');
        const logs = res.data || [];
        content.innerHTML = `
            <div class="card">
                <h3 class="font-semibold text-gray-800 mb-4">Log Aktiviti</h3>
                ${logs.length === 0 ? '<div class="text-center py-10 text-gray-400">Tiada log aktiviti.</div>' : `
                <div class="overflow-x-auto max-h-96 overflow-y-auto">
                    <table>
                        <thead><tr><th>Masa</th><th>Pengguna</th><th>Tindakan</th><th>Butiran</th></tr></thead>
                        <tbody>${logs.map(l => `<tr>
                            <td class="text-xs whitespace-nowrap">${l.dicipta_pada ? new Date(l.dicipta_pada).toLocaleString('ms-MY') : '-'}</td>
                            <td class="text-sm">${l.username || '-'}</td>
                            <td>${l.tindakan || '-'}</td>
                            <td class="text-sm text-gray-500">${l.penerangan || '-'}</td>
                        </tr>`).join('')}</tbody>
                    </table>
                </div>`}
            </div>`;
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

// ========= ROLE HELPER FUNCTIONS =========
const ROLE_RANK = {
    'Developer': 1,
    'Admin (System Preset)': 2,
    'Admin': 2,
    'Admin (Future creation / Custom Admin)': 3,
    'Admin (Custom)': 3,
    'Petugas 1 (System Preset)': 4,
    'Petugas 1 (Pegawai Penyelaras)': 5,
    'Petugas Padang': 5,
    'Petugas 2 (Ketua Keluarga)': 6,
    'Pemerhati': 7
};

const ROLE_LEGEND = [
    { rank: 1, peranan: 'Developer', badge: 'bh-badge-dev', css: 'background:#7c3aed;color:#fff;', akses: 'Full akses sistem (Superuser)' },
    { rank: 2, peranan: 'Admin (System Preset)', badge: 'bh-badge-admin-system', css: 'background:#2563eb;color:#fff;', akses: 'Semua pentadbiran & kelulusan' },
    { rank: 3, peranan: 'Admin (Custom)', badge: 'bh-badge-admin-custom', css: 'background:#0ea5e9;color:#fff;', akses: 'Semua pentadbiran & kelulusan' },
    { rank: 4, peranan: 'Petugas 1 (System Preset)', badge: 'bh-badge-petugas1-system', css: 'background:#16a34a;color:#fff;', akses: 'Urus pengundi & data lapangan, View-only Ketua Keluarga' },
    { rank: 5, peranan: 'Petugas 1 (Pegawai Penyelaras)', badge: 'bh-badge-petugas1-pp', css: 'background:#059669;color:#fff;', akses: 'Urus pengundi & data lapangan, View-only Ketua Keluarga' },
    { rank: 6, peranan: 'Petugas 2 (Ketua Keluarga)', badge: 'bh-badge-petugas2', css: 'background:#ea580c;color:#fff;', akses: 'Lihat & kemaskini KK' },
    { rank: 7, peranan: 'Pemerhati', badge: 'bh-badge-pemerhati', css: 'background:#6b7280;color:#fff;', akses: 'Lihat sahaja (Kecuali Pengurusan Pengguna & Log Aktiviti)' }
];

function getRoleRank(peranan) {
    return ROLE_RANK[peranan] || 99;
}

function getRoleBadge(peranan) {
    const map = {
        'Developer': 'bh-badge-dev',
        'Admin (System Preset)': 'bh-badge-admin-system',
        'Admin': 'bh-badge-admin-system',
        'Admin (Future creation / Custom Admin)': 'bh-badge-admin-custom',
        'Admin (Custom)': 'bh-badge-admin-custom',
        'Petugas 1 (System Preset)': 'bh-badge-petugas1-system',
        'Petugas 1 (Pegawai Penyelaras)': 'bh-badge-petugas1-pp',
        'Petugas Padang': 'bh-badge-petugas1-pp',
        'Petugas 2 (Ketua Keluarga)': 'bh-badge-petugas2',
        'Pemerhati': 'bh-badge-pemerhati'
    };
    return map[peranan] || 'badge-tiada';
}

function getRoleDisplayName(peranan) {
    const map = {
        'Petugas Padang': 'Petugas 1 (Pegawai Penyelaras)',
        'Admin': 'Admin (System Preset)',
        'Admin (Custom)': 'Admin (Future creation / Custom Admin)'
    };
    return map[peranan] || peranan || '-';
}

// ========= USER MANAGEMENT =========
async function renderUserManagement() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan pengguna...</span></div>';
    try {
        const users = await api('/api/users');
        // 🛡️ Sort by role hierarchy rank (strict ascending)
        users.sort((a, b) => getRoleRank(a.peranan) - getRoleRank(b.peranan));
        
        content.innerHTML = `
            <div class="card mb-4">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="font-semibold text-gray-800">Hirarki & Hak Akses</h3>
                    <button onclick="this.closest('.card').querySelector('.legend-body').classList.toggle('hidden')" class="text-sm text-blue-600 hover:text-blue-800 font-medium">Sembunyi / Tunjuk</button>
                </div>
                <div class="legend-body">
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="bg-gray-100">
                                    <th class="border border-gray-300 px-3 py-1.5 text-left font-semibold text-gray-700 w-12">#</th>
                                    <th class="border border-gray-300 px-3 py-1.5 text-left font-semibold text-gray-700">Peranan</th>
                                    <th class="border border-gray-300 px-3 py-1.5 text-left font-semibold text-gray-700">Akses Utama</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${ROLE_LEGEND.map(r => `
                                <tr class="hover:bg-gray-50">
                                    <td class="border border-gray-300 px-3 py-1.5 text-center font-bold text-gray-600">${r.rank}</td>
                                    <td class="border border-gray-300 px-3 py-1.5"><span class="badge ${r.badge}" style="${r.css}">${r.peranan}</span></td>
                                    <td class="border border-gray-300 px-3 py-1.5 text-gray-600">${r.akses}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                    <p class="text-xs text-gray-400 mt-2 italic">* Developer adalah superuser dengan akses penuh ke semua endpoint. Hanya boleh diurus melalui sistem sewaan.</p>
                </div>
            </div>

            <div class="card">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="font-semibold text-gray-800">Pengurusan Pengguna</h3>
                    <button onclick="showCreateUser()" class="btn btn-primary text-sm">+ Tambah Pengguna</button>
                </div>
                <div class="overflow-x-auto">
                    <table>
                        <thead><tr><th>Nama Pengguna</th><th>Nama Penuh</th><th>Peranan</th><th>Status</th><th>Tindakan</th></tr></thead>
                        <tbody>${users.map(u => {
                            const displayRole = getRoleDisplayName(u.peranan);
                            const badgeClass = getRoleBadge(u.peranan);
                            return `<tr>
                            <td class="font-medium">${u.username}</td>
                            <td>${u.nama_penuh || '-'}</td>
                            <td><span class="badge ${badgeClass}">${displayRole}</span></td>
                            <td>${u.aktif ? '<span class="text-green-600 font-medium">Aktif</span>' : '<span class="text-red-500">Tidak Aktif</span>'}</td>
                            <td><div class="flex gap-1"><button onclick="toggleUserActive(${u.id},${!u.aktif})" class="btn ${u.aktif?'btn-warning':'btn-success'} text-xs py-1 px-2">${u.aktif?'Nyahaktif':'Aktifkan'}</button><button onclick="deleteUser(${u.id})" class="btn btn-danger text-xs py-1 px-2">Padam</button></div></td>
                        </tr>`;
                        }).join('')}</tbody>
                    </table>
                </div>
                <p class="text-xs text-gray-400 mt-3">* Susunan mengikut hirarki: Developer → Admin → Petugas → Pemerhati</p>
            </div>`;
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

function showCreateUser() {
    const content = document.getElementById('contentArea');
    content.innerHTML = `
        <div class="max-w-md mx-auto">
            <div class="card">
                <h3 class="font-semibold text-gray-800 mb-4">Tambah Pengguna Baru</h3>
                <div class="space-y-3">
                    <div><label class="block text-sm font-medium mb-1">Nama Pengguna</label><input id="newUsername" class="w-full" placeholder="Nama pengguna"></div>
                    <div><label class="block text-sm font-medium mb-1">Nama Penuh</label><input id="newNamaPenuh" class="w-full" placeholder="Nama penuh"></div>
                    <div><label class="block text-sm font-medium mb-1">Kata Laluan</label><input id="newPassword" type="password" class="w-full" placeholder="Kata laluan"></div>
                    <div><label class="block text-sm font-medium mb-1">Peranan</label><select id="newPeranan" class="w-full">
                        <option value="Admin (System Preset)">Admin (System Preset)</option>
                        <option value="Admin (Future creation / Custom Admin)">Admin (Custom)</option>
                        <option value="Petugas 1 (System Preset)">Petugas 1 (System Preset)</option>
                        <option value="Petugas 1 (Pegawai Penyelaras)">Petugas 1 (Pegawai Penyelaras)</option>
                        <option value="Petugas 2 (Ketua Keluarga)">Petugas 2 (Ketua Keluarga)</option>
                        <option value="Pemerhati">Pemerhati</option>
                    </select></div>
                    <button onclick="createUser()" class="btn btn-primary w-full">Tambah Pengguna</button>
                    <button onclick="navigate('users')" class="btn btn-outline w-full">Batal</button>
                </div>
            </div>
        </div>`;
}

async function createUser() {
    const username = document.getElementById('newUsername').value.trim();
    const nama_penuh = document.getElementById('newNamaPenuh').value.trim();
    const kata_laluan = document.getElementById('newPassword').value;
    const peranan = document.getElementById('newPeranan').value;
    if (!username || !nama_penuh || !kata_laluan) { showToast('Sila isi semua ruangan', 'error'); return; }
    try {
        await api('/api/users', { method: 'POST', body: JSON.stringify({ username, nama_penuh, kata_laluan, peranan }) });
        showToast('Pengguna berjaya ditambah!');
        navigate('users');
    } catch (err) { showToast(err.message, 'error'); }
}

async function toggleUserActive(id, aktif) {
    try {
        await api(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify({ aktif }) });
        showToast(`Pengguna ${aktif?'diaktifkan':'dinyahaktifkan'}`);
        renderUserManagement();
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteUser(id) {
    if (!confirm('Anda pasti mahu memadamkan pengguna ini? Tindakan ini tidak boleh dikembalikan.')) return;
    try {
        await api(`/api/users/${id}`, { method: 'DELETE' });
        showToast('Pengguna berjaya dipadamkan!');
        renderUserManagement();
    } catch (err) { showToast(err.message, 'error'); }
}

// ========= IMPORT DATA =========
async function renderImportData() {
    const content = document.getElementById('contentArea');
    content.innerHTML = `
        <div class="grid grid-cols-1 gap-6">
            <div class="card"><div class="flex items-center gap-3 mb-4"><div class="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center"><svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg></div><div><h3 class="font-semibold text-gray-800">Import Data Pengundi</h3><p class="text-xs text-gray-500">Muat naik fail Excel untuk import data pengundi baru. Data perlu diluluskan oleh Admin.</p></div></div>
        <div class="flex gap-3 mb-4 flex-wrap"><button onclick="downloadTemplate()" class="btn btn-outline text-sm flex items-center gap-2"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg> Muat Turun Templat</button></div>
        <div class="mt-3 text-xs text-gray-400">Lajur wajib: NO KP, NAMA PENUH, JANTINA, TAHUN LAHIR, DM, LOKALITI</div></div>
        <div class="card"><div class="flex items-center gap-3 mb-4"><div class="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center"><svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg></div><div><h3 class="font-semibold text-gray-800">Muat Naik Fail Excel</h3><p class="text-xs text-gray-500">Seret dan lepas atau klik</p></div></div>
        <div id="dropZone" class="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition" onclick="document.getElementById('fileInput').click()" ondragover="event.preventDefault();this.classList.add('border-blue-500','bg-blue-50')" ondragleave="this.classList.remove('border-blue-500','bg-blue-50')" ondrop="event.preventDefault();this.classList.remove('border-blue-500','bg-blue-50');handleFileDrop(event)">
        <svg class="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
        <p class="text-sm text-gray-500" id="dropText">Klik atau seret fail ke sini</p><p class="text-xs text-gray-400 mt-1">Format: .xlsx</p></div>
        <input type="file" id="fileInput" accept=".xlsx,.xls" class="hidden" onchange="handleFileSelect(event)">
        <div id="fileInfo" class="hidden mt-3 p-3 bg-blue-50 rounded-lg flex items-center gap-3"><svg class="w-6 h-6 text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        <div class="flex-1 min-w-0"><p id="fileName" class="text-sm font-medium text-gray-700 truncate"></p><p id="fileSize" class="text-xs text-gray-500"></p></div>
        <button onclick="clearFile()" class="text-gray-400 hover:text-red-500"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button></div>
        <button id="importBtn" onclick="submitImport()" class="btn btn-primary w-full mt-4" disabled>📤 Import Data</button></div></div>
        <div id="importResult" class="hidden mt-6"></div>`;
}

function downloadTemplate() {
    const token = state.token;
    fetch(`${API_BASE}/api/pengundi/template`, { headers: { 'Authorization': `Bearer ${token}` } })
    .then(res => { if (!res.ok) throw new Error('Gagal muat turun'); return res.blob(); })
    .then(blob => { const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'TEMPLAT_IMPORT_PENGUNDI.xlsx'; document.body.appendChild(a); a.click(); document.body.removeChild(a); window.URL.revokeObjectURL(url); showToast('Templat berjaya dimuat turun!'); })
    .catch(err => showToast(err.message, 'error'));
}
function handleFileSelect(event) { const file = event.target.files[0]; if (file) setImportFile(file); }
function handleFileDrop(event) { const file = event.dataTransfer.files[0]; if (file) setImportFile(file); }
function setImportFile(file) {
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) { showToast('Sila pilih fail Excel', 'error'); return; }
    importFile = file;
    document.getElementById('fileInfo').classList.remove('hidden');
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = (file.size/1024).toFixed(1)+' KB';
    document.getElementById('importBtn').disabled = false;
    document.getElementById('dropText').textContent = 'Fail dipilih';
}
function clearFile() {
    importFile = null; document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').classList.add('hidden');
    document.getElementById('importBtn').disabled = true;
    document.getElementById('dropText').textContent = 'Klik atau seret fail ke sini';
}

async function submitImport() {
    if (!importFile) { showToast('Sila pilih fail terlebih dahulu', 'error'); return; }
    const btn = document.getElementById('importBtn');
    btn.disabled = true; btn.innerHTML = '<div class="loading-spinner"></div><span class="ml-2">Memproses...</span>';
    const resultDiv = document.getElementById('importResult');
    resultDiv.classList.remove('hidden');
    resultDiv.innerHTML = '<div class="card text-center py-8"><div class="loading-spinner mx-auto mb-3"></div><p class="text-gray-600">Sedang memproses...</p></div>';
    try {
        const formData = new FormData();
        formData.append('file', importFile);
        const res = await fetch(`${API_BASE}/api/pengundi/import-excel`, { method:'POST', headers:{ 'Authorization':`Bearer ${state.token}` }, body:formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ralat berlaku');
        resultDiv.innerHTML = `<div class="card"><div class="text-center mb-4"><div class="w-16 h-16 ${data.berjaya>0?'bg-green-100':'bg-red-100'} rounded-full flex items-center justify-center mx-auto mb-3"><svg class="w-8 h-8 ${data.berjaya>0?'text-green-600':'text-red-600'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">${data.berjaya>0?'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>':'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'}</svg></div>
        <h3 class="text-lg font-bold ${data.berjaya>0?'text-green-700':'text-red-700'}">${data.berjaya>0?'✅ Import Berjaya!':'❌ Import Gagal'}</h3></div>
        <div class="grid grid-cols-3 gap-4 text-center"><div class="p-3 bg-green-50 rounded-lg"><p class="text-2xl font-bold text-green-700">${data.berjaya}</p><p class="text-xs text-green-600">Berjaya</p></div><div class="p-3 bg-red-50 rounded-lg"><p class="text-2xl font-bold text-red-700">${data.gagal}</p><p class="text-xs text-red-600">Gagal</p></div><div class="p-3 bg-blue-50 rounded-lg"><p class="text-2xl font-bold text-blue-700">${data.jumlah}</p><p class="text-xs text-blue-600">Jumlah</p></div></div>
        <div class="mt-4 p-3 bg-amber-50 rounded-lg text-sm text-amber-700"><span>Data perlu diluluskan di <b>Kelulusan Data</b>.</span></div>
        <div class="flex gap-3 mt-4 justify-center"><button onclick="navigate('import')" class="btn btn-outline">Import Lagi</button><button onclick="navigate('approval')" class="btn btn-primary">Ke Kelulusan Data</button></div></div>`;
        showToast(`${data.berjaya} rekod berjaya diimport!`);
    } catch (err) {
        resultDiv.innerHTML = `<div class="card text-center py-8"><div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3"><svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
        <h3 class="text-lg font-bold text-red-700">Ralat</h3><p class="text-sm text-gray-600 mt-2">${err.message}</p><button onclick="navigate('import')" class="btn btn-outline mt-4">Cuba Lagi</button></div>`;
        showToast(err.message,'error');
    }
    btn.disabled = false; btn.innerHTML = '📤 Import Data'; clearFile();
}

// ========= KETUA KELUARGA HELPERS =========
let ketuaKeluargaState = { page: 1, search: '' };
function sanitizePhone(num) {
    if (!num) return '-';
    let cleaned = String(num).replace(/\.0+$/, '');
    return cleaned;
}

function renderDunPdmColumn(p) {
    const dunPart = (p.dun_kod && p.dun_nama) ? p.dun_kod + ' ' + p.dun_nama : '';
    const dmPart = p.dm || '';
    if (dunPart && dmPart) return dunPart + ' > ' + dmPart;
    return dunPart || dmPart || '-';
}

// ========= KETUA KELUARGA MANAGEMENT (Admin + Petugas 1 View-Only) =========
async function renderKetuaKeluarga() {
    const isViewOnly = checkPetugas1();
    if (!checkAdmin() && !checkPetugas1() && !checkPemerhati()) { showToast('Akses ditolak.', 'error'); navigate('dashboard'); return; }
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan data Ketua Keluarga...</span></div>';
    try {
        const [stats, result] = await Promise.all([
            api('/api/ketua-keluarga/stats'),
            api(`/api/ketua-keluarga/list?page=${ketuaKeluargaState.page}&search=${encodeURIComponent(ketuaKeluargaState.search)}`)
        ]);
        const ketua = result.data || [];
        const total = result.total || 0;
        const totalPages = result.total_pages || 1;

        content.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="card bg-gradient-to-br from-blue-50 to-blue-100 border-l-4 border-blue-500">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center text-white text-xl font-bold">${stats.total_ketua || 0}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Jumlah Ketua Keluarga</p><p class="text-lg font-bold text-gray-800">${stats.total_ketua || 0}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-green-50 to-green-100 border-l-4 border-green-500">
                    <div class="flex items-center gap-3">
                        <div class="w-auto min-w-[3rem] h-12 px-2 bg-green-500 rounded-xl flex items-center justify-center text-white text-base font-bold whitespace-nowrap">${(stats.ahli_terikat || 0).toLocaleString()}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Ahli Keluarga Terikat</p><p class="text-lg font-bold text-gray-800">${(stats.ahli_terikat || 0).toLocaleString()}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-amber-50 to-amber-100 border-l-4 border-amber-500">
                    <div class="flex items-center gap-3">
                        <div class="w-auto min-w-[3rem] h-12 px-2 bg-amber-500 rounded-xl flex items-center justify-center text-white text-base font-bold whitespace-nowrap">${stats.dun_coverage || '0/0'}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Liputan DUN</p><p class="text-lg font-bold text-gray-800">${stats.dun_coverage || '0/0'}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-purple-50 to-purple-100 border-l-4 border-purple-500">
                    <div class="flex items-center gap-3">
                        <div class="w-auto min-w-[3rem] h-12 px-2 bg-purple-500 rounded-xl flex items-center justify-center text-white text-base font-bold whitespace-nowrap">${stats.pdm_coverage || '0/0'}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Liputan PDM</p><p class="text-lg font-bold text-gray-800">${stats.pdm_coverage || '0/0'}</p></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
                    <h3 class="font-semibold text-gray-800">Senarai Ketua Keluarga</h3>
                    <div class="flex items-center gap-2">
                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Tambah Ketua Keluarga</button>' : (isViewOnly ? '<span class="text-xs text-amber-600 font-medium bg-amber-50 px-2 py-1 rounded-lg">(Lihat Sahaja / View Only)</span>' : '<button onclick="showTambahKetuaKeluarga()" class="btn btn-primary text-sm">+ Tambah Ketua Keluarga</button>')}
                        <span class="text-sm text-gray-500">${total.toLocaleString()} ketua keluarga</span>
                    </div>
                </div>
                <div class="flex items-center gap-2 mb-4">
                    <div class="relative flex-1 min-w-[200px]">
                        <input type="text" id="ketuaKeluargaSearch" placeholder="Cari nama atau No KP..." value="${ketuaKeluargaState.search}" onkeyup="if(event.key==='Enter'){ketuaKeluargaState.search=this.value;ketuaKeluargaState.page=1;renderKetuaKeluarga();}" class="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-lg">
                        <svg class="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                    </div>
                    <button onclick="ketuaKeluargaState.search=document.getElementById('ketuaKeluargaSearch').value;ketuaKeluargaState.page=1;renderKetuaKeluarga();" class="btn btn-primary text-sm py-2 px-3">Cari</button>
                    <button onclick="document.getElementById('ketuaKeluargaSearch').value='';ketuaKeluargaState.search='';ketuaKeluargaState.page=1;renderKetuaKeluarga();" class="btn btn-outline text-sm py-2 px-3">Reset</button>
                </div>
                ${ketua.length === 0 ? '<div class="text-center py-10 text-gray-400">Tiada Ketua Keluarga dijumpai.</div>' : `
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr>
                                <th class="w-8 text-center">No.</th>
                                <th>Nama Penuh & No. KP</th>
                                <th>No. Telefon</th>
                                <th>DUN / PDM</th>
                                <th>Ahli Keluarga Terikat</th>
                                <th>Tindakan</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${ketua.map((p, idx) => `
                            <tr>
                                <td class="text-xs text-gray-400 text-center w-8">${(ketuaKeluargaState.page - 1) * 50 + idx + 1}</td>
                                <td>
                                    <div class="font-medium">${p.nama_penuh || '-'}</div>
                                    <div class="text-xs text-gray-400 font-mono">${p.no_kp || '-'}</div>
                                </td>
                                <td>
                                    ${p.no_telefon ? `<a href="https://wa.me/${String(p.no_telefon).replace(/[^0-9]/g, '')}" target="_blank" class="text-green-600 hover:text-green-800 flex items-center gap-1">
                                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                        ${sanitizePhone(p.no_telefon)}
                                    </a>` : '<span class="text-gray-400">-</span>'}
                                </td>
                                <td class="text-sm">${renderDunPdmColumn(p)}</td>
                                <td><span class="badge badge-sah">${p.jumlah_pengundi || 0}</span></td>
                                <td>
                                    <div class="flex gap-1">
                                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-2 py-1 text-xs border-0 mr-1">Edit</button><button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-2 py-1 text-xs border-0">Padam</button>' : '<button onclick="editKetuaKeluarga(' + p.id + ')" class="btn btn-primary text-xs py-1 px-2">Edit</button><button onclick="padamKetuaKeluarga(' + p.id + ')" class="btn btn-outline text-xs py-1 px-2 border-red-300 text-red-600 hover:bg-red-50">Padam</button>'}
                                    </div>
                                </td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="flex items-center justify-between mt-4">
                    <div class="pagination">
                        ${Array.from({length: Math.min(totalPages, 10)}, (_, i) => i + 1).map(p => `
                            <button onclick="ketuaKeluargaState.page=${p};renderKetuaKeluarga()" class="${ketuaKeluargaState.page === p ? 'active' : ''}">${p}</button>
                        `).join('')}
                        ${totalPages > 10 ? `<span class="text-sm text-gray-400">... ${totalPages}</span>` : ''}
                    </div>
                    <span class="text-sm text-gray-500">Halaman ${ketuaKeluargaState.page}/${totalPages}</span>
                </div>`}
            </div>

            <div id="modalKetuaKeluarga" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 hidden" onclick="if(event.target===this)this.classList.add('hidden')">
                <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
                    <div class="flex items-center justify-between p-4 border-b">
                        <h3 id="modalKetuaTitle" class="text-lg font-semibold text-gray-800">Daftar Ketua Keluarga Baru</h3>
                        <button onclick="document.getElementById('modalKetuaKeluarga').classList.add('hidden')" class="text-gray-400 hover:text-red-500 text-2xl leading-none">&times;</button>
                    </div>
                    <div class="p-4 space-y-3">
                        <input type="hidden" id="ketuaEditId" value="">
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">Nama Penuh <span class="text-red-500">*</span></label>
                            <input type="text" id="ketuaNama" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="Nama penuh ketua keluarga">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">No. Kad Pengenalan <span class="text-red-500">*</span></label>
                            <input type="text" id="ketuaNoKp" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="000101-01-0001">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">No. Telefon <span class="text-red-500">*</span></label>
                            <input type="text" id="ketuaNoTelefon" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="012-3456789">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">DUN / PDM (Rujukan Optional)</label>
                            <div class="flex gap-2">
                                <select id="ketuaDun" onchange="ketuaDunChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                                    <option value="">- Pilih DUN (Optional) -</option>
                                </select>
                                <input type="text" id="ketuaDm" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Atau taip PDM">
                            </div>
                            <p class="text-xs text-gray-400 mt-1">Pilih DUN atau taip nama PDM. Ini hanya tag rujukan - tidak mengunci kawasan.</p>
                        </div>
                    </div>
                    <div class="flex gap-2 p-4 border-t">
                        <button onclick="document.getElementById('modalKetuaKeluarga').classList.add('hidden')" class="btn btn-outline flex-1">Batal</button>
                        <button onclick="simpanKetuaKeluarga()" class="btn btn-primary flex-1">Simpan</button>
                    </div>
                </div>
            </div>
        `;

        try {
            const dunList = await api('/api/dun');
            const dunSelect = document.getElementById('ketuaDun');
            if (dunSelect) {
                dunList.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.kod;
                    opt.textContent = `${d.nama} (${d.jumlah_pengundi || 0})`;
                    dunSelect.appendChild(opt);
                });
            }
        } catch (e) {}
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

function ketuaDunChanged() {
    const dunKod = document.getElementById('ketuaDun').value;
    const dmInput = document.getElementById('ketuaDm');
    if (dunKod && dmInput) {
        dmInput.placeholder = `Atau taip PDM untuk ${dunKod}`;
    } else if (dmInput) {
        dmInput.placeholder = 'Atau taip PDM';
    }
}

function showTambahKetuaKeluarga() {
    document.getElementById('modalKetuaTitle').textContent = 'Daftar Ketua Keluarga Baru';
    document.getElementById('ketuaEditId').value = '';
    document.getElementById('ketuaNama').value = '';
    document.getElementById('ketuaNoKp').value = '';
    document.getElementById('ketuaNoTelefon').value = '';
    document.getElementById('ketuaDun').value = '';
    document.getElementById('ketuaDm').value = '';
    document.getElementById('modalKetuaKeluarga').classList.remove('hidden');
}

async function editKetuaKeluarga(id) {
    try {
        const ketua = await api(`/api/ketua-keluarga/${id}`);
        document.getElementById('modalKetuaTitle').textContent = 'Edit Ketua Keluarga';
        document.getElementById('ketuaEditId').value = id;
        document.getElementById('ketuaNama').value = ketua.nama_penuh || '';
        document.getElementById('ketuaNoKp').value = ketua.no_kp || '';
        document.getElementById('ketuaNoTelefon').value = ketua.no_telefon || '';
        document.getElementById('ketuaDun').value = ketua.dun_kod || '';
        document.getElementById('ketuaDm').value = ketua.dm || '';
        document.getElementById('modalKetuaKeluarga').classList.remove('hidden');
    } catch (err) {
        showToast('Gagal memuat data ketua keluarga: ' + err.message, 'error');
    }
}

async function simpanKetuaKeluarga() {
    const editId = document.getElementById('ketuaEditId').value;
    const nama_penuh = document.getElementById('ketuaNama').value.trim();
    const no_kp = document.getElementById('ketuaNoKp').value.trim();
    const no_telefon = document.getElementById('ketuaNoTelefon').value.trim();
    const dun = document.getElementById('ketuaDun').value;
    const dm = document.getElementById('ketuaDm').value.trim();

    if (!nama_penuh) { showToast('Nama Penuh wajib diisi', 'error'); return; }
    if (!no_kp) { showToast('No Kad Pengenalan wajib diisi', 'error'); return; }
    if (!no_telefon) { showToast('No Telefon wajib diisi', 'error'); return; }

    const data = { nama_penuh, no_kp, no_telefon };
    if (dm) data.dm = dm;
    else if (dun) data.dm = dun;

    try {
        if (editId) {
            await api(`/api/ketua-keluarga/${editId}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('Ketua Keluarga berjaya dikemaskini', 'success');
        } else {
            await api('/api/ketua-keluarga', { method: 'POST', body: JSON.stringify(data) });
            showToast('Ketua Keluarga berjaya didaftarkan', 'success');
        }
        document.getElementById('modalKetuaKeluarga').classList.add('hidden');
        renderKetuaKeluarga();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

async function padamKetuaKeluarga(id) {
    if (!confirm('Anda pasti mahu memadamkan Ketua Keluarga ini? Pengundi yang terikat akan dinyahpaut. Tindakan ini tidak boleh dikembalikan.')) return;
    try {
        await api(`/api/ketua-keluarga/${id}`, { method: 'DELETE' });
        showToast('Ketua Keluarga berjaya dipadamkan', 'success');
        renderKetuaKeluarga();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

// ========= PEGAWAI PENYELARAS MANAGEMENT (Admin only) =========
let pegawaiPenyelarasState = { page: 1, search: '' };

async function renderPegawaiPenyelaras() {
    const content = document.getElementById('contentArea');
    content.innerHTML = '<div class="flex items-center justify-center py-20"><div class="loading-spinner"></div><span class="ml-3 text-gray-500">Memuatkan data pegawai penyelaras...</span></div>';
    try {
        const [stats, result] = await Promise.all([
            api('/api/pegawai-penyelaras/stats'),
            api(`/api/pegawai-penyelaras/list?page=${pegawaiPenyelarasState.page}&search=${encodeURIComponent(pegawaiPenyelarasState.search)}`)
        ]);
        const pegawai = result.data || [];
        const total = result.total || 0;
        const totalPages = result.total_pages || 1;

        content.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="card bg-gradient-to-br from-blue-50 to-blue-100 border-l-4 border-blue-500">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 bg-blue-500 rounded-xl flex items-center justify-center text-white text-xl font-bold">${stats.total_pegawai || 0}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Jumlah Pegawai</p><p class="text-lg font-bold text-gray-800">${stats.total_pegawai || 0}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-green-50 to-green-100 border-l-4 border-green-500">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center text-white text-xl font-bold">${stats.dun_coverage || '0/0'}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Liputan DUN</p><p class="text-lg font-bold text-gray-800">${stats.dun_coverage || '0/0'}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-amber-50 to-amber-100 border-l-4 border-amber-500">
                    <div class="flex items-center gap-3">
                        <div class="w-auto min-w-[3rem] h-12 px-2 bg-amber-500 rounded-xl flex items-center justify-center text-white text-base font-bold whitespace-nowrap">${stats.pdm_coverage || '0/0'}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Liputan PDM</p><p class="text-lg font-bold text-gray-800">${stats.pdm_coverage || '0/0'}</p></div>
                    </div>
                </div>
                <div class="card bg-gradient-to-br from-purple-50 to-purple-100 border-l-4 border-purple-500">
                    <div class="flex items-center gap-3">
                        <div class="flex-shrink-0 w-14 h-14 bg-purple-500 rounded-xl flex items-center justify-center text-white text-sm md:text-base font-bold px-2">${(stats.pengundi_terikat || 0).toLocaleString()}</div>
                        <div><p class="text-xs text-gray-500 uppercase font-semibold">Pengundi Terikat</p><p class="text-lg font-bold text-gray-800">${(stats.pengundi_terikat || 0).toLocaleString()}</p></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
                    <h3 class="font-semibold text-gray-800">Senarai Pegawai Penyelaras</h3>
                    <div class="flex items-center gap-2">
                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded-lg px-3 py-2 text-sm border-0">+ Tambah Pegawai Baru</button>' : '<button onclick="showTambahPegawaiPenyelaras()" class="btn btn-primary text-sm">+ Tambah Pegawai Baru</button>'}
                        <span class="text-sm text-gray-500">${total.toLocaleString()} pegawai</span>
                    </div>
                </div>
                <div class="flex items-center gap-2 mb-4">
                    <div class="relative flex-1 min-w-[200px]">
                        <input type="text" id="pegawaiSearch" placeholder="Cari nama atau No KP..." value="${pegawaiPenyelarasState.search}" onkeyup="if(event.key==='Enter'){pegawaiPenyelarasState.search=this.value;pegawaiPenyelarasState.page=1;renderPegawaiPenyelaras();}" class="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-lg">
                        <svg class="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                    </div>
                    <button onclick="pegawaiPenyelarasState.search=document.getElementById('pegawaiSearch').value;pegawaiPenyelarasState.page=1;renderPegawaiPenyelaras();" class="btn btn-primary text-sm py-2 px-3">Cari</button>
                    <button onclick="document.getElementById('pegawaiSearch').value='';pegawaiPenyelarasState.search='';pegawaiPenyelarasState.page=1;renderPegawaiPenyelaras();" class="btn btn-outline text-sm py-2 px-3">Reset</button>
                </div>
                ${pegawai.length === 0 ? '<div class="text-center py-10 text-gray-400">Tiada pegawai penyelaras dijumpai.</div>' : `
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr>
                                <th class="w-8 text-center">No.</th>
                                <th>Nama Penuh & No. KP</th>
                                <th>No. Telefon</th>
                                <th>DUN / PDM</th>
                                <th>Pengundi Terikat</th>
                                <th>Tindakan</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pegawai.map((p, idx) => `
                            <tr>
                                <td class="text-xs text-gray-400 text-center w-8">${(pegawaiPenyelarasState.page - 1) * 50 + idx + 1}</td>
                                <td>
                                    <div class="font-medium">${p.nama_penuh || '-'}</div>
                                    <div class="text-xs text-gray-400 font-mono">${p.no_kp || '-'}</div>
                                </td>
                                <td>
                                    ${p.no_telefon ? `<a href="https://wa.me/${String(p.no_telefon).replace(/[^0-9]/g, '')}" target="_blank" class="text-green-600 hover:text-green-800 flex items-center gap-1">
                                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                                        ${sanitizePhone(p.no_telefon)}
                                    </a>` : '<span class="text-gray-400">-</span>'}
                                </td>
                                <td class="text-sm">${renderDunPdmColumn(p)}</td>
                                <td><span class="badge badge-sah">${p.jumlah_pengundi || 0}</span></td>
                                <td>
                                    <div class="flex gap-1">
                                        ${checkPemerhati() ? '<button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-2 py-1 text-xs border-0 mr-1">Edit</button><button disabled class="bg-gray-300 text-gray-500 opacity-60 cursor-not-allowed rounded px-2 py-1 text-xs border-0">Padam</button>' : '<button onclick="editPegawaiPenyelaras(' + p.id + ')" class="btn btn-primary text-xs py-1 px-2">Edit</button><button onclick="padamPegawaiPenyelaras(' + p.id + ')" class="btn btn-outline text-xs py-1 px-2 border-red-300 text-red-600 hover:bg-red-50">Padam</button>'}
                                    </div>
                                </td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="flex items-center justify-between mt-4">
                    <div class="pagination">
                        ${Array.from({length: Math.min(totalPages, 10)}, (_, i) => i + 1).map(p => `
                            <button onclick="pegawaiPenyelarasState.page=${p};renderPegawaiPenyelaras()" class="${pegawaiPenyelarasState.page === p ? 'active' : ''}">${p}</button>
                        `).join('')}
                        ${totalPages > 10 ? `<span class="text-sm text-gray-400">... ${totalPages}</span>` : ''}
                    </div>
                    <span class="text-sm text-gray-500">Halaman ${pegawaiPenyelarasState.page}/${totalPages}</span>
                </div>`}
            </div>

            <div id="modalPegawaiPenyelaras" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 hidden" onclick="if(event.target===this)this.classList.add('hidden')">
                <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
                    <div class="flex items-center justify-between p-4 border-b">
                        <h3 id="modalPegawaiTitle" class="text-lg font-semibold text-gray-800">Daftar Pegawai Penyelaras Baru</h3>
                        <button onclick="document.getElementById('modalPegawaiPenyelaras').classList.add('hidden')" class="text-gray-400 hover:text-red-500 text-2xl leading-none">&times;</button>
                    </div>
                    <div class="p-4 space-y-3">
                        <input type="hidden" id="pegawaiEditId" value="">
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">Nama Penuh <span class="text-red-500">*</span></label>
                            <input type="text" id="pegawaiNama" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="Nama penuh pegawai">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">No. Kad Pengenalan <span class="text-red-500">*</span></label>
                            <input type="text" id="pegawaiNoKp" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="000101-01-0001">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">No. Telefon <span class="text-red-500">*</span></label>
                            <input type="text" id="pegawaiNoTelefon" class="w-full px-3 py-2 text-sm border rounded-lg" placeholder="012-3456789">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-600 mb-1">DUN / PDM (Rujukan Optional)</label>
                            <div class="flex gap-2">
                                <select id="pegawaiDun" onchange="pegawaiDunChanged()" class="flex-1 px-3 py-2 text-sm border rounded-lg">
                                    <option value="">- Pilih DUN (Optional) -</option>
                                </select>
                                <input type="text" id="pegawaiDm" class="flex-1 px-3 py-2 text-sm border rounded-lg" placeholder="Atau taip PDM">
                            </div>
                            <p class="text-xs text-gray-400 mt-1">Pilih DUN atau taip nama PDM. Ini hanya tag rujukan - tidak mengunci kawasan.</p>
                        </div>
                    </div>
                    <div class="flex gap-2 p-4 border-t">
                        <button onclick="document.getElementById('modalPegawaiPenyelaras').classList.add('hidden')" class="btn btn-outline flex-1">Batal</button>
                        <button onclick="simpanPegawaiPenyelaras()" class="btn btn-primary flex-1">Simpan</button>
                    </div>
                </div>
            </div>
        `;

        try {
            const dunList = await api('/api/dun');
            const dunSelect = document.getElementById('pegawaiDun');
            if (dunSelect) {
                dunList.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.kod;
                    opt.textContent = `${d.nama} (${d.jumlah_pengundi || 0})`;
                    dunSelect.appendChild(opt);
                });
            }
        } catch (e) {}
    } catch (err) {
        content.innerHTML = `<div class="card text-center py-10"><p class="text-red-500">${err.message}</p></div>`;
    }
}

function pegawaiDunChanged() {
    const dunKod = document.getElementById('pegawaiDun').value;
    const dmInput = document.getElementById('pegawaiDm');
    if (dunKod && dmInput) {
        dmInput.placeholder = `Atau taip PDM untuk ${dunKod}`;
    } else if (dmInput) {
        dmInput.placeholder = 'Atau taip PDM';
    }
}

function showTambahPegawaiPenyelaras() {
    document.getElementById('modalPegawaiTitle').textContent = 'Daftar Pegawai Penyelaras Baru';
    document.getElementById('pegawaiEditId').value = '';
    document.getElementById('pegawaiNama').value = '';
    document.getElementById('pegawaiNoKp').value = '';
    document.getElementById('pegawaiNoTelefon').value = '';
    document.getElementById('pegawaiDun').value = '';
    document.getElementById('pegawaiDm').value = '';
    document.getElementById('modalPegawaiPenyelaras').classList.remove('hidden');
}

async function editPegawaiPenyelaras(id) {
    try {
        const pegawai = await api(`/api/pegawai-penyelaras/${id}`);
        document.getElementById('modalPegawaiTitle').textContent = 'Edit Pegawai Penyelaras';
        document.getElementById('pegawaiEditId').value = id;
        document.getElementById('pegawaiNama').value = pegawai.nama_penuh || '';
        document.getElementById('pegawaiNoKp').value = pegawai.no_kp || '';
        document.getElementById('pegawaiNoTelefon').value = pegawai.no_telefon || '';
        document.getElementById('pegawaiDun').value = pegawai.dun_kod || '';
        document.getElementById('pegawaiDm').value = pegawai.dm || '';
        document.getElementById('modalPegawaiPenyelaras').classList.remove('hidden');
    } catch (err) {
        showToast('Gagal memuat data pegawai: ' + err.message, 'error');
    }
}

async function simpanPegawaiPenyelaras() {
    const editId = document.getElementById('pegawaiEditId').value;
    const nama_penuh = document.getElementById('pegawaiNama').value.trim();
    const no_kp = document.getElementById('pegawaiNoKp').value.trim();
    const no_telefon = document.getElementById('pegawaiNoTelefon').value.trim();
    const dun = document.getElementById('pegawaiDun').value;
    const dm = document.getElementById('pegawaiDm').value.trim();

    if (!nama_penuh) { showToast('Nama Penuh wajib diisi', 'error'); return; }
    if (!no_kp) { showToast('No Kad Pengenalan wajib diisi', 'error'); return; }
    if (!no_telefon) { showToast('No Telefon wajib diisi', 'error'); return; }

    const data = { nama_penuh, no_kp, no_telefon };
    if (dm) data.dm = dm;
    else if (dun) data.dm = dun;

    try {
        if (editId) {
            await api(`/api/pegawai-penyelaras/${editId}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('Pegawai Penyelaras berjaya dikemaskini', 'success');
        } else {
            await api('/api/pegawai-penyelaras', { method: 'POST', body: JSON.stringify(data) });
            showToast('Pegawai Penyelaras berjaya didaftarkan', 'success');
        }
        document.getElementById('modalPegawaiPenyelaras').classList.add('hidden');
        renderPegawaiPenyelaras();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

async function padamPegawaiPenyelaras(id) {
    if (!confirm('Anda pasti mahu memadamkan Pegawai Penyelaras ini? Tindakan ini tidak boleh dikembalikan.')) return;
    try {
        await api(`/api/pegawai-penyelaras/${id}`, { method: 'DELETE' });
        showToast('Pegawai Penyelaras berjaya dipadamkan', 'success');
        renderPegawaiPenyelaras();
    } catch (err) {
        showToast('Ralat: ' + err.message, 'error');
    }
}

// ========= COMING SOON PAGE =========
function renderComingSoon(page) {
    const titles = {
        'kpi': 'Petunjuk Prestasi Utama (PPU)',
        'berita': 'Berita & Amanat',
        'kalendar': 'Kalendar Aktiviti',
        'aduan': 'Aduan Pengguna',
        'cadangan': 'Cadangan Pengguna',
        'survey-view': 'Borang Soal Selidik'
    };
    const icons = {
        'kpi': '<svg class="w-16 h-16 mx-auto text-amber-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>',
        'berita': '<svg class="w-16 h-16 mx-auto text-amber-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/></svg>',
        'kalendar': '<svg class="w-16 h-16 mx-auto text-amber-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>',
        'default': '<svg class="w-16 h-16 mx-auto text-amber-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>'
    };
    const content = document.getElementById('contentArea');
    content.innerHTML = `
        <div class="max-w-2xl mx-auto">
            <div class="card text-center py-12">
                ${icons[page] || icons['default']}
                <h2 class="text-xl font-bold text-gray-800 mb-2">${titles[page] || 'Ciri Akan Datang'}</h2>
                <div class="inline-block bg-amber-100 text-amber-800 text-sm font-semibold px-3 py-1 rounded-full mb-4">Akan Datang</div>
                <p class="text-gray-500 max-w-md mx-auto">Ciri ini sedang dalam pembangunan dan akan dilancarkan dalam fasa akan datang. Sila nantikan!</p>
                <button onclick="navigate('dashboard')" class="btn btn-primary mt-6">← Kembali ke Papan Pemuka</button>
            </div>
        </div>`;
}

// ============================================================
// GLOBAL REPORTING FUNCTIONS (Cetak / Excel / PDF)
// ============================================================
function globalPrint() {
    window.print();
}

function globalDownloadExcel() {
    const container = document.getElementById('contentArea');
    if (!container) return;
    const table = container.querySelector('table');
    if (!table) { showToast('Tiada jadual untuk dieksport', 'error'); return; }

    let csv = '\uFEFF';
    const thead = table.querySelector('thead');
    if (thead) {
        const headerCells = thead.querySelectorAll('th');
        const headers = [];
        headerCells.forEach(th => {
            headers.push('"' + (th.textContent || '').trim().replace(/"/g, '""') + '"');
        });
        csv += headers.join(',') + '\n';
    }

    const tbody = table.querySelector('tbody');
    if (tbody) {
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(tr => {
            const cells = tr.querySelectorAll('td');
            const values = [];
            cells.forEach(td => {
                values.push('"' + (td.textContent || '').trim().replace(/"/g, '""') + '"');
            });
            csv += values.join(',') + '\n';
        });
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Eksport_' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Fail CSV berjaya dimuat turun!');
}

function globalDownloadPDF() {
    showToast('⏳ Menyediakan PDF...', 'success');
    setTimeout(() => {
        const container = document.getElementById('contentArea');
        if (!container) return;
        const table = container.querySelector('table');
        if (!table) { showToast('Tiada jadual untuk dieksport', 'error'); return; }
        const clone = table.cloneNode(true);
        const pageTitle = document.getElementById('pageTitle')?.textContent || 'Laporan';
        const pdfHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${pageTitle}</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; }
                h1 { font-size: 18pt; text-align: center; margin-bottom: 5px; }
                .subtitle { text-align: center; color: #666; font-size: 10pt; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; font-size: 9pt; }
                th { background: #f8fafc; padding: 8px 6px; text-align: left; border-bottom: 2px solid #e2e8f0; }
                td { padding: 6px; border-bottom: 1px solid #f1f5f9; }
                tfoot td { font-weight: bold; background: #f3f4f6; border-top: 2px solid #d1d5db; }
                @media print { @page { size: A4 landscape; margin: 10mm; } }
    </style></head><body>
            <h1>${pageTitle}</h1>
            <p class="subtitle">Dikeluarkan: ${new Date().toLocaleDateString('ms-MY')}</p>
            ${clone.outerHTML}
    </body></html>`;
        const w = window.open('', '_blank', 'width=1100,height=700');
        if (w) {
            w.document.write(pdfHtml);
            w.document.close();
            setTimeout(() => { w.print(); }, 500);
        }
    }, 0);
}

// ============================================================
// MAIN APP RENDER
// ============================================================
function renderApp() {
    if (!requiresAuth()) { renderLoginPage(); return; }
    renderSidebar();
    if (window.innerWidth < 768) document.getElementById('sidebar').classList.add('closed');
    else document.getElementById('sidebar').classList.remove('closed');
    document.getElementById('userInfo').innerHTML = `
        <button onclick="globalPrint()" class="text-gray-500 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="Cetak">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
            </svg>
        </button>
        <button onclick="globalDownloadExcel()" class="text-gray-500 hover:text-green-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="Muat Turun Excel">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
        </button>
        <button onclick="globalDownloadPDF()" class="text-gray-500 hover:text-red-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="Muat Turun PDF">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
            </svg>
        </button>
        <span class="text-gray-300 text-lg mx-0.5">|</span>
        <span class="hidden md:block text-sm text-gray-600">${state.user?.nama_penuh}</span><span class="${(() => {
            const r = state.user?.peranan || '';
            if (r === 'Developer') return 'badge bh-badge-dev';
            if (r.startsWith('Admin')) return 'badge bh-badge-admin-system';
            if (r === 'Petugas 1 (System Preset)') return 'badge bh-badge-petugas1-system';
            if (r === 'Petugas 1 (Pegawai Penyelaras)') return 'badge bh-badge-petugas1-pp';
            if (r === 'Petugas 2 (Ketua Keluarga)') return 'badge bh-badge-petugas2';
            if (r === 'Pemerhati') return 'badge bh-badge-pemerhati';
            return 'badge badge-tiada';
        })()}">${state.user?.peranan}</span>
        <button onclick="handleLogout()" class="btn btn-danger text-sm flex items-center gap-1.5 px-3 py-1.5"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg> Log Keluar</button>`;
    navigate(state.currentPage);
    if (state.user?.peranan?.startsWith('Admin')) updateApprovalBadge();
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('closed'); sidebar.classList.toggle('open');
    if (window.innerWidth < 768) {
        if (sidebar.classList.contains('open')) {
            document.body.classList.add('no-scroll');
            if (overlay) overlay.classList.add('active');
        } else {
            document.body.classList.remove('no-scroll');
            if (overlay) overlay.classList.remove('active');
        }
    }
}

document.getElementById('menuToggle')?.addEventListener('click', toggleSidebar);
try {
    renderApp();
} catch(e) {
    console.error('[CRITICAL] renderApp() crashed:', e);
    document.getElementById('sidebar')?.classList.add('hidden');
    document.getElementById('pageTitle').textContent = 'Log Masuk';
    document.getElementById('userInfo').innerHTML = '';
    document.getElementById('contentArea').innerHTML = `<div class="flex items-center justify-center min-h-70vh">
        <div class="card w-full max-w-md p-8 text-center">
            <div class="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center mb-4">
                <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
            </div>
            <h2 class="text-lg font-bold text-gray-800 mb-2">Ralat Aplikasi</h2>
            <p class="text-sm text-gray-500 mb-4">Aplikasi mengalami masalah teknikal. Sila muat semula halaman.</p>
            <button onclick="location.reload()" class="btn btn-primary">Muat Semula</button>
        </div>
    </div>`;
}
setInterval(() => { if (state.token && state.user?.peranan?.startsWith('Admin')) updateApprovalBadge(); }, 30000);
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (window.innerWidth < 768) {
        // Close when clicking overlay
        if (e.target === overlay) { toggleSidebar(); return; }
        // Close when clicking outside sidebar & menuToggle
        if (!sidebar.contains(e.target) && !e.target.closest('#menuToggle')) {
            sidebar.classList.remove('open'); sidebar.classList.add('closed');
            if (overlay) overlay.classList.remove('active');
            document.body.classList.remove('no-scroll');
        }
    }
});

// 🛡️ OVERRIDE: app.js telah selesai dimuat — override navigate() dengan RBAC guards + PHASE 3 cache
(function() {
    window.navigate = function(page) {
        if (!requiresAuth()) { renderLoginPage(); return; }
        
        // 🛡️ ACL ROUTE GUARD: Pemerhati hanya dihalang dari audit & users
        if (checkPemerhati()) {
            const blockedPages = ['audit', 'users'];
            if (blockedPages.includes(page)) {
                showToast('Akses Tidak Dibenarkan', 'error');
                page = 'dashboard';
                state.currentPage = page;
                localStorage.setItem('currentPage', page);
            }
        }
        
        // 🛡️ ACL ROUTE GUARD: Petugas 1 hanya boleh akses dashboard, pengundi, ketua-keluarga
        if (checkPetugas1()) {
            const allowedPages = ['dashboard', 'pengundi', 'ketua-keluarga'];
            if (!allowedPages.includes(page)) {
                showToast('Akses Tidak Dibenarkan', 'error');
                page = 'dashboard';
                state.currentPage = page;
                localStorage.setItem('currentPage', page);
            }
        }
        
        // 🛡️ ACL ROUTE GUARD: Petugas 2 hanya boleh akses dashboard & pengundi
        if (checkPetugas2()) {
            const allowedPages = ['dashboard', 'pengundi'];
            if (!allowedPages.includes(page)) {
                showToast('Akses Tidak Dibenarkan', 'error');
                page = 'dashboard';
                state.currentPage = page;
                localStorage.setItem('currentPage', page);
            }
        }
        
        const prevPage = state.currentPage;
        state.currentPage = page;
        localStorage.setItem('currentPage', page);
        
        // 🚀 PHASE 3 PERF: Only rebuild sidebar if role changed or first time
        const currentRole = state.user?.peranan || '';
        if (state.lastRenderedRole !== currentRole || !document.querySelector('.sidebar-item')) {
            renderSidebar();
            state.lastRenderedRole = currentRole;
        } else {
            updateSidebarActive(page);
            document.getElementById('sidebar').classList.remove('hidden');
        }
        
        document.getElementById('pageTitle').textContent = 
            page==='dashboard'?'Papan Pemuka':page==='pengundi'?'Senarai Pengundi':
            page==='approval'?'Kelulusan Data':page==='audit'?'Log Aktiviti':
            page==='users'?'Pengurusan Pengguna':page==='import'?'Import Data Excel':
            page==='survey'?'Senarai Soal Selidik':page==='survey-create'?'Cipta Soal Selidik':
            page==='survey-view'?'Borang Soal Selidik':
            page==='pegawai-penyelaras'?'Pengurusan Pegawai Penyelaras':
            page==='ketua-keluarga'?'Pengurusan Ketua Keluarga':
            page==='kpi'?'Petunjuk Prestasi Utama (PPU)':
            'Papan Pemuka';
        document.getElementById('sidebar').classList.remove('open');
        const overlay = document.getElementById('sidebarOverlay');
        if (window.innerWidth < 768) {
            document.getElementById('sidebar').classList.add('closed');
            if (overlay) overlay.classList.remove('active');
            document.body.classList.remove('no-scroll');
        } else {
            document.getElementById('sidebar').classList.remove('closed');
        }
        
        // 🚀 PHASE 3 PERF: Restore from cache if valid (skip for dashboard which re-fetches)
        if (state.pageCacheValid[page] && state.pageCache[page]) {
            document.getElementById('contentArea').innerHTML = state.pageCache[page];
            return;
        }
        
        if (page==='dashboard') renderDashboard();
        else if (page==='pengundi') renderPengundi();
        else if (page==='approval') { if (!checkAdmin()) { navigate('dashboard'); return; } renderApprovalQueue(); }
        else if (page==='audit') renderAuditLogs();
        else if (page==='users') renderUserManagement();
        else if (page==='import') renderImportData();
        else if (page==='survey') renderSurveyList();
        else if (page==='survey-create') renderCreateSurvey();
        else if (page==='survey-view') renderSurveyView();
        else if (page==='kpi') renderKpi();
        else if (page==='pegawai-penyelaras') renderPegawaiPenyelaras();
        else if (page==='ketua-keluarga') renderKetuaKeluarga();
        else renderComingSoon(page);
    };
    if (state.currentPage && requiresAuth()) {
        window.navigate(state.currentPage);
    }
})();
