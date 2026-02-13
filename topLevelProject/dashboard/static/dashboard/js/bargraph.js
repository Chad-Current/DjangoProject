// dashboard/static/dashboard/js/bargraph.js
// Horizontal Bar Charts for Category Breakdowns

document.addEventListener('DOMContentLoaded', function() {
    initializeBarCharts();
});

function initializeBarCharts() {
    // Initialize all bar charts on the page
    const barCharts = document.querySelectorAll('[data-chart-type="bar"]');
    barCharts.forEach(chart => {
        animateBarChart(chart);
    });
    
    // Set up observer for charts that come into view
    if ('IntersectionObserver' in window) {
        setupBarChartObserver();
    }
}

function setupBarChartObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                animateBarChart(entry.target);
                entry.target.dataset.animated = 'true';
            }
        });
    }, {
        threshold: 0.2
    });
    
    const barCharts = document.querySelectorAll('[data-chart-type="bar"]');
    barCharts.forEach(chart => observer.observe(chart));
}

function animateBarChart(chartElement) {
    const bars = chartElement.querySelectorAll('.bar-fill');
    
    bars.forEach((bar, index) => {
        const targetWidth = bar.getAttribute('data-value') || '0';
        
        // Delay each bar slightly for staggered effect
        setTimeout(() => {
            bar.style.width = targetWidth + '%';
        }, index * 100);
    });
}

// Create bar chart programmatically
function createBarChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const {
        title = 'Chart',
        maxValue = Math.max(...data.map(d => d.value)),
        showValues = true,
        colorClass = 'accounts'
    } = options;
    
    // Clear container
    container.innerHTML = '';
    
    // Create chart wrapper
    const chartDiv = document.createElement('div');
    chartDiv.className = 'bar-chart';
    chartDiv.setAttribute('data-chart-type', 'bar');
    
    // Add each bar
    data.forEach((item, index) => {
        const percentage = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
        
        const barRow = document.createElement('div');
        barRow.className = 'bar-row';
        
        // Label
        const label = document.createElement('div');
        label.className = 'bar-label';
        label.textContent = item.label;
        
        // Bar wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'bar-wrapper';
        
        // Bar fill
        const fill = document.createElement('div');
        fill.className = `bar-fill ${item.colorClass || colorClass}`;
        fill.setAttribute('data-value', percentage);
        fill.style.width = '0%';
        
        if (showValues && item.value > 0) {
            const valueSpan = document.createElement('span');
            valueSpan.className = 'bar-value';
            valueSpan.textContent = item.value;
            fill.appendChild(valueSpan);
        }
        
        wrapper.appendChild(fill);
        
        // Count
        const count = document.createElement('div');
        count.className = 'bar-count';
        count.textContent = item.value;
        
        // Assemble
        barRow.appendChild(label);
        barRow.appendChild(wrapper);
        barRow.appendChild(count);
        
        chartDiv.appendChild(barRow);
    });
    
    container.appendChild(chartDiv);
    
    // Trigger animation
    setTimeout(() => {
        animateBarChart(chartDiv);
    }, 100);
}

// Helper function to create account category chart
function createAccountCategoriesChart(containerId, categories) {
    const data = Object.entries(categories)
        .map(([key, value]) => ({
            label: formatCategoryLabel(key),
            value: value,
            colorClass: 'accounts'
        }))
        .filter(item => item.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10); // Top 10 categories
    
    createBarChart(containerId, data, {
        title: 'Account Categories',
        showValues: true,
        colorClass: 'accounts'
    });
}

// Helper function to create device types chart
function createDeviceTypesChart(containerId, deviceTypes) {
    const data = Object.entries(deviceTypes)
        .map(([key, value]) => ({
            label: formatCategoryLabel(key),
            value: value,
            colorClass: 'devices'
        }))
        .filter(item => item.value > 0)
        .sort((a, b) => b.value - a.value);
    
    createBarChart(containerId, data, {
        title: 'Device Types',
        showValues: true,
        colorClass: 'devices'
    });
}

// Format category labels (convert snake_case to Title Case)
function formatCategoryLabel(key) {
    return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Update existing chart with new data
function updateBarChart(containerId, newData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const bars = container.querySelectorAll('.bar-fill');
    const counts = container.querySelectorAll('.bar-count');
    
    newData.forEach((item, index) => {
        if (bars[index]) {
            const percentage = Math.max(...newData.map(d => d.value)) > 0 
                ? (item.value / Math.max(...newData.map(d => d.value))) * 100 
                : 0;
            
            bars[index].style.width = percentage + '%';
            
            const valueSpan = bars[index].querySelector('.bar-value');
            if (valueSpan) {
                valueSpan.textContent = item.value;
            }
        }
        
        if (counts[index]) {
            counts[index].textContent = item.value;
        }
    });
}