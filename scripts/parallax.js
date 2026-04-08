/**
 * AcessAI — Parallax, Animations & Visual Effects
 * Award-winning interaction layer
 */

(function () {
  'use strict';

  /* ─── Utilities ─── */
  const qs  = (sel, ctx = document) => ctx.querySelector(sel);
  const qsa = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
  const clamp = (v, min, max) => Math.min(Math.max(v, min), max);

  /* ──────────────────────────────────────────────
     1. PARTICLE CANVAS — Hero background
  ────────────────────────────────────────────── */
  function initParticles() {
    const hero = qs('.custom-hero-section');
    if (!hero) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'particles-canvas';
    Object.assign(canvas.style, {
      position: 'absolute',
      inset: '0',
      zIndex: '1',
      pointerEvents: 'none',
      opacity: '0.55'
    });
    hero.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let W, H, particles;
    const PARTICLE_COUNT = 90;
    const COLORS = ['#2563eb', '#38bdf8', '#818cf8', '#60a5fa', '#0ea5e9'];

    function resize() {
      W = canvas.width  = hero.offsetWidth;
      H = canvas.height = hero.offsetHeight;
    }

    function mkParticle() {
      return {
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 1.8 + 0.4,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        alpha: Math.random() * 0.6 + 0.2,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        pulse: Math.random() * Math.PI * 2
      };
    }

    function init() {
      resize();
      particles = Array.from({ length: PARTICLE_COUNT }, mkParticle);
    }

    function drawConnections() {
      const MAX_DIST = 120;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < MAX_DIST) {
            const alpha = (1 - dist / MAX_DIST) * 0.2;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(56,189,248,${alpha})`;
            ctx.lineWidth = 0.6;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }
    }

    let frame = 0;
    function animate() {
      ctx.clearRect(0, 0, W, H);
      frame++;

      drawConnections();

      particles.forEach(p => {
        p.pulse += 0.02;
        const pulsed = p.alpha * (0.7 + 0.3 * Math.sin(p.pulse));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = pulsed;
        ctx.fill();
        ctx.globalAlpha = 1;

        p.x += p.vx;
        p.y += p.vy;

        if (p.x < -10) p.x = W + 10;
        if (p.x > W + 10) p.x = -10;
        if (p.y < -10) p.y = H + 10;
        if (p.y > H + 10) p.y = -10;
      });

      requestAnimationFrame(animate);
    }

    window.addEventListener('resize', () => {
      resize();
    }, { passive: true });

    init();
    animate();
  }

  /* ──────────────────────────────────────────────
     2. PARALLAX — Hero image
  ────────────────────────────────────────────── */
  function initParallax() {
    const heroImg = qs('.custom-hero-section img');
    if (!heroImg) return;

    let ticking = false;

    function updateParallax() {
      const scrollY = window.scrollY;
      const heroH   = heroImg.closest('.custom-hero-section')?.offsetHeight || 720;
      // Only apply while hero is visible
      if (scrollY < heroH) {
        const offset = scrollY * 0.45;
        heroImg.style.transform = `translateY(${offset}px) scale(1.1)`;
      }
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(updateParallax);
        ticking = true;
      }
    }, { passive: true });

    // Initial call
    heroImg.style.transform = 'translateY(0) scale(1.1)';
  }

  /* ──────────────────────────────────────────────
     3. PARALLAX — CTA section background
  ────────────────────────────────────────────── */
  function initCtaParallax() {
    const ctaImg = qs('.modern-cta-section img');
    if (!ctaImg) return;

    let ticking = false;

    function update() {
      const section = ctaImg.closest('.modern-cta-section');
      const rect    = section.getBoundingClientRect();
      const visible = rect.top < window.innerHeight && rect.bottom > 0;
      if (visible) {
        const progress = (window.innerHeight - rect.top) / (window.innerHeight + section.offsetHeight);
        const offset   = (progress - 0.5) * 120;
        ctaImg.style.transform = `translateY(${offset}px) scale(1.15)`;
      }
      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
  }

  /* ──────────────────────────────────────────────
     4. SCROLL REVEAL — Intersection Observer
  ────────────────────────────────────────────── */
  function initScrollReveal() {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    // Add reveal classes to key elements
    const cardSelectors = [
      '.tool-card',
      '.feature-card',
      '.blog-post',
      '.ai-item',
      '.tech-item',
      '.app-card',
      '.future-item',
      '.stat-item',
      '.stat-card',
      '.metric-card',
      '.box',
      '.principle-card',
      '.service-card',
      '.recommendation-card'
    ];

    const sectionSelectors = [
      '.section-header',
      '.fundamental-section-header',
      '.my-ai-quote',
      '.mission-header',
      '.help-hero-content',
      '.results-header'
    ];

    // Cards — stagger by index within parent
    cardSelectors.forEach(sel => {
      qsa(sel).forEach((el, i) => {
        el.classList.add('reveal');
        const parent = el.parentElement;
        if (parent) parent.classList.add('stagger-children');
        io.observe(el);
      });
    });

    sectionSelectors.forEach(sel => {
      qsa(sel).forEach(el => {
        el.classList.add('reveal');
        io.observe(el);
      });
    });

    // Alternating left/right for feature rows
    qsa('.ai-item, .future-item').forEach((el, i) => {
      el.classList.remove('reveal');
      el.classList.add(i % 2 === 0 ? 'reveal-left' : 'reveal-right');
      io.observe(el);
    });
  }

  /* ──────────────────────────────────────────────
     5. COUNT-UP ANIMATION — Statistics
  ────────────────────────────────────────────── */
  function initCountUp() {
    const statNumbers = qsa('.stat-number, .stat-item .stat-number');

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          const el  = entry.target;
          const raw = el.textContent.trim();

          // Parse suffix (%, +, x, B, M etc.)
          const match = raw.match(/^([0-9.]+)([^0-9.]*)$/);
          if (!match) return;

          const target   = parseFloat(match[1]);
          const suffix   = match[2] || '';
          const duration = 1800;
          const start    = performance.now();
          const isDecimal = raw.includes('.');

          function tick(now) {
            const elapsed  = now - start;
            const progress = clamp(elapsed / duration, 0, 1);
            const ease     = 1 - Math.pow(1 - progress, 3);
            const val      = target * ease;
            el.textContent = (isDecimal ? val.toFixed(1) : Math.round(val)) + suffix;
            if (progress < 1) requestAnimationFrame(tick);
          }

          requestAnimationFrame(tick);
          io.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );

    statNumbers.forEach(el => io.observe(el));
  }

  /* ──────────────────────────────────────────────
     6. HEADER — Shrink on scroll
  ────────────────────────────────────────────── */
  function initStickyHeader() {
    const header = qs('header.modern-header, header[role="banner"]');
    if (!header) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          if (window.scrollY > 40) {
            header.classList.add('scrolled');
          } else {
            header.classList.remove('scrolled');
          }
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ──────────────────────────────────────────────
     7. FLOATING ORBS — Hero decoration
  ────────────────────────────────────────────── */
  function initHeroOrbs() {
    const hero = qs('.custom-hero-section');
    if (!hero) return;

    const orbData = [
      { className: 'orb orb-1' },
      { className: 'orb orb-2' },
      { className: 'orb orb-3' }
    ];

    orbData.forEach(({ className }) => {
      const orb = document.createElement('div');
      orb.className = className;
      hero.appendChild(orb);
    });
  }

  /* ──────────────────────────────────────────────
     8. HERO SCROLL INDICATOR
  ────────────────────────────────────────────── */
  function initHeroScrollIndicator() {
    const hero = qs('.custom-hero-section');
    if (!hero) return;

    // Fade out indicator when user scrolls
    const indicator = hero.querySelector('.hero-scroll-indicator');
    if (!indicator) return;

    window.addEventListener('scroll', () => {
      const opacity = 1 - clamp(window.scrollY / 200, 0, 1);
      indicator.style.opacity = opacity;
    }, { passive: true });
  }

  /* ──────────────────────────────────────────────
     9. SMOOTH TAB TRANSITIONS
  ────────────────────────────────────────────── */
  function initTabTransitions() {
    // Patch switchTab to add fade animation
    const origSwitch = window.switchTab;
    if (!origSwitch) return;

    window.switchTab = function (tabName) {
      // Fade out current active tab
      const current = qs('.tab-content.active');
      if (current) {
        current.style.opacity = '0';
        current.style.transition = 'opacity 0.2s ease';
      }

      setTimeout(() => {
        origSwitch(tabName);
        const next = document.getElementById(tabName);
        if (next) {
          next.style.opacity = '0';
          next.style.transition = 'opacity 0.3s ease';
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              next.style.opacity = '1';
            });
          });
        }
        // Re-trigger scroll reveal for newly visible elements
        setTimeout(initScrollReveal, 100);
      }, 150);
    };
  }

  /* ──────────────────────────────────────────────
     10. TILT EFFECT — Cards
  ────────────────────────────────────────────── */
  function initCardTilt() {
    const cards = qsa('.tool-card, .feature-card, .tech-item, .app-card');

    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect   = card.getBoundingClientRect();
        const cx     = rect.left + rect.width  / 2;
        const cy     = rect.top  + rect.height / 2;
        const dx     = (e.clientX - cx) / (rect.width  / 2);
        const dy     = (e.clientY - cy) / (rect.height / 2);
        const rx     = clamp(dy * 5, -8, 8);
        const ry     = clamp(-dx * 5, -8, 8);

        card.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-6px)`;
        card.style.transition = 'transform 0.1s ease';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        card.style.transition = 'transform 0.4s ease, border-color 0.3s ease, box-shadow 0.3s ease';
      });
    });
  }

  /* ──────────────────────────────────────────────
     11. INJECT HERO ELEMENTS
  ────────────────────────────────────────────── */
  function enhanceHero() {
    const hero = qs('.custom-hero-section');
    if (!hero) return;

    // Ensure hero content overlay has correct structure
    const overlay = hero.querySelector('div[style*="position: absolute"]');
    if (overlay) {
      // Add tagline below the h1
      const h1 = overlay.querySelector('h1');
      if (h1 && !overlay.querySelector('.hero-tagline')) {
        const tagline = document.createElement('p');
        tagline.className = 'hero-tagline';
        tagline.textContent = 'Making the Web Accessible for Everyone';
        h1.insertAdjacentElement('afterend', tagline);
      }
    }

    // Add scroll indicator
    if (!hero.querySelector('.hero-scroll-indicator')) {
      const indicator = document.createElement('div');
      indicator.className = 'hero-scroll-indicator';
      indicator.setAttribute('aria-hidden', 'true');
      indicator.textContent = 'Scroll';
      hero.appendChild(indicator);
    }
  }

  /* ──────────────────────────────────────────────
     12. INJECT WAVE DIVIDERS between key sections
  ────────────────────────────────────────────── */
  function injectWaveDividers() {
    // Wave between hero and CTA
    const cta = qs('.modern-cta-section');
    if (cta && !qs('.wave-divider')) {
      const wave = document.createElement('div');
      wave.className = 'wave-divider';
      wave.innerHTML = `
        <svg viewBox="0 0 1440 60" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z" fill="#0d1a36"/>
        </svg>`;
      cta.parentNode.insertBefore(wave, cta);
    }
  }

  /* ──────────────────────────────────────────────
     13. MISSION SECTION PARALLAX
  ────────────────────────────────────────────── */
  function initMissionParallax() {
    const missionHero = qs('.mission-hero');
    if (!missionHero) return;

    // Add orbs to mission hero
    ['orb orb-1', 'orb orb-2'].forEach(cls => {
      const orb = document.createElement('div');
      orb.className = cls;
      missionHero.style.overflow = 'hidden';
      missionHero.appendChild(orb);
    });

    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const rect = missionHero.getBoundingClientRect();
          if (rect.top < window.innerHeight && rect.bottom > 0) {
            const progress = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
            const title = missionHero.querySelector('.mission-hero-title, .mission-hero-content');
            if (title) {
              title.style.transform = `translateY(${(progress - 0.5) * 30}px)`;
            }
          }
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  /* ──────────────────────────────────────────────
     INIT
  ────────────────────────────────────────────── */
  function init() {
    initHeroOrbs();
    enhanceHero();
    injectWaveDividers();
    initParticles();
    initParallax();
    initCtaParallax();
    initScrollReveal();
    initCountUp();
    initStickyHeader();
    initHeroScrollIndicator();
    initCardTilt();
    initMissionParallax();

    // Tab transitions – patch after DOM scripts have run
    setTimeout(initTabTransitions, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
