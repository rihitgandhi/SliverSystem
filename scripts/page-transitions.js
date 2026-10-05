(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const PAGE_EXIT_DURATION_MS = 240;

  function initMenu() {
    const button = document.querySelector('.menu-toggle');
    const menu = document.getElementById('nav-menu');
    if (!button || !menu) return;

    const close = () => {
      button.setAttribute('aria-expanded', 'false');
      menu.classList.remove('is-open');
      document.body.classList.remove('nav-open');
    };

    button.addEventListener('click', () => {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!expanded));
      menu.classList.toggle('is-open', !expanded);
      document.body.classList.toggle('nav-open', !expanded);
    });

    menu.addEventListener('click', (event) => {
      if (event.target.closest('a')) close();
    });

    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close();
    });
  }

  function initReveal() {
    const items = Array.from(document.querySelectorAll('.reveal'));
    if (!items.length) return;

    if (prefersReducedMotion.matches || !('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('in-view'));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      });
    }, {
      rootMargin: '0px 0px -12% 0px',
      threshold: 0.14
    });

    items.forEach((item) => observer.observe(item));
  }

  function initPageTransitions() {
    const body = document.body;
    if (!body || prefersReducedMotion.matches) return;

    body.classList.add('page-entering');
    window.addEventListener('pageshow', () => {
      body.classList.remove('page-transitioning');
      body.removeAttribute('aria-busy');
      body.classList.add('page-entering');
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
      if (url.pathname === window.location.pathname && url.hash) return false;

      return true;
    };

    document.addEventListener('click', (event) => {
      if (body.classList.contains('page-transitioning')) return;
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = event.target.closest('a[href]');
      if (!isNavigableLink(anchor)) return;

      event.preventDefault();
      body.classList.add('page-transitioning');
      body.setAttribute('aria-busy', 'true');

      setTimeout(() => {
        window.location.assign(anchor.href);
      }, PAGE_EXIT_DURATION_MS);
    }, { capture: true });
  }

  function init() {
    initMenu();
    initReveal();
    initPageTransitions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
