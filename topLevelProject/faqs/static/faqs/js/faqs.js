const icon = document.querySelector(".icon-img");
var acc = document.getElementsByClassName("accordion");
var i;

for (i = 0; i < acc.length; i++) {
  acc[i].addEventListener("click", function() {
    this.classList.toggle("active");

    var panel = this.nextElementSibling;
    if (panel.style.maxHeight) {
      panel.style.maxHeight = null;
      icon.style.transform = "rotate(45deg)";
      icon.style.width = "4em";
    } else {
      panel.style.maxHeight = panel.scrollHeight + "px";
      icon.style.transform = "rotate(0deg)";
      icon.style.width = "3em";
    } 
  });
}