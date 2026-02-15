// dashboard/static/dashboard/js/vault-dashboard.js
// Digital Vault Dashboard Interactions

document.addEventListener('DOMContentLoaded', function() {
    initializeVaultDashboard();
});

function initializeVaultDashboard() {
    animateVaultProgress();
    setupLockInteractions();
    animateLayerBars();
    animateLogEntries();
}

// Animate the central vault progress display
function animateVaultProgress() {
    const progressInput = document.getElementById('progress-value');
    const progressText = document.getElementById('vault-progress-text');
    
    if (!progressInput || !progressText) return;
    
    const targetProgress = parseFloat(progressInput.value) || 0;
    const duration = 2000; // 2 seconds
    const startTime = performance.now();
    
    function updateProgress(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out cubic)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.round(targetProgress * easeOut);
        
        progressText.textContent = currentValue + '%';
        
        // Update glow based on progress
        updateVaultGlow(currentValue);
        
        if (progress < 1) {
            requestAnimationFrame(updateProgress);
        }
    }
    
    requestAnimationFrame(updateProgress);
}

// Update vault progress color based on progress (subtle color only, no glow)
function updateVaultGlow(progress) {
    const progressDisplay = document.getElementById('vault-progress-text');
    if (!progressDisplay) return;
    
    if (progress >= 100) {
        progressDisplay.style.color = '#2d6a9c'; // Strong blue
    } else if (progress >= 70) {
        progressDisplay.style.color = '#62a2ce'; // Medium blue
    } else if (progress >= 40) {
        progressDisplay.style.color = '#ffa62b'; // Accent orange
    } else {
        progressDisplay.style.color = '#254e70'; // Dark blue
    }
}

// Setup lock click interactions
function setupLockInteractions() {
    const locks = document.querySelectorAll('.vault-lock');
    
    locks.forEach((lock, index) => {
        lock.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            handleLockClick(category, this);
        });
    });
}

function handleLockClick(category, lockElement) {
    // Add a click animation
    lockElement.style.transform = 'scale(0.95)';
    setTimeout(() => {
        lockElement.style.transform = 'scale(1)';
    }, 100);
    
    // Navigate to the corresponding section
    const routes = {
        'Accounts': '/accounts/',
        'Devices': '/devices/',
        'Contacts': '/contacts/',
        'Documents': '/estate/'
    };
    
    const route = routes[category];
    if (route) {
        window.location.href = route;
    }
}

// Animate protection layer strength bars
function animateLayerBars() {
    const layers = document.querySelectorAll('.layer');
    
    // Use Intersection Observer for scroll-based animation
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting && !entry.target.dataset.animated) {
                    setTimeout(() => {
                        animateLayer(entry.target);
                        entry.target.dataset.animated = 'true';
                    }, index * 150);
                }
            });
        }, {
            threshold: 0.2
        });
        
        layers.forEach(layer => observer.observe(layer));
    } else {
        // Fallback: animate all immediately
        layers.forEach((layer, index) => {
            setTimeout(() => {
                animateLayer(layer);
            }, index * 150);
        });
    }
}

function animateLayer(layerElement) {
    const strengthFill = layerElement.querySelector('.layer-strength-fill');
    if (!strengthFill) return;
    
    const targetWidth = strengthFill.style.width;
    strengthFill.style.width = '0%';
    
    // Force reflow
    strengthFill.offsetWidth;
    
    // Animate to target
    strengthFill.style.transition = 'width 1s cubic-bezier(0.4, 0, 0.2, 1)';
    strengthFill.style.width = targetWidth;
}

// Animate security log entries
function animateLogEntries() {
    const entries = document.querySelectorAll('.log-entry');
    
    entries.forEach((entry, index) => {
        entry.style.opacity = '0';
        entry.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            entry.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            entry.style.opacity = '1';
            entry.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

// Add click handler to layers for navigation
document.addEventListener('DOMContentLoaded', function() {
    const layers = document.querySelectorAll('.layer');
    
    layers.forEach(layer => {
        layer.addEventListener('click', function() {
            const layerClass = this.classList.contains('accounts') ? 'accounts' :
                              this.classList.contains('assets') ? 'devices' :
                              this.classList.contains('legacy') ? 'estates' :
                              'contacts';
            
            const routes = {
                'accounts': '/accounts/',
                'devices': '/devices/',
                'estates': '/estate/',
                'contacts': '/contacts/'
            };
            
            if (routes[layerClass]) {
                window.location.href = routes[layerClass];
            }
        });
    });
});

// Subtle highlight for unlocked locks (light theme - no pulse)
function highlightUnlockedLocks() {
    const unlockedLocks = document.querySelectorAll('.vault-lock:not(.locked)');
    
    unlockedLocks.forEach(lock => {
        lock.style.borderColor = '#ffa62b'; // Subtle orange border hint
    });
}

// Call after initial animations
setTimeout(highlightUnlockedLocks, 3000);