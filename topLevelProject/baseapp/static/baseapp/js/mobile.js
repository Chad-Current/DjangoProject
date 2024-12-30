const openButton = document.getElementById('open-sidebar-button');
const navbar = document.getElementById('navbar');
const media = window.matchMedia("(max-width: 700px)");
const dropdown = document.querySelector('.dropdown');
const classes = document.querySelector('.classes');

media.addEventListener('change', (e) => updateNavbar(e));

function updateNavbar(e) {
  const isMobile = e.matches;
  console.log(isMobile);
  if (isMobile) {
    navbar.setAttribute('inert', '');
    hideDropdown();
  } else {
    // desktop device
    navbar.removeAttribute('inert');
    showDropdown();
  }
}

function openSidebar() {
  navbar.classList.add('show');
  openButton.setAttribute('aria-expanded', 'true');
  navbar.removeAttribute('inert');
}

function closeSidebar() {
  navbar.classList.remove('show');
  openButton.setAttribute('aria-expanded', 'false');
  navbar.setAttribute('inert', '');
}

function hideDropdown() {
  dropdown.style.display = 'none';
  classes.style.display = 'block';
  // dropdownContent.style.display = 'none';
}

function showDropdown() {
  dropdown.style.display = 'block';
  classes.style.display = 'none';
  // dropdownContent.style.display = 'block';
}


// For Bookmark Links
// const navLinks = document.querySelectorAll('nav a')
// navLinks.forEach(link => {
//   link.addEventListener('click', () => {
//     closeSidebar()
//   })
// })

updateNavbar(media)