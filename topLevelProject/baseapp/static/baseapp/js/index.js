const infograph = document.querySelector('.infographic-container');
const infograph_mobile = document.querySelector('.infographic-container-mobile');
const compchart = document.querySelector('.comp-chart');
const compchart_mobile = document.querySelector('.comp-chart-mobile');

function removeInfograph(){
    if (window.innerWidth <= 768){
        infograph.style.display = "none";
    } else {
        infograph.style.display = "grid";
    }
}

function removeInfographMobile() {
    if (window.innerWidth <= 768) {
        infograph_mobile.style.display = "flex";
    } else {
        infograph_mobile.style.display = "none";
    }
}

function removeCompchart(){
    if (window.innerWidth <= 768) {
        compchart.style.display = "none";
    } else {
        compchart.style.display = "flex";
    }
}

function removeCompchartMobile(){
    if (window.innerWidth <= 768) {
        compchart_mobile.style.display = "flex";
    } else {
        compchart_mobile.style.display = "none";
    }
}



window.addEventListener("resize",function() { 
    removeInfograph();
    removeInfographMobile();
    removeCompchart();
    removeCompchartMobile();
});
// window.addEventListener("resize", removeInfograph);
// window.addEventListener("resize", removeCompchart);