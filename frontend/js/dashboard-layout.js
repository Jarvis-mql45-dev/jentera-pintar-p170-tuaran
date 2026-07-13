/**
 * 🛑 ISOLATED ZONE: DO NOT TOUCH UNLESS EXPLICITLY PERMITTED
 * 
 * dashboard-layout.js — Interact.js Drag & Resize untuk Dashboard
 * 
 * SEJARAH BUG:
 *  - 🔴 4.10 README: CSS Grid vs Transform conflict (point b)
 *  - 🔴 Listener Stacking Bug: Setiap kali init/panggil semula, Interact.js
 *    melampirkan listeners baru tanpa buang yang lama. Delta koordinat berganda.
 * 
 * SOLUSI MUTLAK:
 *  1. interact(card).unset() — buang semua listeners lama sebelum init
 *  2. applyInteractToCards() dipanggil SEKALI sahaja
 *  3. toggleDashboardEditMode() hanya enable/disable, tidak pasang semula
 * 
 * Fungsi:
 * - applySavedStyles()        — restore saved left/top/width/height
 * - enterEditMode()           — semua card → position:absolute + left/top
 * - exitEditMode()            — semua card → position:relative + reset
 * - initDashboardInteract()   — clean reset + init interact.js (panggil SEKALI)
 * - applyInteractToCards()    — pasang draggable + resizable listeners
 * - saveInteractLayout()      — simpan left/top/width/height
 * - toggleDashboardEditMode() — toggle enable/disable SAHAJA
 */

function applySavedStyles() {
    const saved = localStorage.getItem('dashboardInteractLayout');
    if (!saved) return;
    if (!state.dashboardEditMode) return;
    try {
        const layout = JSON.parse(saved);
        Object.keys(layout).forEach(id => {
            const el = document.getElementById(id);
            if (!el || !layout[id]) return;
            const data = layout[id];
            el.style.position = 'absolute';
            if (data.left !== undefined) el.style.left = data.left;
            if (data.top !== undefined) el.style.top = data.top;
            if (data.width) el.style.width = data.width;
            if (data.height) el.style.height = data.height;
            if (data.x !== undefined) el.dataset.x = data.x;
            if (data.y !== undefined) el.dataset.y = data.y;
        });
    } catch(e) {
        console.warn('applySavedStyles error:', e);
    }
}

function enterEditMode() {
    const container = document.getElementById('dashboardContainer');
    if (!container) return;
    const containerRect = container.getBoundingClientRect();
    container.style.position = 'relative';
    
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach(card => {
        const rect = card.getBoundingClientRect();
        const left = rect.left - containerRect.left;
        const top = rect.top - containerRect.top;
        card.dataset.x = left;
        card.dataset.y = top;
        card.style.position = 'absolute';
        card.style.left = left + 'px';
        card.style.top = top + 'px';
        card.style.width = card.offsetWidth + 'px';
        card.style.height = card.offsetHeight + 'px';
        card.style.margin = '0';
        card.classList.add('interact-draggable');
    });
}

function exitEditMode() {
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach(card => {
        card.style.position = '';
        card.style.left = '';
        card.style.top = '';
        card.style.width = '';
        card.style.height = '';
        card.style.transform = '';
        card.style.margin = '';
        card.classList.remove('interact-draggable');
    });
    const container = document.getElementById('dashboardContainer');
    if (container) container.style.position = '';
}

function initDashboardInteract() {
    // 🛡️ SAFETY: Force reset sebarang absolute positioning yang rosak
    // akibat localStorage corrupted dari eksperimen lama
    exitEditMode();
    
    // 🟢 SAFETY: Validate localstorage — jika data rosak/corrupted, buang
    // Format baru guna left/top/width/height. Format lama guna x/y/transform.
    try {
        const savedRaw = localStorage.getItem('dashboardInteractLayout');
        if (savedRaw) {
            const saved = JSON.parse(savedRaw);
            const keys = Object.keys(saved);
            if (keys.length > 0) {
                const first = saved[keys[0]];
                // Jika tidak ada left DAN top dalam format, ia corrupted
                if (first.left === undefined || first.top === undefined) {
                    localStorage.removeItem('dashboardInteractLayout');
                    console.log('dashboardInteractLayout cleared: corrupted format');
                }
            }
        }
    } catch(e) {
        localStorage.removeItem('dashboardInteractLayout');
        console.log('dashboardInteractLayout cleared: parse error');
    }
    
    // 🔴 LANGKAH KRITIKAL: Buang SEMUA Interact listeners LAMA
    const oldCards = document.querySelectorAll('#dashboardContainer .card');
    oldCards.forEach(card => {
        try { interact(card).unset(); } catch(e) { /* ignore */ }
    });
    
    // Set ID konsisten
    oldCards.forEach((card, index) => {
        if (!card.id || card.id.startsWith('card-')) {
            card.id = 'card-' + index;
        }
    });
    
    applySavedStyles();
    applyInteractToCards();
}

function applyInteractToCards() {
    // 🛡️ SAFETY: Pastikan Interact.js telah dimuatkan sebelum guna
    if (typeof interact === 'undefined') {
        console.warn('[Layout] Interact.js not loaded — skipping drag/resize init');
        return;
    }
    
    const cards = document.querySelectorAll('#dashboardContainer .card');
    if (cards.length === 0) return;
    
    const container = document.getElementById('dashboardContainer');
    
    cards.forEach(card => {
        try {
            interact(card).draggable({
                enabled: state.dashboardEditMode,
                inertia: true,
                modifiers: [
                    interact.modifiers.restrictRect({
                        restriction: container || 'parent',
                        endOnly: true
                    })
                ],
                listeners: {
                    move(event) {
                        const target = event.target;
                        const x = (parseFloat(target.dataset.x) || 0) + event.dx;
                        const y = (parseFloat(target.dataset.y) || 0) + event.dy;
                        target.style.left = x + 'px';
                        target.style.top = y + 'px';
                        target.dataset.x = x;
                        target.dataset.y = y;
                    },
                    end(event) {
                        saveInteractLayout();
                    }
                }
            });
            
            interact(card).resizable({
                enabled: state.dashboardEditMode,
                edges: { right: true, bottom: true, bottomRight: true },
                listeners: {
                    move(event) {
                        const target = event.target;
                        let x = parseFloat(target.dataset.x) || 0;
                        let y = parseFloat(target.dataset.y) || 0;
                        
                        if (event.rect.width > 100) {
                            target.style.width = event.rect.width + 'px';
                        }
                        if (event.rect.height > 80) {
                            target.style.height = event.rect.height + 'px';
                        }
                        
                        x += event.deltaRect.left;
                        y += event.deltaRect.top;
                        target.style.left = x + 'px';
                        target.style.top = y + 'px';
                        target.dataset.x = x;
                        target.dataset.y = y;
                        
                        const canvases = target.querySelectorAll('canvas');
                        canvases.forEach(canvas => {
                            Object.values(state.charts).forEach(chart => {
                                if (chart && chart.canvas && chart.canvas.id === canvas.id) {
                                    chart.resize();
                                }
                            });
                        });
                    },
                    end(event) {
                        saveInteractLayout();
                    }
                }
            });
        } catch(e) {
            console.warn('[Layout] interact() init error for card:', card.id, e);
        }
    });
}

function saveInteractLayout() {
    const cards = document.querySelectorAll('#dashboardContainer .card');
    const layout = {};
    cards.forEach(card => {
        const id = card.id;
        if (id) {
            layout[id] = {
                x: parseFloat(card.dataset.x) || 0,
                y: parseFloat(card.dataset.y) || 0,
                left: card.style.left || '',
                top: card.style.top || '',
                width: card.style.width || '',
                height: card.style.height || ''
            };
        }
    });
    localStorage.setItem('dashboardInteractLayout', JSON.stringify(layout));
}

function toggleDashboardEditMode() {
    state.dashboardEditMode = !state.dashboardEditMode;
    
    if (state.dashboardEditMode) {
        enterEditMode();
        applySavedStyles();
    } else {
        exitEditMode();
        saveInteractLayout();
    }
    
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach(card => {
        try {
            interact(card).draggable(state.dashboardEditMode);
            interact(card).resizable(state.dashboardEditMode);
        } catch(e) { console.warn('toggle error:', card.id, e); }
    });
    
    showToast(state.dashboardEditMode ? '✏️ Mod Ubah Susunan Diaktifkan' : '🔒 Susunan Dikunci');
}