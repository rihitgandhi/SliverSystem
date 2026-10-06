(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const PAGE_EXIT_DURATION_MS = 240;
  let lenis = null;

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
    const sectionSelector = [
      '.home-screen',
      '.sell-section',
      '.learn-section',
      '.learn-stat-section',
      '.checker-hero',
      '.checker-input-section',
      '.checker-results-section',
      '.mission-article > section',
      '.screen',
      '.single-screen'
    ].join(', ');
    const sectionItems = Array.from(document.querySelectorAll(sectionSelector));
    const fallbackItems = Array.from(document.querySelectorAll('.reveal'));
    const items = sectionItems.length ? sectionItems : fallbackItems;
    if (!items.length) return;

    if (prefersReducedMotion.matches || !('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('in-view'));
      fallbackItems.forEach((item) => item.classList.add('in-view'));
      return;
    }

    items.forEach((item) => item.classList.add('scroll-reveal'));

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      });
    }, {
      rootMargin: '0px 0px -18% 0px',
      threshold: 0.22
    });

    items.forEach((item) => observer.observe(item));
    fallbackItems.forEach((item) => item.classList.add('in-view'));
  }

  function initSmoothScroll() {
    if (prefersReducedMotion.matches || typeof window.Lenis !== 'function') return;

    lenis = new window.Lenis({
      autoRaf: true,
      duration: 1.08,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 0.92,
      touchMultiplier: 1,
      anchors: {
        offset: -8,
        duration: 1
      }
    });

    window.accessAILenis = lenis;

    document.addEventListener('click', (event) => {
      if (!lenis || event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const anchor = event.target.closest('a[href^="#"]');
      if (!anchor) return;

      const href = anchor.getAttribute('href');
      if (!href || href === '#') return;

      const target = document.querySelector(href);
      if (!target) return;

      event.preventDefault();
      lenis.scrollTo(target, {
        offset: -8,
        duration: 1,
        easing: (t) => 1 - Math.pow(1 - t, 3)
      });
    });
  }

  function initCountUp() {
    const items = Array.from(document.querySelectorAll('[data-count-to]'));
    if (!items.length) return;

    const setFinalValues = () => {
      items.forEach((item) => {
        const target = Number(item.dataset.countTo);
        const decimals = Number(item.dataset.countDecimals || 0);
        const prefix = item.dataset.countPrefix || '';
        const suffix = item.dataset.countSuffix || '';
        item.textContent = `${prefix}${target.toFixed(decimals)}${suffix}`;
      });
    };

    if (prefersReducedMotion.matches || !('IntersectionObserver' in window)) {
      setFinalValues();
      return;
    }

    const formatValue = (item, value, isFinal) => {
      const target = Number(item.dataset.countTo);
      const decimals = Number(item.dataset.countDecimals || 0);
      const prefix = item.dataset.countPrefix || '';
      const suffix = item.dataset.countSuffix || '';
      const displayValue = isFinal ? target : value;
      return `${prefix}${displayValue.toFixed(decimals)}${suffix}`;
    };

    const animate = (item) => {
      const target = Number(item.dataset.countTo);
      if (!Number.isFinite(target)) return;

      const duration = 1350;
      const start = performance.now();

      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;
        item.textContent = formatValue(item, value, progress === 1);

        if (progress < 1) {
          requestAnimationFrame(step);
        }
      };

      item.textContent = formatValue(item, 0, false);
      requestAnimationFrame(step);
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        items.forEach(animate);
        observer.disconnect();
      });
    }, {
      rootMargin: '0px 0px -20% 0px',
      threshold: 0.28
    });

    const section = document.querySelector('.home-learn-screen') || items[0];
    observer.observe(section);
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
    initSmoothScroll();
    initReveal();
    initCountUp();
    initPageTransitions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
