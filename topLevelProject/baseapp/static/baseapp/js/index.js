const infograph = document.querySelector('.infographic-container');
const compchart = document.querySelector('.comp-chart');


function removeInfograph(){
    if (window.innerWidth <= 780) {
        infograph.style.display = "none";
    } else {
        infograph.style.display = "grid";
    }
}


function removeCompchart(){
    if (window.innerWidth <= 780) {
        compchart.style.display = "none";
    } else {
        compchart.style.display = "flex";
    }
}


// removeInfograph();
// removeCompchart();

window.addEventListener("resize",function() { 
    removeInfograph();
    removeCompchart();
});
// window.addEventListener("resize", removeInfograph);
// window.addEventListener("resize", removeCompchart);