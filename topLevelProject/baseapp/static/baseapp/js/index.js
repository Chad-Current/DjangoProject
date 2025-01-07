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
  
  
// const infograph = document.querySelector('.infographic-container');
// const infograph_mobile = document.querySelector('.infographic-container-mobile');
// const compchart = document.querySelector('.comp-chart');
// const compchart_mobile = document.querySelector('.comp-chart-mobile');
// var active_mobile = false;

// function removeInfograph(){
//     if (window.innerWidth <= 468){
//         infograph.style.display = "none";
//     } else {
//         infograph.style.display = "grid";
//     }
// }

// function removeInfographMobile() {
//     if (window.innerWidth > 468) {
//         infograph_mobile.style.display = "none";
//     } else {
//         infograph_mobile.style.display = "flex";
//     }
// }

// function removeCompchart(){
//     if (window.innerWidth <= 468) {
//         compchart.style.display = "none";
//     } else {
//         compchart.style.display = "flex";
//     }
// }

// function removeCompchartMobile(){
//     if (window.innerWidth > 468) {
//         compchart_mobile.style.display = "none";
//     } else {
//         compchart_mobile.style.display = "flex";
//     }
// }

// console.log(window.innerWidth)
// console.log(window.innerHeight)

// window.addEventListener("resize", function() { 
//     if (!active_mobile){
//         removeInfograph();
//         removeCompchart();
//     } else {
//         removeInfographMobile();
//         removeCompchartMobile();
//     }
//     console.log(window.innerWidth)
//     console.log(window.innerHeight)
// });
// window.addEventListener("resize", removeInfograph);
// window.addEventListener("resize", removeCompchart);