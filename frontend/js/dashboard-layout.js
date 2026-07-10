/**
 * 🛑 ISOLATED ZONE: DO NOT TOUCH UNLESS EXPLICITLY PERMITTED
 * 
 * dashboard-layout.js — Interact.js Drag & Resize untuk Dashboard
 * Fail ini DIASINGKAN dari frontend/index.html untuk mengelakkan
 * regresi keselamatan dan visual. Sebarang perubahan mesti melalui
 * perbincangan dengan pentadbir sistem.
 * 
 * Fungsi:
 * - applySavedStyles()       — baca localStorage, inject inline CSS terus ke DOM
 * - initDashboardInteract()  — apply interact.js (draggable + resizable)
 * - applyInteractToCards()   — pasang interact listeners
 * - saveInteractLayout()     — simpan x, y, width, height ke localStorage
 * - toggleDashboardEditMode() — butang toggle edit mode
 * 
 * Kebergantungan: Interact.js CDN, State global `state`
 */

function applySavedStyles() {
    const saved = localStorage.getItem('dashboardInteractLayout');
    if (!saved) return;
    try {
        const layout = JSON.parse(saved);
        Object.keys(layout).forEach(id => {
            const el = document.getElementById(id);
            if (!el || !layout[id]) return;
            const data = layout[id];
            // SUNTIK TERUS INLINE CSS
            if (data.w) el.style.width = data.w;
            if (data.h) el.style.height = data.h;
            if (data.transform) el.style.transform = data.transform;
            // Simpan dataset untuk Interact.js
            if (data.x !== undefined) el.dataset.x = data.x;
            if (data.y !== undefined) el.dataset.y = data.y;
        });
    } catch(e) {
        console.warn('applySavedStyles error:', e);
    }
}

function initDashboardInteract() {
    // Step 1: Set ID konsisten berdasarkan indeks SEBELUM restore styles
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach((card, index) => {
        if (!card.id || card.id.startsWith('card-')) {
            card.id = 'card-' + index;
        }
    });
    
    // Step 2: Restore saved styles (inject inline CSS terus)
    applySavedStyles();
    
    // Step 3: Apply interact.js
    applyInteractToCards();
}

function applyInteractToCards() {
    const cards = document.querySelectorAll('#dashboardContainer .card');
    if (cards.length === 0) return;
    
    const container = document.getElementById('dashboardContainer');
    
    cards.forEach(card => {
        
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
                    target.style.transform = `translate(${x}px, ${y}px)`;
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
                    target.style.transform = `translate(${x}px, ${y}px)`;
                    target.dataset.x = x;
                    target.dataset.y = y;
                    
                    // Resize charts inside card
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
                w: card.style.width || '',
                h: card.style.height || '',
                transform: card.style.transform || ''
            };
        }
    });
    localStorage.setItem('dashboardInteractLayout', JSON.stringify(layout));
}

function toggleDashboardEditMode() {
    state.dashboardEditMode = !state.dashboardEditMode;
    
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach(card => {
        interact(card).draggable(state.dashboardEditMode);
        interact(card).resizable(state.dashboardEditMode);
        card.classList.toggle('interact-draggable', state.dashboardEditMode);
    });
    
    showToast(state.dashboardEditMode ? '✏️ Mod Ubah Susunan Diaktifkan' : '🔒 Susunan Dikunci');
    if (!state.dashboardEditMode) {
        saveInteractLayout();
    }
}