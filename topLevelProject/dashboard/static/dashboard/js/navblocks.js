document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const subnavItems = document.querySelectorAll('.subnav-item');
    
    subnavItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
            item.setAttribute('aria-current', 'page');
        }
    });

    // Smooth scroll active item into view on mobile
    const activeItem = document.querySelector('.subnav-item.active');
    if (activeItem && window.innerWidth <= 780) {
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
});
