(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  // Keep in sync with css/ux-improvements.css `pageExitContent` and `pageExitOverlay` durations.
  const PAGE_EXIT_DURATION_MS = 460;

  function startEnterAnimation(body) {
    // Remove the class first and force a reflow so that re-adding it restarts the animation.
    // This is critical for bfcache restores where the class may already be present.
    body.classList.remove('page-entering');
    // eslint-disable-next-line no-unused-expressions
    body.offsetWidth; // force reflow
    body.classList.add('page-entering');

    // Clean up the class once the animation finishes so it doesn't linger on the element.
    body.addEventListener('animationend', () => {
      body.classList.remove('page-entering');
    }, { once: true });
  }

  function init() {
    const body = document.body;
    if (!body) return;

    if (!prefersReducedMotion.matches) {
      startEnterAnimation(body);
    }

    // Re-run enter animation on bfcache restores (back/forward navigation)
    window.addEventListener('pageshow', (e) => {
      body.classList.remove('page-transitioning');
      if (!prefersReducedMotion.matches) {
        startEnterAnimation(body);
      }
    });

    const isNavigableLink = (anchor) => {
      if (!anchor || !anchor.href) return false;
      if (anchor.target && anchor.target !== '_self') return false;
      if (anchor.hasAttribute('download')) return false;
      if (anchor.getAttribute('rel') === 'external') return false;
      if (anchor.dataset.noTransition === 'true') return false;

      const href = (anchor.getAttribute('href') || '').trim();
      if (!href || href.startsWith('#')) return false;

      let url;
      try {
        url = new URL(href, window.location.href);
      } catch (_) {
        return false;
      }
      if (!['http:', 'https:'].includes(url.protocol)) return false;
      if (url.origin !== window.location.origin) return false;

      const samePath = url.pathname === window.location.pathname;
      if (samePath && url.hash) return false;

      return true;
    };

    document.addEventListener('click', (event) => {
      if (prefersReducedMotion.matches || body.classList.contains('page-transitioning')) return;
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = event.target.closest('a[href]');
      if (!isNavigableLink(anchor)) return;

      event.preventDefault();
      body.classList.add('page-transitioning');

      setTimeout(() => {
        window.location.assign(anchor.href);
      }, PAGE_EXIT_DURATION_MS);
    }, { capture: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
