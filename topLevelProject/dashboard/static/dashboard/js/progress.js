// dashboard/static/dashboard/js/progress.js
// Circular Progress Indicator

document.addEventListener('DOMContentLoaded', function() {
    initializeProgressCircle();
});

function initializeProgressCircle() {
    const progressInput = document.getElementById('progress-value');
    if (!progressInput) return;
    
    const progressValue = parseFloat(progressInput.value) || 0;
    const circle = document.querySelector('.progress-circle-fill');
    const percentageText = document.querySelector('.progress-percentage');
    const container = document.querySelector('.progress-circle-container');
    
    if (!circle || !percentageText || !container) return;
    
    // Circle calculations
    const radius = 85; // Must match the 'r' attribute in your SVG
    const circumference = 2 * Math.PI * radius; // ≈ 534.07
    
    // Set initial state
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference;
    
    // Determine progress level for color
    let progressLevel = 'low';
    if (progressValue >= 100) {
        progressLevel = 'complete';
    } else if (progressValue >= 70) {
        progressLevel = 'high';
    } else if (progressValue >= 40) {
        progressLevel = 'medium';
    } else {
        progressLevel = 'low';
    }
    
    container.setAttribute('data-progress-level', progressLevel);
    
    // Animate progress after a brief delay
    setTimeout(() => {
        animateProgress(circle, percentageText, progressValue, circumference);
    }, 300);
}

function animateProgress(circle, percentageText, targetProgress, circumference) {
    const duration = 1000; // 1 second
    const startTime = performance.now();
    const startProgress = 0;
    
    function updateProgress(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = startProgress + (targetProgress - startProgress) * easeOut;
        
        // Update circle
        const offset = circumference - (currentValue / 100) * circumference;
        circle.style.strokeDashoffset = offset;
        
        // Update text
        percentageText.textContent = Math.round(currentValue) + '%';
        
        // Continue animation
        if (progress < 1) {
            requestAnimationFrame(updateProgress);
        } else {
            // Ensure final value is exact
            circle.style.strokeDashoffset = circumference - (targetProgress / 100) * circumference;
            percentageText.textContent = Math.round(targetProgress) + '%';
        }
    }
    
    requestAnimationFrame(updateProgress);
}

// Update progress dynamically (can be called from other scripts)
function updateProgressCircle(newProgress) {
    const circle = document.querySelector('.progress-circle-fill');
    const percentageText = document.querySelector('.progress-percentage');
    const container = document.querySelector('.progress-circle-container');
    
    if (!circle || !percentageText || !container) return;
    
    const radius = 85;
    const circumference = 2 * Math.PI * radius;
    
    // Update color
    let progressLevel = 'low';
    if (newProgress >= 100) {
        progressLevel = 'complete';
    } else if (newProgress >= 70) {
        progressLevel = 'high';
    } else if (newProgress >= 40) {
        progressLevel = 'medium';
    } else {
        progressLevel = 'low';
    }
    
    
    container.setAttribute('data-progress-level', progressLevel);
    
    // Animate to new progress
    animateProgress(circle, percentageText, newProgress, circumference);
}