/**
 * AccessAI — Opening scroll sequence
 * ---------------------------------------------------------------------
 * Progressive enhancement only. The HTML (#hp-seq) already reads fine
 * as three plain stacked paragraphs with no JS at all — that's what
 * ships by default. This script adds the pinned, scroll-scrubbed
 * crossfade on top of it, and only when it's safe to:
 *
 *   - prefers-reduced-motion: reduce → skip entirely, static stack stays.
 *   - missing rAF/IntersectionObserver → skip entirely (very old browser).
 *
 * The animation itself is driven by reading the *actual* scroll
 * position every frame (rAF-throttled) and mapping it to opacity/
 * transform — never by intercepting or fighting the scroll wheel
 * (no preventDefault, no forced scrollTo). Pinning is plain CSS
 * `position: sticky`, so trackpad/wheel/keyboard/touch scrolling all
 * behave exactly as the browser already handles them.
 *
 * One-shot per page load: this is a plain in-memory flag (`introDone`),
 * not sessionStorage/localStorage, and that's deliberate — a real
 * reload or a fresh visit to the link re-runs this whole script from
 * scratch, so the intro plays again exactly when it should. What it
 * must NOT do is come back within the same page load: scrolling back
 * up to the top, or switching to a different nav tab (AI/Blogs/Mission
 * are all still index.html under the hood, no reload happens) and
 * back to Home. Once finished — by scrolling through it, by "Skip
 * intro", or by navigating to any non-Home tab — #hp-seq is removed
 * from layout outright (not just frozen in place): a frozen-but-still-
 * pinned 320vh section would still swallow a full screen's worth of
 * scrolling on every tab, which reads exactly like the intro is still
 * "there". Removing it means scrolling to the top on any tab shows
 * that tab's content immediately, the way it should have all along.
 * Collapsing the height mid-session would normally jump whatever the
 * visitor is looking at, so removal is paired with a scrollTo that
 * subtracts the removed height — same content stays under the cursor.
 */
(function () {
    'use strict';

    var seq = document.getElementById('hp-seq');
    if (!seq) return;

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (!('requestAnimationFrame' in window)) return;

    var lines = Array.prototype.slice.call(seq.querySelectorAll('.hp-seq-line'));
    var BEAT_COUNT = lines.length;
    if (BEAT_COUNT === 0) return;

    // Per-beat timing, as a fraction of that beat's own scroll window.
    var FADE_IN_END = 0.18;   // 0 → this: fading/sliding in
    var FADE_OUT_START = 0.82; // this → 1: fading/sliding out (all but the last beat)
    var DRIFT_PX = 22;         // subtle — this is a settle, not a bounce

    var seqTop = 0;
    var scrollableDistance = 1;
    var ticking = false;
    var revealed = false;
    var introDone = false;

    function measure() {
        seqTop = seq.offsetTop;
        scrollableDistance = Math.max(seq.offsetHeight - window.innerHeight, 1);
    }

    function clamp01(v) { return Math.max(0, Math.min(1, v)); }

    function applyProgress(progress) {
        var beatWindow = 1 / BEAT_COUNT;

        lines.forEach(function (line, i) {
            var local = clamp01((progress - i * beatWindow) / beatWindow);
            var isFirst = i === 0;
            var isLast = i === BEAT_COUNT - 1;
            var opacity;
            var drift;

            // Beat 0 has nothing before it to crossfade from — it's what
            // paints on first load, at scrollY 0/progress 0. Fading it in
            // like every other beat left the very first frame fully
            // transparent (a blank screen until the visitor scrolls), so
            // it skips the fade-in phase and starts already fully visible.
            if (!isFirst && local <= FADE_IN_END) {
                var inT = local / FADE_IN_END;
                opacity = inT;
                drift = DRIFT_PX * (1 - inT);
            } else if (!isLast && local >= FADE_OUT_START) {
                var outT = (local - FADE_OUT_START) / (1 - FADE_OUT_START);
                opacity = 1 - outT;
                drift = -DRIFT_PX * outT;
            } else {
                opacity = 1;
                drift = 0;
            }

            line.style.opacity = String(opacity);
            line.style.transform = 'translateY(calc(-50% + ' + drift.toFixed(1) + 'px))';
        });

        if (progress >= 0.995) {
            finishIntro();
        }
    }

    // Removes #hp-seq from layout for the rest of this page load and
    // stops reacting to scroll. Idempotent — safe to call from multiple
    // triggers (scroll completion, Skip intro, switching to a non-Home
    // tab). Compensates scroll position so whatever the visitor is
    // currently looking at doesn't jump when the section disappears.
    function finishIntro() {
        if (introDone) return;
        introDone = true;

        if (!revealed) {
            revealed = true;
            seq.classList.add('hp-seq--revealed'); // header fades in even if we're mid-freeze
        }

        var removedHeight = seq.offsetHeight;
        var priorScrollY = window.scrollY;

        seq.style.display = 'none';

        // Only content *above* the current scroll position moved — if
        // the visitor hadn't scrolled into #hp-seq's range yet (e.g. it
        // was skipped instantly via a tab click at scrollY 0), there's
        // nothing to compensate and clamping to 0 is correct anyway.
        if (priorScrollY > 0) {
            window.scrollTo(0, Math.max(0, priorScrollY - removedHeight));
        }

        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onResize);
    }

    function update() {
        ticking = false;
        if (introDone) return;
        var progress = clamp01((window.scrollY - seqTop) / scrollableDistance);
        applyProgress(progress);
    }

    function onScroll() {
        if (!ticking) {
            ticking = true;
            requestAnimationFrame(update);
        }
    }

    function onResize() {
        if (introDone) return;
        measure();
        update();
    }

    // Leaving the Home tab for AI/Blogs/Mission (all still index.html,
    // switched client-side with no reload) means the visitor is done
    // with the homepage narrative — remove the section immediately
    // rather than leaving it able to reappear if they scroll to the
    // top of whatever tab they land on.
    function watchTabSwitches() {
        var tabButtons = document.querySelectorAll('.nav-item[data-tab]');
        tabButtons.forEach(function (btn) {
            if (btn.getAttribute('data-tab') === 'home') return;
            btn.addEventListener('click', finishIntro);
        });
    }

    // Switch on the pinned layout, measure, then paint the correct
    // starting state immediately (handles a mid-page load/back-nav).
    seq.classList.add('hp-seq--enhanced');
    measure();
    update();
    watchTabSwitches();

    var skipLink = seq.querySelector('.hp-seq-skip');
    if (skipLink) skipLink.addEventListener('click', finishIntro);

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
})();
