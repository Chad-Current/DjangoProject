const elements = {
    infograph: document.querySelector('.infographic-container'),
    infograph_mobile: document.querySelector('.infographic-container-mobile'),
    compchart: document.querySelector('.comp-chart'),
    compchart_mobile: document.querySelector('.comp-chart-mobile')
  };
  
  const MOBILE_BREAKPOINT = 768;
  let active_mobile = false;
  
  function updateElementVisibility() {
    const isMobile = window.innerWidth <= MOBILE_BREAKPOINT;
    
    elements.infograph.style.display = isMobile ? 'none' : 'grid';
    elements.infograph_mobile.style.display = isMobile ? 'flex' : 'none';
    elements.compchart.style.display = isMobile ? 'none' : 'flex';
    elements.compchart_mobile.style.display = isMobile ? 'flex' : 'none';
  }
  
  function logWindowSize() {
    console.log(`Width: ${window.innerWidth}, Height: ${window.innerHeight}`);
  }
  
  window.addEventListener('resize', () => {
    updateElementVisibility();
    logWindowSize();
  });
  
  // Initial setup
  updateElementVisibility();
  logWindowSize();
  
