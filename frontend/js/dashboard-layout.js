/**
 * 🛑 ISOLATED ZONE: DO NOT TOUCH UNLESS EXPLICITLY PERMITTED
 * 
 * dashboard-layout.js — Interact.js Drag & Resize untuk Dashboard
 * Fail ini DIASINGKAN dari frontend/index.html untuk mengelakkan
 * regresi keselamatan dan visual. Sebarang perubahan mesti melalui
 * perbincangan dengan pentadbir sistem.
 * 
 * Fungsi:
 * - initDashboardInteract()  — restore layout + apply interact
 * - applyInteractToCards()   — draggable + resizable dengan Interact.js
 * - saveInteractLayout()     — simpan x, y, width, height ke localStorage
 * - toggleDashboardEditMode()  — butang toggle edit mode
 * 
 * Kebergantungan: Interact.js CDN (dimuatkan di index.html head)
 *                 State global `state` (dari index.html)
 */

function initDashboardInteract() {
    // Restore saved positions from localStorage
    const saved = localStorage.getItem('dashboardInteractLayout');
    if (saved) {
        try {
            const layout = JSON.parse(saved);
            Object.keys(layout).forEach(id => {
                const el = document.getElementById(id);
                if (el && layout[id]) {
                    el.style.transform = `translate(${layout[id].x}px, ${layout[id].y}px)`;
                    if (layout[id].width) el.style.width = layout[id].width;
                    if (layout[id].height) el.style.height = layout[id].height;
                }
            });
        } catch(e) {}
    }
    
    // Apply interact.js
    applyInteractToCards();
}

function applyInteractToCards() {
    const cards = document.querySelectorAll('#dashboardContainer .card');
    if (cards.length === 0) return;
    
    // Get container for restriction
    const container = document.getElementById('dashboardContainer');
    
    cards.forEach(card => {
        // Generate unique ID if not exist
        if (!card.id) {
            card.id = 'card-' + Math.random().toString(36).substr(2, 9);
        }
        
        // Enable dragging with restriction
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
        
        // Enable resize
        interact(card).resizable({
            enabled: state.dashboardEditMode,
            edges: { right: true, bottom: true, bottomRight: true },
            listeners: {
                move(event) {
                    const target = event.target;
                    let x = parseFloat(target.dataset.x) || 0;
                    let y = parseFloat(target.dataset.y) || 0;
                    
                    // Update width
                    if (event.rect.width > 100) {
                        target.style.width = event.rect.width + 'px';
                    }
                    // Update height
                    if (event.rect.height > 80) {
                        target.style.height = event.rect.height + 'px';
                    }
                    
                    // Update position
                    x += event.deltaRect.left;
                    y += event.deltaRect.top;
                    target.style.transform = `translate(${x}px, ${y}px)`;
                    target.dataset.x = x;
                    target.dataset.y = y;
                    
                    // Resize all charts inside this card
                    const canvases = target.querySelectorAll('canvas');
                    canvases.forEach(canvas => {
                        const chartId = canvas.id;
                        if (chartId) {
                            Object.values(state.charts).forEach(chart => {
                                if (chart && chart.canvas && chart.canvas.id === chartId) {
                                    chart.resize();
                                }
                            });
                        }
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
            const x = parseFloat(card.dataset.x) || 0;
            const y = parseFloat(card.dataset.y) || 0;
            const width = card.style.width;
            const height = card.style.height;
            layout[id] = { x, y, width, height };
        }
    });
    localStorage.setItem('dashboardInteractLayout', JSON.stringify(layout));
}

function toggleDashboardEditMode() {
    state.dashboardEditMode = !state.dashboardEditMode;
    
    const cards = document.querySelectorAll('#dashboardContainer .card');
    cards.forEach(card => {
        // Update draggable and resizable state
        interact(card).draggable(state.dashboardEditMode);
        interact(card).resizable(state.dashboardEditMode);
        card.classList.toggle('interact-draggable', state.dashboardEditMode);
    });
    
    showToast(state.dashboardEditMode ? '✏️ Mod Ubah Susunan Diaktifkan' : '🔒 Susunan Dikunci');
    if (!state.dashboardEditMode) {
        saveInteractLayout();
    }
}