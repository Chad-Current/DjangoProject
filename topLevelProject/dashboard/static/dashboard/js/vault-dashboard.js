// dashboard/static/dashboard/js/vault-dashboard.js
// Digital Vault Dashboard Interactions

document.addEventListener('DOMContentLoaded', function () {
    initializeVaultDashboard();
});

function initializeVaultDashboard() {
    animateVaultProgress();
    animateLayerBars();
    animateLogEntries();
    setupLayerNavigation();
}

// ─── Animate the central vault progress circle ────────────────────────────
function animateVaultProgress() {
    const progressInput = document.getElementById('progress-value');
    // Targets the correct IDs from the HTML template
    const progressPercentEl = document.querySelector('.progress-percentage');
    const circleContainer   = document.querySelector('.progress-circle-container');
    const circleFill        = document.querySelector('.progress-circle-fill');

    if (!progressInput || !progressPercentEl || !circleFill) return;

    const targetProgress = parseFloat(progressInput.value) || 0;
    const circumference  = 534.07; // 2 * π * 85
    const duration       = 2000;   // ms
    const startTime      = performance.now();

    // Set the data-progress-level attribute for CSS colour switching
    let level = 'low';
    if      (targetProgress >= 100) level = 'complete';
    else if (targetProgress >= 70)  level = 'high';
    else if (targetProgress >= 40)  level = 'medium';
    if (circleContainer) circleContainer.setAttribute('data-progress-level', level);

    function updateProgress(currentTime) {
        const elapsed  = currentTime - startTime;
        const t        = Math.min(elapsed / duration, 1);
        const easeOut  = 1 - Math.pow(1 - t, 3);
        const current  = Math.round(targetProgress * easeOut);

        // Update counter text
        progressPercentEl.textContent = current + '%';

        // Update stroke-dashoffset so the arc fills proportionally
        const offset = circumference - (circumference * current) / 100;
        circleFill.style.strokeDashoffset = offset;

        // Update text colour to match progress level
        updateProgressTextColor(current, progressPercentEl);

        if (t < 1) requestAnimationFrame(updateProgress);
    }

    requestAnimationFrame(updateProgress);
}

// Update percentage text colour based on progress value
function updateProgressTextColor(progress, element) {
    if (!element) return;
    if      (progress >= 100) element.style.color = '#192EFF'; // blue
    else if (progress >= 70)  element.style.color = '#19FF5A'; // green
    else if (progress >= 40)  element.style.color = '#FFCE19'; // yellow
    else                      element.style.color = '#FF2B2B'; // red
}

// ─── Animate protection-layer strength bars ───────────────────────────────
function animateLayerBars() {
    const layers = document.querySelectorAll('.layer');

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting && !entry.target.dataset.animated) {
                    setTimeout(() => {
                        animateSingleLayer(entry.target);
                        entry.target.dataset.animated = 'true';
                    }, index * 150);
                }
            });
        }, { threshold: 0.2 });

        layers.forEach(layer => observer.observe(layer));
    } else {
        layers.forEach((layer, i) => {
            setTimeout(() => animateSingleLayer(layer), i * 150);
        });
    }
}

function animateSingleLayer(layerElement) {
    const fill = layerElement.querySelector('.layer-strength-fill');
    if (!fill) return;

    const targetWidth = fill.style.width;
    fill.style.width  = '0%';

    // Force reflow so the transition fires
    void fill.offsetWidth;

    fill.style.transition = 'width 1s cubic-bezier(0.4, 0, 0.2, 1)';
    fill.style.width      = targetWidth;
}

// ─── Animate security log entries ─────────────────────────────────────────
function animateLogEntries() {
    const entries = document.querySelectorAll('.log-entry');

    entries.forEach((entry, index) => {
        entry.style.opacity   = '0';
        entry.style.transform = 'translateX(-20px)';

        setTimeout(() => {
            entry.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            entry.style.opacity    = '1';
            entry.style.transform  = 'translateX(0)';
        }, index * 100);
    });
}

// ─── Layer click navigation ────────────────────────────────────────────────
// Consolidated into a single DOMContentLoaded (removed duplicate listener).
function setupLayerNavigation() {
    const routes = {
        accounts:  '/accounts/',
        assets:    '/devices/',    // .assets class → devices route
        legacy:    '/contacts/',   // .legacy class → contacts route (was missing)
        estate:    '/estate/',     // .estate class → estate route (was missing)
        documents: '/documents/',
        family:    '/familyawareness/',
    };

    document.querySelectorAll('.layer').forEach(layer => {
        layer.addEventListener('click', function () {
            // Derive key from the second class (e.g. "layer accounts" → "accounts")
            const key = Array.from(this.classList).find(c => c !== 'layer');
            if (key && routes[key]) {
                window.location.href = routes[key];
            }
        });
    });
}