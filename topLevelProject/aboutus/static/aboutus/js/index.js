document.querySelectorAll('.toggle-img').forEach(img => {
  const targetId = img.dataset.target;  // e.g. "p1"
  const targetP = document.getElementById(targetId);

  if (!targetP) return;

  // Show paragraph on hover enter
  img.addEventListener('mouseenter', () => {
    // Hide all paragraphs first
    document.querySelectorAll('.info').forEach(p => {
      p.classList.remove('active');
    });
    
    // Show only the targeted one
    targetP.classList.add('active');
  });

  // Hide when mouse leaves image
  img.addEventListener('mouseleave', () => {
    targetP.classList.remove('active');
  });
});
