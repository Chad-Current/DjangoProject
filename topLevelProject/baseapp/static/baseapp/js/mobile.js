const openButton = document.getElementById('open-sidebar-button');
const navbar = document.getElementById('navbar');
const media = window.matchMedia("(max-width: 780px)");
const dropdown = document.querySelector('.dropdown');
const classes = document.querySelector('.classes');
const margin_left = document.querySelector('.marginLeft');
const siteTitle = document.getElementById('site-title');
// const sectionTwo = document.querySelector('.section_two');
// const sectionTwoMobile = document.querySelector('.section_two_mobile');
media.addEventListener('change', (e) => updateNavbar(e));

function updateNavbar(e) {
  const isMobile = e.matches;
  console.log(isMobile);
  if (isMobile) {
    navbar.setAttribute('inert', '');
    siteTitle.style.display = 'none'; 
    margin_left.classList.remove('marginLeft');
    // sectionTwoMobile.style.display = 'block';
    hideDropdown();
  } else {
    // desktop device
    navbar.removeAttribute('inert');
    siteTitle.style.display = 'block'; 
    margin_left.classList.add('marginLeft');
    // sectionTwo.style.display = 'block';
    // sectionTwoMobile.style.display = 'none';
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