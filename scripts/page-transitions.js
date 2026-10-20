(() => {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const PAGE_EXIT_DURATION_MS = 240;
  let lenis = null;

  const shouldReduceMotion = () => (
    prefersReducedMotion.matches || document.documentElement.dataset.a11yMotion === 'reduce'
  );

  const onSystemMotionChange = (listener) => {
    if (typeof prefersReducedMotion.addEventListener === 'function') {
      prefersReducedMotion.addEventListener('change', listener);
    } else if (typeof prefersReducedMotion.addListener === 'function') {
      prefersReducedMotion.addListener(listener);
    }
  };

  function initSkipLink() {
    const link = document.querySelector('.skip-link[href^="#"]');
    if (!link) return;

    link.addEventListener('click', (event) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (!target) return;

      event.preventDefault();
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: 'start', behavior: 'auto' });
      window.history.pushState(null, '', link.getAttribute('href'));
    });
  }

  function initMenu() {
    const button = document.querySelector('.menu-toggle');
    const menu = document.getElementById('nav-menu');
    const nav = button?.closest('nav');
    if (!button || !menu) return;

    const close = (returnFocus = false) => {
      if (button.getAttribute('aria-expanded') !== 'true') return;
      button.setAttribute('aria-expanded', 'false');
      menu.classList.remove('is-open');
      document.body.classList.remove('nav-open');
      if (returnFocus) button.focus();
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

    nav?.addEventListener('focusout', (event) => {
      if (event.relatedTarget && !nav.contains(event.relatedTarget)) close();
    });

    document.addEventListener('pointerdown', (event) => {
      if (nav && !nav.contains(event.target)) close();
    });

    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') close(true);
    });

    window.addEventListener('resize', () => {
      if (window.matchMedia('(min-width: 1101px)').matches) close();
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

    if (shouldReduceMotion() || !('IntersectionObserver' in window)) {
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
    if (sectionItems.length) {
      fallbackItems.forEach((item) => item.classList.add('in-view'));
    }

    document.addEventListener('accessai:settingschange', (event) => {
      if (!event.detail || !event.detail.reducedMotion) return;
      items.forEach((item) => item.classList.add('in-view'));
      fallbackItems.forEach((item) => item.classList.add('in-view'));
      observer.disconnect();
    });
  }

  function initSmoothScroll() {
    if (typeof window.Lenis !== 'function') return;

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

    const syncMotion = () => {
      if (!lenis) return;
      if (shouldReduceMotion() && typeof lenis.stop === 'function') {
        lenis.stop();
      } else if (!shouldReduceMotion() && typeof lenis.start === 'function') {
        lenis.start();
      }
    };

    document.addEventListener('accessai:settingschange', syncMotion);
    onSystemMotionChange(syncMotion);
    syncMotion();

    document.addEventListener('click', (event) => {
      if (!lenis || shouldReduceMotion() || event.defaultPrevented || event.button !== 0) return;
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

    if (shouldReduceMotion() || !('IntersectionObserver' in window)) {
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

    document.addEventListener('accessai:settingschange', (event) => {
      if (!event.detail || !event.detail.reducedMotion) return;
      setFinalValues();
      observer.disconnect();
    });
  }

  function initPageTransitions() {
    const body = document.body;
    if (!body) return;

    if (!shouldReduceMotion()) body.classList.add('page-entering');
    window.addEventListener('pageshow', () => {
      body.classList.remove('page-transitioning');
      body.removeAttribute('aria-busy');
      body.classList.toggle('page-entering', !shouldReduceMotion());
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
      if (shouldReduceMotion()) return;
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

  function initSecondBrainWalkthrough() {
    const walkthrough = document.querySelector('.sbw-walkthrough');
    if (!walkthrough) return;

    const stage = walkthrough.querySelector('.sbw-stage');
    const playback = walkthrough.querySelector('.sbw-playback');
    const popup = walkthrough.querySelector('.sbw-popup');
    const toolbarIcon = walkthrough.querySelector('.sbw-toolbar-icon');
    const address = walkthrough.querySelector('.sbw-address');
    const hostHint = walkthrough.querySelector('.sbw-host-hint');
    const siteA = walkthrough.querySelector('.sbw-site-a');
    const siteB = walkthrough.querySelector('.sbw-site-b');
    const siteBPage = walkthrough.querySelector('.sbw-site-b-page');
    const tabA = walkthrough.querySelector('.sbw-tab-a');
    const tabB = walkthrough.querySelector('.sbw-tab-b');
    const caption = walkthrough.querySelector('.sbw-caption');
    const voicePanel = walkthrough.querySelector('.sbw-voice-panel');
    const voiceTranscript = walkthrough.querySelector('.sbw-voice-transcript');
    const voiceMessage = walkthrough.querySelector('.sbw-voice-message');
    const textValue = walkthrough.querySelector('.sbw-text-value');
    const sliderFill = walkthrough.querySelector('.sbw-slider-fill');
    const sliderThumb = walkthrough.querySelector('.sbw-slider-thumb');
    const reduceToggle = walkthrough.querySelector('[data-setting="reduce"]');
    const highlightToggle = walkthrough.querySelector('[data-setting="highlight"]');
    const contrastToggle = walkthrough.querySelector('[data-setting="contrast"]');
    const voiceToggle = walkthrough.querySelector('[data-setting="voice"]');
    const siteBButton = siteB.querySelector('button');
    const cursor = walkthrough.querySelector('.sbw-cursor');
    const ripple = walkthrough.querySelector('.sbw-click-ripple');
    const duration = 18000;
    const reducedAtLoad = shouldReduceMotion();
    let elapsed = 0;
    let lastFrame = 0;
    let inView = false;
    let userPaused = reducedAtLoad;
    let showReducedStatic = reducedAtLoad;
    let pausedBeforeReducedMotion = false;

    const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
    const easeInOut = (value) => {
      const t = clamp(value);
      return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    };
    const easeOut = (value) => 1 - Math.pow(1 - clamp(value), 3);
    const between = (time, start, end) => clamp((time - start) / (end - start));
    const setToggle = (element, on, pressed = false) => {
      element.classList.toggle('is-on', on);
      element.classList.toggle('is-pressed', pressed);
    };
    const setPlaybackState = () => {
      const paused = userPaused || showReducedStatic;
      playback.classList.toggle('is-paused', paused);
      playback.setAttribute('aria-label', paused ? 'Play walkthrough' : 'Pause walkthrough');
    };

    const cursorFrames = [
      [0, 58, 30],
      [1200, 70, 17],
      [2100, 95.5, 9.2],
      [2850, 68.2, 22.1],
      [5000, 94.2, 22.1],
      [5600, 94.2, 27.3],
      [6300, 94.2, 31.5],
      [7000, 94.2, 39.9],
      [7700, 51, 48],
      [9000, 45, 3.2],
      [10500, 62, 23]
    ];

    function cursorPosition(time) {
      if (time <= cursorFrames[0][0]) return cursorFrames[0].slice(1);
      for (let index = 1; index < cursorFrames.length; index += 1) {
        const previous = cursorFrames[index - 1];
        const next = cursorFrames[index];
        if (time > next[0]) continue;
        const progress = easeInOut((time - previous[0]) / (next[0] - previous[0]));
        const arc = Math.sin(progress * Math.PI) * (index % 2 ? -2.6 : 2.2);
        return [
          previous[1] + (next[1] - previous[1]) * progress,
          previous[2] + (next[2] - previous[2]) * progress + arc
        ];
      }
      return cursorFrames[cursorFrames.length - 1].slice(1);
    }

    function setRipple(time) {
      const clickTimes = [2100, 5600, 6300, 7000, 7700, 9000];
      let active = null;
      for (const clickTime of clickTimes) {
        if (time >= clickTime && time <= clickTime + 400) active = clickTime;
      }

      let x;
      let y;
      let progress;
      if (time >= 14400 && time <= 14800) {
        x = 50;
        y = 39;
        progress = (time - 14400) / 400;
      } else if (active !== null) {
        [x, y] = cursorPosition(active);
        progress = (time - active) / 400;
      } else {
        ripple.style.opacity = '0';
        return;
      }

      ripple.style.transform = `translate(${x}cqi, ${y}cqi) translate(-50%, -50%) scale(${progress})`;
      ripple.style.opacity = String(1 - progress);
    }

    function setSite(site, active, scale, highlighted) {
      site.classList.toggle('is-active', active);
      site.classList.toggle('has-highlights', highlighted);
      site.style.setProperty('--text-scale', String(scale / 100));
    }

    function renderStaticFrame() {
      stage.style.opacity = '1';
      popup.style.opacity = '0';
      popup.style.transform = 'translateY(-0.6cqi) scale(0.98)';
      toolbarIcon.classList.remove('is-pressed');
      address.textContent = 'another-site.org';
      hostHint.textContent = 'another-site.org';
      tabA.classList.remove('is-active');
      tabB.classList.add('is-active');
      setSite(siteA, false, 177, true);
      setSite(siteB, true, 177, true);
      siteBPage.style.transform = 'translateY(0)';
      caption.style.opacity = '0';
      caption.style.transform = 'translateY(0.8cqi)';
      voicePanel.style.opacity = '0';
      voicePanel.style.transform = 'translateY(3cqi)';
      voiceTranscript.textContent = '';
      voiceMessage.textContent = '';
      textValue.textContent = '177%';
      sliderFill.style.width = '80.83%';
      sliderThumb.style.left = '80.83%';
      setToggle(reduceToggle, true);
      setToggle(highlightToggle, true);
      setToggle(contrastToggle, false);
      setToggle(voiceToggle, false);
      siteBButton.classList.remove('is-pressed');
      cursor.style.opacity = '0';
      ripple.style.opacity = '0';
    }

    function render(time) {
      if (showReducedStatic) {
        renderStaticFrame();
        return;
      }

      const fadeIn = easeOut(between(time, 0, 1200));
      const fadeOut = 1 - easeInOut(between(time, 17600, 18000));
      stage.style.opacity = String(Math.min(fadeIn, fadeOut));

      const sliderProgress = easeInOut(between(time, 2800, 5000));
      const currentTextSize = Math.round(100 + 77 * sliderProgress);
      const sliderPercent = ((currentTextSize - 80) / 120) * 100;
      textValue.textContent = `${currentTextSize}%`;
      sliderFill.style.width = `${sliderPercent}%`;
      sliderThumb.style.left = `${sliderPercent}%`;

      const popupOpen = time >= 2100 && time < 7700;
      popup.style.opacity = popupOpen ? '1' : '0';
      popup.style.transform = popupOpen ? 'translateY(0) scale(1)' : 'translateY(-0.6cqi) scale(0.98)';
      toolbarIcon.classList.toggle('is-pressed', time >= 2100 && time < 2220);

      const reduceOn = time >= 5600;
      const highlightOn = time >= 6300;
      const voiceOn = time >= 7000;
      setToggle(reduceToggle, reduceOn, time >= 5600 && time < 5720);
      setToggle(highlightToggle, highlightOn, time >= 6300 && time < 6420);
      setToggle(contrastToggle, false);
      setToggle(voiceToggle, voiceOn, time >= 7000 && time < 7120);

      const showingSiteB = time >= 9000;
      address.textContent = showingSiteB ? 'another-site.org' : 'example.com';
      hostHint.textContent = showingSiteB ? 'another-site.org' : 'example.com';
      tabA.classList.toggle('is-active', !showingSiteB);
      tabB.classList.toggle('is-active', showingSiteB);
      setSite(siteA, !showingSiteB, currentTextSize, highlightOn);
      setSite(siteB, showingSiteB, currentTextSize, highlightOn);

      const captionVisible = time >= 9300 && time < 11400;
      caption.style.opacity = captionVisible ? '1' : '0';
      caption.style.transform = captionVisible ? 'translateY(0)' : 'translateY(0.8cqi)';

      const voiceVisible = voiceOn;
      voicePanel.style.opacity = voiceVisible ? '1' : '0';
      voicePanel.style.transform = voiceVisible ? 'translateY(0)' : 'translateY(3cqi)';

      let transcript = '';
      if (time >= 12000 && time < 13900) {
        const letters = Math.ceil('scroll down'.length * between(time, 12000, 12500));
        transcript = 'scroll down'.slice(0, letters);
      } else if (time >= 13900) {
        const letters = Math.ceil('click sample button'.length * between(time, 13900, 14400));
        transcript = 'click sample button'.slice(0, letters);
      }
      voiceTranscript.textContent = transcript;
      voiceMessage.textContent = time >= 14400 ? 'Clicked "Sample button"' : '';

      const scrollProgress = easeOut(between(time, 12500, 13100));
      siteBPage.style.transform = `translateY(${-38 * scrollProgress}cqi)`;
      siteBButton.classList.toggle('is-pressed', time >= 14400 && time < 14750);

      const [cursorX, cursorY] = cursorPosition(time);
      cursor.style.transform = `translate(${cursorX}cqi, ${cursorY}cqi)`;
      cursor.style.opacity = time < 10100 ? '1' : '0';
      setRipple(time);
    }

    function tick(now) {
      if (!lastFrame) lastFrame = now;
      const delta = Math.min(now - lastFrame, 80);
      lastFrame = now;

      if (inView && !userPaused && !showReducedStatic) {
        elapsed = (elapsed + delta) % duration;
        render(elapsed);
      }

      requestAnimationFrame(tick);
    }

    playback.addEventListener('click', () => {
      if (showReducedStatic) {
        showReducedStatic = false;
        userPaused = false;
        elapsed = 0;
      } else {
        userPaused = !userPaused;
      }
      setPlaybackState();
      render(elapsed);
    });

    const syncWalkthroughMotion = () => {
      const reduce = shouldReduceMotion();
      if (reduce && !showReducedStatic) {
        pausedBeforeReducedMotion = userPaused;
        showReducedStatic = true;
        userPaused = true;
      } else if (!reduce && showReducedStatic) {
        showReducedStatic = false;
        userPaused = pausedBeforeReducedMotion;
        elapsed = 0;
      }
      setPlaybackState();
      render(elapsed);
    };

    document.addEventListener('accessai:settingschange', syncWalkthroughMotion);
    onSystemMotionChange(syncWalkthroughMotion);

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        inView = entries.some((entry) => entry.isIntersecting && entry.intersectionRatio >= 0.5);
        lastFrame = performance.now();
      }, { threshold: [0, 0.5, 1] });
      observer.observe(stage);
    } else {
      inView = true;
    }

    setPlaybackState();
    render(0);
    requestAnimationFrame(tick);
  }

  function init() {
    initSkipLink();
    initMenu();
    initSmoothScroll();
    initReveal();
    initCountUp();
    initPageTransitions();
    initSecondBrainWalkthrough();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
