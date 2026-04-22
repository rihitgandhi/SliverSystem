(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const body = document.body;
  const PAGE_EXIT_DURATION_MS = 460;

  if (!body) return;

  if (!prefersReducedMotion.matches) {
    body.classList.add('page-entering');
    requestAnimationFrame(() => body.classList.add('page-entering-active'));
    window.addEventListener('pageshow', () => {
      body.classList.remove('page-transitioning');
      body.classList.add('page-entering');
      requestAnimationFrame(() => body.classList.add('page-entering-active'));
    });
  }

  const isNavigableLink = (anchor) => {
    if (!anchor || !anchor.href) return false;
    if (anchor.target && anchor.target !== '_self') return false;
    if (anchor.hasAttribute('download')) return false;
    if (anchor.getAttribute('rel') === 'external') return false;
    if (anchor.dataset.noTransition === 'true') return false;

    const href = (anchor.getAttribute('href') || '').trim();
    if (!href || href.startsWith('#')) return false;

    const url = new URL(href, window.location.href);
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
})();
