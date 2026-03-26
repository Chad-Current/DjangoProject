/* tooltip_positioner.js
   Positions .ob-tip bubbles for every .ob-label-tooltip on the page.
   Loaded globally via base_dashboard.html so all dashboard pages — including
   onboarding steps — get tooltip support without per-template JS blocks.    */

(function () {
  'use strict';

  const GAP = 10; // px gap between label top-edge and bubble bottom

  function positionTip(wrapper, tip) {
    const rect = wrapper.getBoundingClientRect();
    const tipW = tip.offsetWidth;
    const tipH = tip.offsetHeight;

    // Default: above the label, left-aligned to it
    let top  = rect.top - tipH - GAP;
    let left = rect.left;

    // Flip below if it would clip the top of the viewport
    if (top < 8) {
      top = rect.bottom + GAP;
    }

    // Pull left if the bubble would overflow the right viewport edge
    const overflowRight = left + tipW - (window.innerWidth - 8);
    if (overflowRight > 0) {
      left -= overflowRight;
    }

    // Never go off the left edge
    if (left < 8) left = 8;

    tip.style.top  = top  + 'px';
    tip.style.left = left + 'px';
  }

  function initTooltips() {
    document.querySelectorAll('.ob-label-tooltip').forEach(function (wrapper) {
      const tip = wrapper.querySelector('.ob-tip');
      if (!tip) return;

      function show() {
        positionTip(wrapper, tip);
        tip.classList.add('ob-tip--visible');
      }

      function hide() {
        tip.classList.remove('ob-tip--visible');
        tip.style.top  = '-9999px';
        tip.style.left = '-9999px';
      }

      wrapper.addEventListener('mouseenter', show);
      wrapper.addEventListener('mouseleave', hide);

      // Keyboard focus — skip checkbox rows (focus-within conflicts with click)
      if (!wrapper.classList.contains('ob-check-row')) {
        wrapper.addEventListener('focusin',  show);
        wrapper.addEventListener('focusout', hide);
      }

      // Keep position accurate if page scrolls while tip is open
      window.addEventListener('scroll', function () {
        if (tip.classList.contains('ob-tip--visible')) positionTip(wrapper, tip);
      }, { passive: true });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTooltips);
  } else {
    initTooltips();
  }
})();
