// ============================================================
// 📊 PPU Module: Petunjuk Prestasi Utama (Pegawai Penyelaras)
// ============================================================
// Module berasingan daripada app.js — tidak mengganggu dashboard
// Fungsi global renderKpi() boleh dipanggil dari app.js navigate()
// ============================================================

// Module-level state untuk sort & filter (client-side sahaja)
let kpiData = [];          // Simpan data penuh dari API
let kpiSortDir = 'desc';   // 'desc' atau 'asc' untuk Bil. Rekrut Putih
let kpiFilterDun = '';     // '' = semua, atau 'N12 Sulaman' dsb

async function renderKpi() {
    const container = document.getElementById('contentArea');
    if (!container) return;

    // --- Render HTML shell + loading state ---
    container.innerHTML = `
        <div class="max-w-6xl mx-auto">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
                    <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                    </svg>
                </div>
                <div>
                    <h1 class="text-2xl font-bold text-gray-800">Petunjuk Prestasi Utama (PPU)</h1>
                    <p class="text-sm text-gray-500">Prestasi Pegawai Penyelaras — Profil Mengundi & Rekrut K.K / Putih</p>
                </div>
            </div>

            <div id="kpiTableContainer" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div class="flex items-center justify-center py-12">
                    <svg class="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    <span class="ml-3 text-gray-500">Memuat data PPU...</span>
                </div>
            </div>
        </div>
    `;

    try {
        // --- Fetch data from backend ---
        const res = await api('/api/p_pegawai-penyelaras');
        kpiData = res.data || [];

        if (!kpiData || kpiData.length === 0) {
            document.getElementById('kpiTableContainer').innerHTML = `
                <div class="flex flex-col items-center justify-center py-12 text-gray-400">
                    <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
                    </svg>
                    <p class="text-lg font-medium">Tiada data Pegawai Penyelaras</p>
                    <p class="text-sm">Belum ada pengundi yang ditetapkan sebagai Pegawai Penyelaras.</p>
                </div>
            `;
            return;
        }

        // --- Default sort: Bil. Rekrut Putih descending ---
        kpiSortDir = 'desc';
        kpiFilterDun = '';
        renderKpiTable();

    } catch (err) {
        console.error('❌ PPU renderKpi() error:', err);
        document.getElementById('kpiTableContainer').innerHTML = `
            <div class="flex flex-col items-center justify-center py-12 text-red-400">
                <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                </svg>
                <p class="text-lg font-medium">Ralat memuat data PPU</p>
                <p class="text-sm text-gray-400 mt-1">${err.message || 'Sila cuba sebentar lagi.'}</p>
            </div>
        `;
    }
}

// ============================================================
// RENDER TABLE (dipanggil setiap kali sort/filter berubah)
// ============================================================
function renderKpiTable() {
    let data = [...kpiData];

    // --- Client-side Filter by DUN ---
    if (kpiFilterDun) {
        data = data.filter(row => row.dun === kpiFilterDun);
    }

    // --- Client-side Sort by Bil. Rekrut Putih ---
    data.sort((a, b) => {
        const valA = a.rekrut_putih || 0;
        const valB = b.rekrut_putih || 0;
        return kpiSortDir === 'desc' ? valB - valA : valA - valB;
    });

    // --- Calculate totals ---
    const totalKk = data.reduce((sum, row) => sum + (row.rekrut_kk || 0), 0);
    const totalPutih = data.reduce((sum, row) => sum + (row.rekrut_putih || 0), 0);

    // --- Arrow indicator untuk header ---
    const arrowDown = ' ▼';
    const arrowUp = ' ▲';
    const sortArrow = kpiSortDir === 'desc' ? arrowDown : arrowUp;

    // --- DUN dropdown options ---
    const dunOptions = [
        { value: '', label: 'Semua DUN' },
        { value: 'N12 Sulaman', label: 'N12 Sulaman' },
        { value: 'N13 Pantai Dalit', label: 'N13 Pantai Dalit' },
        { value: 'N14 Tamparuli', label: 'N14 Tamparuli' },
        { value: 'N15 Kiulu', label: 'N15 Kiulu' }
    ];

    const dunOptionsHtml = dunOptions.map(opt =>
        `<option value="${opt.value}" ${kpiFilterDun === opt.value ? 'selected' : ''}>${opt.label}</option>`
    ).join('');

    // --- Build table rows ---
    let rowsHtml = '';
    data.forEach((row, index) => {
        const parlimen = row.parlimen || '-';
        const dun = row.dun || '-';
        const pdm = row.pdm || '-';

        // Highlight baris jika rekrut_putih > 0 (prestasi aktif)
        const rowHighlight = (row.rekrut_putih || 0) > 0
            ? 'bg-green-50'
            : '';

        rowsHtml += `
            <tr class="border-b border-gray-100 hover:bg-blue-50 transition-colors ${rowHighlight}">
                <td class="px-4 py-3 text-sm text-gray-700">${index + 1}</td>
                <td class="px-4 py-3 text-sm font-medium text-gray-900">${row.nama || '-'}</td>
                <td class="px-4 py-3 text-sm text-gray-700">${parlimen}</td>
                <td class="px-4 py-3 text-sm text-gray-700">${dun}</td>
                <td class="px-4 py-3 text-sm text-gray-700">${pdm}</td>
                <td class="px-4 py-3 text-sm text-gray-700 text-right font-mono">${(row.rekrut_kk || 0).toLocaleString()}</td>
                <td class="px-4 py-3 text-sm text-gray-700 text-right font-mono font-semibold">${(row.rekrut_putih || 0).toLocaleString()}</td>
            </tr>
        `;
    });

    const tableHtml = `
        <!-- Toolbar: Title + Dropdown + Reset -->
        <div class="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 class="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                PPU PEGAWAI PENYELARAS
            </h2>
            <div class="flex items-center gap-2 flex-wrap">
                <!-- DUN Dropdown Filter -->
                <select id="kpiDunFilter" onchange="onKpiDunChange(this.value)" class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 cursor-pointer">
                    ${dunOptionsHtml}
                </select>
                <!-- Reset Button -->
                <button onclick="onKpiReset()" class="btn btn-outline text-xs py-1.5 px-3 border-gray-300 text-gray-600 hover:bg-gray-100 flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Tetapkan Semula
                </button>
                <!-- Badge kiraan -->
                <span class="text-xs text-gray-400 bg-gray-50 px-3 py-1 rounded-full">${data.length} Pegawai Penyelaras</span>
            </div>
        </div>

        <!-- Wrapper untuk scroll jadual -->
        <div class="overflow-x-auto">
            <table class="w-full border-collapse">
                <!-- Header -->
                <thead>
                    <tr class="bg-gray-50 border-b-2 border-gray-200">
                        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-12">#</th>
                        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Nama Pegawai Penyelaras</th>
                        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Parlimen Mengundi</th>
                        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">DUN Mengundi</th>
                        <th class="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">PDM Mengundi</th>
                        <th class="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Bil. Rekrut K.K</th>
                        <th class="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 transition-colors"
                            onclick="onKpiSortToggle()"
                            title="Klik untuk isih">
                            Bil. Rekrut Putih<span class="text-primary-600 ml-1">${sortArrow}</span>
                        </th>
                    </tr>
                </thead>
                <!-- Body -->
                <tbody>
                    ${rowsHtml}
                </tbody>
                <!-- Footer Jumlah -->
                <tfoot>
                    <tr class="bg-gray-100 font-semibold border-t-2 border-gray-300">
                        <td colspan="5" class="px-4 py-3.5 text-sm text-gray-800 text-right">JUMLAH</td>
                        <td class="px-4 py-3.5 text-sm text-gray-800 text-right font-mono">${totalKk.toLocaleString()}</td>
                        <td class="px-4 py-3.5 text-sm text-gray-800 text-right font-mono">${totalPutih.toLocaleString()}</td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <!-- Nota kaki -->
        <div class="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-400">
            <span>📍 <strong>Parlimen/DUN/PDM Mengundi</strong>: Lokasi mengundi Pegawai berdasarkan data pengundi berdaftar ('-' jika tiada padanan)</span>
            <span>📌 <strong>Rekrut K.K</strong>: Pengundi yang mempunyai Ketua Keluarga (ketua_keluarga_id IS NOT NULL)</span>
            <span>📌 <strong>Rekrut Putih</strong>: Pengundi dengan status sokongan PUTIH</span>
        </div>
    `;

    document.getElementById('kpiTableContainer').innerHTML = tableHtml;
}

// ============================================================
// REPORTING FUNCTIONS (Cetak / Excel / PDF)
// ============================================================

function onKpiPrint() {
    window.print();
}

function onKpiDownloadExcel() {
    // Generate CSV dari data yang sedang dipaparkan (filtered + sorted)
    let data = [...kpiData];
    if (kpiFilterDun) {
        data = data.filter(row => row.dun === kpiFilterDun);
    }
    data.sort((a, b) => {
        const valA = a.rekrut_putih || 0;
        const valB = b.rekrut_putih || 0;
        return kpiSortDir === 'desc' ? valB - valA : valA - valB;
    });

    // Build CSV header
    const headers = ['#', 'Nama Pegawai Penyelaras', 'Parlimen Mengundi', 'DUN Mengundi', 'PDM Mengundi', 'Bil. Rekrut K.K', 'Bil. Rekrut Putih'];
    let csv = '\uFEFF' + headers.join(',') + '\n';  // BOM untuk Excel UTF-8

    // Build CSV rows
    data.forEach((row, index) => {
        const values = [
            index + 1,
            `"${(row.nama || '-').replace(/"/g, '""')}"`,
            `"${(row.parlimen || '-').replace(/"/g, '""')}"`,
            `"${(row.dun || '-').replace(/"/g, '""')}"`,
            `"${(row.pdm || '-').replace(/"/g, '""')}"`,
            row.rekrut_kk || 0,
            row.rekrut_putih || 0
        ];
        csv += values.join(',') + '\n';
    });

    // Download as .csv file
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PPU_Pegawai_Penyelaras_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function onKpiDownloadPDF() {
    // Dapatkan data yang sedang dipaparkan
    let data = [...kpiData];
    if (kpiFilterDun) {
        data = data.filter(row => row.dun === kpiFilterDun);
    }
    data.sort((a, b) => {
        const valA = a.rekrut_putih || 0;
        const valB = b.rekrut_putih || 0;
        return kpiSortDir === 'desc' ? valB - valA : valA - valB;
    });

    // Bina HTML untuk tetingkap baru (print-friendly)
    let rowsHtml = '';
    data.forEach((row, index) => {
        rowsHtml += `<tr>
            <td>${index + 1}</td>
            <td>${row.nama || '-'}</td>
            <td>${row.parlimen || '-'}</td>
            <td>${row.dun || '-'}</td>
            <td>${row.pdm || '-'}</td>
            <td style="text-align:right">${(row.rekrut_kk || 0).toLocaleString()}</td>
            <td style="text-align:right">${(row.rekrut_putih || 0).toLocaleString()}</td>
        </tr>`;
    });

    const totalKk = data.reduce((s, r) => s + (r.rekrut_kk || 0), 0);
    const totalPutih = data.reduce((s, r) => s + (r.rekrut_putih || 0), 0);

    const pdfHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>PPU Pegawai Penyelaras</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; }
            h1 { font-size: 18pt; text-align: center; margin-bottom: 5px; }
            .subtitle { text-align: center; color: #666; font-size: 10pt; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; font-size: 9pt; }
            th { background: #f8fafc; padding: 8px 6px; text-align: left; border-bottom: 2px solid #e2e8f0; }
            td { padding: 6px; border-bottom: 1px solid #f1f5f9; }
            .text-right { text-align: right; }
            tfoot td { font-weight: bold; background: #f3f4f6; border-top: 2px solid #d1d5db; }
            @media print { @page { size: A4 landscape; margin: 10mm; } }
</style></head><body>
        <h1>PPU PEGAWAI PENYELARAS</h1>
        <p class="subtitle">Parlimen P170 Tuaran &bull; Dikeluarkan: ${new Date().toLocaleDateString('ms-MY')} &bull; ${data.length} Pegawai</p>
        <table><thead><tr>
            <th>#</th><th>Nama Pegawai Penyelaras</th><th>Parlimen</th><th>DUN</th><th>PDM</th><th class="text-right">Rekrut K.K</th><th class="text-right">Rekrut Putih</th>
        </tr></thead><tbody>${rowsHtml}</tbody>
        <tfoot><tr>
            <td colspan="5">JUMLAH</td>
            <td class="text-right">${totalKk.toLocaleString()}</td>
            <td class="text-right">${totalPutih.toLocaleString()}</td>
        </tr></tfoot></table></body></html>`;

    const w = window.open('', '_blank', 'width=1100,height=700');
    if (w) {
        w.document.write(pdfHtml);
        w.document.close();
        // Tunggu sekejap untuk render, kemudian auto print
        setTimeout(() => { w.print(); }, 500);
    }
}

// ============================================================
// EVENT HANDLERS
// ============================================================

function onKpiSortToggle() {
    // Toggle direction
    kpiSortDir = kpiSortDir === 'desc' ? 'asc' : 'desc';
    renderKpiTable();
}

function onKpiDunChange(value) {
    kpiFilterDun = value;
    renderKpiTable();
}

function onKpiReset() {
    // Reset semua state kepada default
    kpiSortDir = 'desc';
    kpiFilterDun = '';

    // Reset dropdown UI
    const dropdown = document.getElementById('kpiDunFilter');
    if (dropdown) dropdown.value = '';

    renderKpiTable();
}