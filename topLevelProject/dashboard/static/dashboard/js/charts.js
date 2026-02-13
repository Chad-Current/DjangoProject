// dashboard/static/dashboard/js/dashboard-charts.js
// Dashboard Overview Charts and Statistics

document.addEventListener('DOMContentLoaded', function() {
    initializeDashboardCharts();
    setupStatCardAnimations();
});

function initializeDashboardCharts() {
    // Animate stat cards on load
    animateStatCards();
    
    // Initialize any donut/pie charts
    const donutCharts = document.querySelectorAll('[data-chart-type="donut"]');
    donutCharts.forEach(chart => {
        animateDonutChart(chart);
    });
}

function setupStatCardAnimations() {
    const statCards = document.querySelectorAll('.stat-card');
    
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            threshold: 0.1
        });
        
        statCards.forEach(card => observer.observe(card));
    } else {
        // Fallback for browsers without IntersectionObserver
        statCards.forEach(card => card.classList.add('visible'));
    }
}

function animateStatCards() {
    const statValues = document.querySelectorAll('.stat-value h3');
    
    statValues.forEach(element => {
        const targetText = element.textContent;
        const targetNumber = parseInt(targetText);
        
        // Only animate if it's a number
        if (!isNaN(targetNumber)) {
            animateNumber(element, 0, targetNumber, 1500);
        }
    });
}

function animateNumber(element, start, end, duration) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * easeOut);
        
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = end;
        }
    }
    
    requestAnimationFrame(update);
}

// Create a simple donut chart
function createDonutChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const {
        size = 280,
        strokeWidth = 40,
        centerText = '',
        centerValue = '',
        colors = ['#324d72', '#4facfe', '#f093fb', '#43e97b', '#fa709a']
    } = options;
    
    const radius = (size / 2) - (strokeWidth / 2);
    const circumference = 2 * Math.PI * radius;
    const total = data.reduce((sum, item) => sum + item.value, 0);
    
    let currentOffset = 0;
    
    // Create SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', size);
    svg.setAttribute('height', size);
    svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
    svg.classList.add('donut-chart-svg');
    
    // Create segments
    data.forEach((item, index) => {
        const percentage = (item.value / total) * 100;
        const segmentLength = (percentage / 100) * circumference;
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', size / 2);
        circle.setAttribute('cy', size / 2);
        circle.setAttribute('r', radius);
        circle.setAttribute('fill', 'none');
        circle.setAttribute('stroke', colors[index % colors.length]);
        circle.setAttribute('stroke-width', strokeWidth);
        circle.setAttribute('stroke-dasharray', `${segmentLength} ${circumference - segmentLength}`);
        circle.setAttribute('stroke-dashoffset', -currentOffset);
        circle.classList.add('donut-segment');
        circle.setAttribute('data-label', item.label);
        circle.setAttribute('data-value', item.value);
        
        svg.appendChild(circle);
        
        currentOffset += segmentLength;
    });
    
    container.innerHTML = '';
    container.appendChild(svg);
    
    // Add center text if provided
    if (centerText || centerValue) {
        const centerDiv = document.createElement('div');
        centerDiv.className = 'donut-center';
        
        if (centerValue) {
            const valueDiv = document.createElement('div');
            valueDiv.className = 'donut-center-value';
            valueDiv.textContent = centerValue;
            centerDiv.appendChild(valueDiv);
        }
        
        if (centerText) {
            const labelDiv = document.createElement('div');
            labelDiv.className = 'donut-center-label';
            labelDiv.textContent = centerText;
            centerDiv.appendChild(labelDiv);
        }
        
        container.style.position = 'relative';
        container.appendChild(centerDiv);
    }
    
    // Add legend
    createChartLegend(containerId + '-legend', data, colors);
}

function animateDonutChart(chartElement) {
    const segments = chartElement.querySelectorAll('.donut-segment');
    
    segments.forEach((segment, index) => {
        segment.style.opacity = '0';
        setTimeout(() => {
            segment.style.transition = 'opacity 0.5s ease';
            segment.style.opacity = '1';
        }, index * 200);
    });
}

// Create legend for charts
function createChartLegend(containerId, data, colors) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    container.className = 'chart-legend';
    
    data.forEach((item, index) => {
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        
        const colorBox = document.createElement('div');
        colorBox.className = 'legend-color';
        colorBox.style.backgroundColor = colors[index % colors.length];
        
        const label = document.createElement('span');
        label.className = 'legend-label';
        label.textContent = `${item.label} (${item.value})`;
        
        legendItem.appendChild(colorBox);
        legendItem.appendChild(label);
        container.appendChild(legendItem);
    });
}

// Summary statistics for dashboard overview
function createDashboardSummary(data) {
    const summaryContainer = document.querySelector('.summary-stats');
    if (!summaryContainer) return;
    
    summaryContainer.innerHTML = '';
    
    data.forEach(stat => {
        const card = document.createElement('div');
        card.className = 'summary-card';
        
        const value = document.createElement('div');
        value.className = 'summary-value';
        value.textContent = stat.value;
        
        const label = document.createElement('div');
        label.className = 'summary-label';
        label.textContent = stat.label;
        
        card.appendChild(value);
        card.appendChild(label);
        summaryContainer.appendChild(card);
    });
    
    // Trigger animation
    setTimeout(() => animateStatCards(), 100);
}

// Calculate and update progress based on completion criteria
function calculateProgress(counts) {
    const criteria = {
        accounts: { weight: 0.25, target: 10 },
        devices: { weight: 0.15, target: 5 },
        contacts: { weight: 0.20, target: 5 },
        estates: { weight: 0.15, target: 3 },
        documents: { weight: 0.15, target: 5 },
        family_knows: { weight: 0.05, target: 3 },
        care_relations: { weight: 0.05, target: 1 }
    };
    
    let totalProgress = 0;
    
    Object.keys(criteria).forEach(key => {
        const { weight, target } = criteria[key];
        const count = counts[key] || 0;
        const itemProgress = Math.min(count / target, 1) * weight;
        totalProgress += itemProgress;
    });
    
    return Math.round(totalProgress * 100);
}

// Update dashboard with new data
function updateDashboardData(newData) {
    // Update stat cards
    Object.keys(newData).forEach(key => {
        const statElement = document.querySelector(`[data-stat="${key}"] .stat-value h3`);
        if (statElement) {
            const newValue = newData[key];
            const oldValue = parseInt(statElement.textContent) || 0;
            if (newValue !== oldValue) {
                animateNumber(statElement, oldValue, newValue, 1000);
            }
        }
    });
    
    // Recalculate progress
    const newProgress = calculateProgress(newData);
    if (typeof updateProgressCircle === 'function') {
        updateProgressCircle(newProgress);
    }
}

// Tooltip functionality for interactive charts
function setupChartTooltips() {
    const chartElements = document.querySelectorAll('.donut-segment, .bar-fill, .vertical-bar-wrapper');
    
    chartElements.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            showTooltip(e, this);
        });
        
        element.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
}

function showTooltip(event, element) {
    const label = element.getAttribute('data-label');
    const value = element.getAttribute('data-value');
    
    if (!label && !value) return;
    
    let tooltip = document.getElementById('chart-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'chart-tooltip';
        tooltip.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            pointer-events: none;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;
        document.body.appendChild(tooltip);
    }
    
    tooltip.textContent = label ? `${label}: ${value}` : value;
    tooltip.style.left = event.clientX + 15 + 'px';
    tooltip.style.top = event.clientY + 15 + 'px';
    tooltip.style.opacity = '1';
}

function hideTooltip() {
    const tooltip = document.getElementById('chart-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
    }
}

// Initialize tooltips if elements exist
setTimeout(() => {
    if (document.querySelector('.donut-segment, .bar-fill, .vertical-bar-wrapper')) {
        setupChartTooltips();
    }
}, 500);