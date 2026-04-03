document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.faq-item').forEach(details => {
        const summary = details.querySelector('summary');
        const answer  = details.querySelector('.faq-answer');

        summary.addEventListener('click', e => {
            e.preventDefault();

            // Cancel any in-flight animation before starting a new one
            answer.getAnimations().forEach(a => a.cancel());

            if (details.open) {
                // Collapse: read current rendered height (may be mid-animation), animate to 0
                answer.animate(
                    [{ height: answer.offsetHeight + 'px' }, { height: '0' }],
                    { duration: 280, easing: 'ease-in-out', fill: 'forwards' }
                ).onfinish = function () {
                    this.cancel();
                    details.removeAttribute('open');
                };
            } else {
                // Expand: set [open] so browser renders the content, measure, animate from 0
                details.setAttribute('open', '');
                const targetH = answer.scrollHeight;
                answer.animate(
                    [{ height: '0' }, { height: targetH + 'px' }],
                    { duration: 280, easing: 'ease-in-out', fill: 'forwards' }
                ).onfinish = function () {
                    // Release fixed height so auto-height takes over (safe for window resize)
                    this.cancel();
                };
            }
        });
    });
});
