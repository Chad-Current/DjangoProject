  const orbits = document.querySelectorAll('.image-orbit');
  const totalImages = orbits.length;
  const circle = document.getElementById('circle');
  const sectionTwo = document.getElementById('section_two');

  // Position icons around the circle
  orbits.forEach((orbit, i) => {
    const angle = (360 / totalImages) * i;
    orbit.style.transform = `rotate(${angle}deg)`;
  });

  // Observe section_two visibility
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        circle.classList.add('visible');
        sectionTwo.classList.add('visible');
      } else {
        circle.classList.remove('visible');
        sectionTwo.classList.remove('visible');
      }
    });
  }, { threshold: 0.4 });

  observer.observe(sectionTwo);