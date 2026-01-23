/**
 * Progress Circle Component
 * Updates a circular progress indicator based on provided percentage
 */

class ProgressCircle {
  constructor(containerSelector, options = {}) {
    this.container = document.querySelector(containerSelector);
    if (!this.container) {
      console.error(`Progress circle container not found: ${containerSelector}`);
      return;
    }
    
    this.circle = this.container.querySelector('.progress-circle-fill');
    this.percentageText = this.container.querySelector('.progress-percentage');
    this.radius = 85; // Must match the circle's r attribute
    this.circumference = 2 * Math.PI * this.radius;
    
    // Options
    this.animationDuration = options.animationDuration || 1000;
    this.animateOnLoad = options.animateOnLoad !== false;
    
    this.init();
  }
  
  init() {
    // Set initial dasharray
    this.circle.style.strokeDasharray = this.circumference;
    this.circle.style.strokeDashoffset = this.circumference;
  }
  
  setProgress(percentage) {
    // Clamp percentage between 0 and 100
    const progress = Math.min(100, Math.max(0, percentage));
    
    // Calculate offset
    const offset = this.circumference - (progress / 100) * this.circumference;
    
    // Animate the circle
    this.circle.style.strokeDashoffset = offset;
    
    // Animate the percentage text
    this.animatePercentage(progress);
    
    // Update color based on progress level
    this.updateProgressLevel(progress);
  }
  
  animatePercentage(targetPercentage) {
    const startPercentage = parseFloat(this.percentageText.textContent) || 0;
    const startTime = performance.now();
    
    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / this.animationDuration, 1);
      
      // Easing function (easeOutCubic)
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      
      const currentPercentage = startPercentage + (targetPercentage - startPercentage) * easeProgress;
      this.percentageText.textContent = Math.round(currentPercentage) + '%';
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        this.percentageText.textContent = Math.round(targetPercentage) + '%';
      }
    };
    
    requestAnimationFrame(animate);
  }
  
  updateProgressLevel(percentage) {
    let level;
    
    if (percentage === 100) {
      level = 'complete';
    } else if (percentage >= 70) {
      level = 'high';
    } else if (percentage >= 40) {
      level = 'medium';
    } else {
      level = 'low';
    }
    
    this.container.setAttribute('data-progress-level', level);
  }
}

// Initialize progress circle when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Get progress from Django template context
  const progressValue = parseFloat(document.getElementById('progress-value')?.value || 0);
  
  // Create progress circle instance
  const progressCircle = new ProgressCircle('.progress-circle-container', {
    animationDuration: 1500,
    animateOnLoad: true
  });
  
  // Set progress with slight delay for visual effect
  setTimeout(() => {
    progressCircle.setProgress(progressValue);
  }, 100);
});

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ProgressCircle;
}