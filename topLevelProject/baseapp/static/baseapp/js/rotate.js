
document.addEventListener("DOMContentLoaded", function () {
const targets = document.querySelectorAll(".scroll-circle-target");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
          } else {
            // remove if you only want the circle while it's in view
            entry.target.classList.remove("in-view");
          }
        });
      },
      {
        root: null,        // viewport
        threshold: 0.4     // trigger when ~40% visible
      }
    );

    targets.forEach((el) => observer.observe(el));
  });

