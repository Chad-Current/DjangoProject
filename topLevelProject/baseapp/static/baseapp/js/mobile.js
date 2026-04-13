/* mobile.js
   openSidebar() and closeSidebar() are defined inline in navbar.html
   so they are available immediately on page load regardless of this
   file's load timing. This file only adds enhancement listeners.
*/

/* Close sidebar on Escape key */
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && document.body.classList.contains('nav-open')) {
    closeSidebar();
  }
});

/* Close sidebar when any link inside it is tapped on mobile */
(function () {
  var navbar = document.getElementById('navbar');
  if (!navbar) return;
  navbar.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      if (window.innerWidth <= 780) closeSidebar();
    });
  });
}());