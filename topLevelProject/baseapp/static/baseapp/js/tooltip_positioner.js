/* tooltip_positioner.js
   Positions .ob-tip bubbles for every .ob-label-tooltip on the page.
   Loaded globally via base_dashboard.html.

   Supports two positioning modes — determined at runtime by the tip's
   computed CSS position:

     position:fixed  (tooltip_styles.css)      — used on contact forms
       Coordinates are viewport-relative.

     position:absolute (onboarding_tooltips.css) — used on onboarding pages
       Coordinates are relative to the wrapper (.ob-label-tooltip has
       position:relative).  Immune to transform-based containing blocks
       created by the .ob-in animation on .onboarding-main.            */

(function () {
  'use strict';

  const GAP = 10; // px gap between label edge and bubble

  function positionTip(wrapper, tip) {
    const tipW = tip.offsetWidth;
    const tipH = tip.offsetHeight;
    const rect  = wrapper.getBoundingClientRect();
    const isAbsolute = window.getComputedStyle(tip).position === 'absolute';

    let top, left;

    if (isAbsolute) {
      // Coordinates are relative to the wrapper (position:relative)
      top  = -tipH - GAP;
      left = 0;

      // Flip below if the bubble would clip the top of the viewport
      if (rect.top + top < 8) {
        top = wrapper.offsetHeight + GAP;
      }

      // Pull left if the bubble would overflow the right viewport edge
      const overflowRight = rect.left + left + tipW - (window.innerWidth - 8);
      if (overflowRight > 0) { left -= overflowRight; }

      // Never go off the left viewport edge
      if (rect.left + left < 8) { left = 8 - rect.left; }

    } else {
      // position:fixed — coordinates are viewport-relative
      top  = rect.top - tipH - GAP;
      left = rect.left;

      // Flip below if it would clip the top of the viewport
      if (top < 8) { top = rect.bottom + GAP; }

      // Pull left if the bubble would overflow the right viewport edge
      const overflowRight = left + tipW - (window.innerWidth - 8);
      if (overflowRight > 0) { left -= overflowRight; }

      // Never go off the left edge
      if (left < 8) left = 8;
    }

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
