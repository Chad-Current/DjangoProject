const track = document.querySelector('.carousel-track');
const slides = Array.from(document.querySelectorAll('.carousel-slide'));
const nextButton = document.querySelector('.carousel-btn.next');
const prevButton = document.querySelector('.carousel-btn.prev');
const dotsNav = document.querySelector('.carousel-dots');
const dots = Array.from(document.querySelectorAll('.carousel-dot'));

const slideWidth = slides[0].getBoundingClientRect().width;

// Arrange slides next to each other
slides.forEach((slide, index) => {
  slide.style.left = slideWidth * index + 'px';
});

const moveToSlide = (track, currentSlide, targetSlide) => {
  track.style.transform = 'translateX(-' + targetSlide.style.left + ')';
  currentSlide.classList.remove('current-slide');
  currentSlide.setAttribute('aria-hidden', 'true');
  targetSlide.classList.add('current-slide');
  targetSlide.setAttribute('aria-hidden', 'false');
};

const updateDots = (currentDot, targetDot) => {
  currentDot.classList.remove('current-dot');
  currentDot.setAttribute('aria-selected', 'false');
  targetDot.classList.add('current-dot');
  targetDot.setAttribute('aria-selected', 'true');
};

const getSlideIndex = (slide) => slides.indexOf(slide);

// Click right
nextButton.addEventListener('click', () => {
  const currentSlide = document.querySelector('.carousel-slide.current-slide');
  const currentIndex = getSlideIndex(currentSlide);
  const nextIndex = (currentIndex + 1) % slides.length;
  const nextSlide = slides[nextIndex];

  const currentDot = document.querySelector('.carousel-dot.current-dot');
  const nextDot = dots[nextIndex];

  moveToSlide(track, currentSlide, nextSlide);
  updateDots(currentDot, nextDot);
});

// Click left
prevButton.addEventListener('click', () => {
  const currentSlide = document.querySelector('.carousel-slide.current-slide');
  const currentIndex = getSlideIndex(currentSlide);
  const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
  const prevSlide = slides[prevIndex];

  const currentDot = document.querySelector('.carousel-dot.current-dot');
  const prevDot = dots[prevIndex];

  moveToSlide(track, currentSlide, prevSlide);
  updateDots(currentDot, prevDot);
});

// Click dots
dotsNav.addEventListener('click', (e) => {
  const targetDot = e.target.closest('button');
  if (!targetDot) return;

  const currentSlide = document.querySelector('.carousel-slide.current-slide');
  const currentDot = document.querySelector('.carousel-dot.current-dot');
  const targetIndex = dots.indexOf(targetDot);
  const targetSlide = slides[targetIndex];

  moveToSlide(track, currentSlide, targetSlide);
  updateDots(currentDot, targetDot);
});