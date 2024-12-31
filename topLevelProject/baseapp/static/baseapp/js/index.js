const infograph = document.querySelector('.infographic-container');
const infoheader = document.querySelector(".infograph-header");

function removeInfograph(){
    if (window.innerWidth <= 780) {
        infograph.style.display = "none";
    } else {
        infograph.style.display = "grid";
    }
}

removeInfograph();

window.addEventListener("resize", removeInfograph);