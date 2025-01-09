
var acc = document.getElementsByClassName("accordion");
var i, j;

for (i = 0; i < acc.length; i++) {
  acc[i].addEventListener("click", function() {
    this.classList.toggle("active");

    var panel = this.nextElementSibling;
    var icon = this.querySelector(".icon-img"); // Get the icon for this specific accordion
    if (panel.style.maxHeight) {
      panel.style.maxHeight = null;
      icon.style.transform = "rotate(0deg)";

    } else {
      panel.style.maxHeight = panel.scrollHeight + "px";
      icon.style.transform = "rotate(45deg)";

    } 
  });
}

