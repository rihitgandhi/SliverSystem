(() => {
  'use strict';

  const STORAGE_KEY = 'secondBrainAccessibilitySettings';
  const WIDGET_VERSION = '5';
  const FONT_MIN = 100;
  const FONT_MAX = 200;
  const FONT_STEP = 10;
  const CONTRAST_VALUES = ['default', 'high', 'dark'];
  const defaults = Object.freeze({
    fontScale: 100,
    contrast: 'default',
    spacing: false,
    readableFont: false,
    underlineLinks: false,
    reducedMotion: false
  });
  const root = document.documentElement;

  const asBoolean = (value) => value === true || value === 'true';

  function normalize(candidate = {}) {
    const rawScale = Number(candidate.fontScale);
    const roundedScale = Number.isFinite(rawScale)
      ? Math.round(rawScale / FONT_STEP) * FONT_STEP
      : defaults.fontScale;

    return {
      fontScale: Math.min(FONT_MAX, Math.max(FONT_MIN, roundedScale)),
      contrast: CONTRAST_VALUES.includes(candidate.contrast) ? candidate.contrast : defaults.contrast,
      spacing: asBoolean(candidate.spacing),
      readableFont: asBoolean(candidate.readableFont),
      underlineLinks: asBoolean(candidate.underlineLinks),
      reducedMotion: asBoolean(candidate.reducedMotion)
    };
  }

  function load() {
    try {
      return normalize(JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}'));
    } catch (_) {
      return { ...defaults };
    }
  }

  function save(settings) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (_) {
      // Settings still work for the current page when storage is unavailable.
    }
  }

  function buildWidget() {
    const existing = document.querySelector('.accessibility-settings');
    const isCurrent = existing
      && existing.dataset.accessibilityVersion === WIDGET_VERSION
      && existing.querySelector('.accessibility-settings__close')
      && existing.querySelector('.accessibility-settings__status');
    if (isCurrent) return existing;
    if (existing) existing.remove();

    const widget = document.createElement('aside');
    widget.className = 'accessibility-settings';
    widget.dataset.accessibilityVersion = WIDGET_VERSION;
    widget.setAttribute('aria-label', 'Accessibility appearance settings');
    widget.innerHTML = `
      <button class="accessibility-settings__toggle" type="button" aria-label="Open accessibility settings" aria-haspopup="dialog" aria-expanded="false" aria-controls="accessibility-settings-panel">
        <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
          <circle cx="12" cy="4.5" r="2.2"></circle>
          <path d="M4.8 8.2h14.4"></path>
          <path d="M12 6.8v6.1"></path>
          <path d="M8.1 20.2l2.1-6.7"></path>
          <path d="M15.9 20.2l-2.1-6.7"></path>
        </svg>
      </button>
      <form class="accessibility-settings__panel" id="accessibility-settings-panel" role="dialog" aria-modal="false" aria-labelledby="accessibility-settings-title" hidden>
        <div class="accessibility-settings__heading">
          <div>
            <strong id="accessibility-settings-title">Accessibility</strong>
            <span>Appearance</span>
          </div>
          <button class="accessibility-settings__close" type="button" aria-label="Close accessibility settings">
            <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M6 6l12 12M18 6L6 18"></path></svg>
          </button>
        </div>
        <label class="accessibility-settings__field">
          <span>Text size <output for="a11y-text-size" data-a11y-size-output>100%</output></span>
          <input id="a11y-text-size" name="fontScale" type="range" min="${FONT_MIN}" max="${FONT_MAX}" step="${FONT_STEP}" value="100">
          <span class="accessibility-settings__range-labels" aria-hidden="true"><small>100%</small><small>200%</small></span>
        </label>
        <label class="accessibility-settings__field">
          <span>Contrast</span>
          <select name="contrast">
            <option value="default">Default</option>
            <option value="high">High contrast</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <label class="accessibility-settings__check">
          <input name="spacing" type="checkbox">
          <span>More text spacing</span>
        </label>
        <label class="accessibility-settings__check">
          <input name="readableFont" type="checkbox">
          <span>Readable font</span>
        </label>
        <label class="accessibility-settings__check">
          <input name="underlineLinks" type="checkbox">
          <span>Underline links</span>
        </label>
        <label class="accessibility-settings__check">
          <input name="reducedMotion" type="checkbox">
          <span>Reduce motion</span>
        </label>
        <button class="accessibility-settings__reset" type="button">Reset all settings</button>
        <p class="accessibility-settings__status" aria-live="polite" aria-atomic="true"></p>
      </form>
    `;
    document.body.append(widget);
    return widget;
  }

  function init() {
    const currentWidget = document.querySelector('.accessibility-settings');
    if (
      root.dataset.a11yInitialized === 'true'
      && currentWidget
      && currentWidget.dataset.accessibilityVersion === WIDGET_VERSION
    ) return;
    root.dataset.a11yInitialized = 'true';

    const widget = buildWidget();
    const toggle = widget.querySelector('.accessibility-settings__toggle');
    const panel = widget.querySelector('.accessibility-settings__panel');
    const closeButton = widget.querySelector('.accessibility-settings__close');
    const resetButton = widget.querySelector('.accessibility-settings__reset');
    const sizeOutput = widget.querySelector('[data-a11y-size-output]');
    const status = widget.querySelector('.accessibility-settings__status');
    const form = panel;
    const themeColor = document.querySelector('meta[name="theme-color"]');
    const originalThemeColor = themeColor ? themeColor.content : '';
    let settings = load();
    let statusTimer = null;

    const syncControls = () => {
      form.elements.fontScale.value = String(settings.fontScale);
      form.elements.contrast.value = settings.contrast;
      form.elements.spacing.checked = settings.spacing;
      form.elements.readableFont.checked = settings.readableFont;
      form.elements.underlineLinks.checked = settings.underlineLinks;
      form.elements.reducedMotion.checked = settings.reducedMotion;
      sizeOutput.value = `${settings.fontScale}%`;
    };

    const announce = (message) => {
      window.clearTimeout(statusTimer);
      status.textContent = '';
      window.requestAnimationFrame(() => {
        status.textContent = message;
        statusTimer = window.setTimeout(() => {
          status.textContent = '';
        }, 2500);
      });
    };

    const apply = (shouldAnnounce = false, message = 'Accessibility settings applied') => {
      root.style.setProperty('--a11y-font-scale', String(settings.fontScale / 100));
      root.dataset.a11yFontScale = String(settings.fontScale);
      root.dataset.a11yContrast = settings.contrast;
      root.dataset.a11ySpacing = String(settings.spacing);
      root.dataset.a11yReadableFont = String(settings.readableFont);
      root.dataset.a11yUnderlineLinks = String(settings.underlineLinks);
      root.dataset.a11yMotion = settings.reducedMotion ? 'reduce' : 'default';

      if (settings.contrast === 'dark') {
        root.style.colorScheme = 'dark';
        if (themeColor) themeColor.content = '#05070a';
      } else if (settings.contrast === 'high') {
        root.style.colorScheme = 'light';
        if (themeColor) themeColor.content = '#ffffff';
      } else {
        root.style.removeProperty('color-scheme');
        if (themeColor) themeColor.content = originalThemeColor;
      }

      document.dispatchEvent(new CustomEvent('accessai:settingschange', {
        detail: { ...settings }
      }));

      if (shouldAnnounce) announce(message);
    };

    const setOpen = (open, returnFocus = false) => {
      panel.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Hide accessibility settings' : 'Open accessibility settings');

      if (open) {
        window.requestAnimationFrame(() => closeButton.focus());
      } else if (returnFocus) {
        toggle.focus();
      }
    };

    const messages = {
      fontScale: () => `Text size set to ${settings.fontScale}%`,
      contrast: () => settings.contrast === 'default'
        ? 'Default contrast applied'
        : `${settings.contrast === 'high' ? 'High contrast' : 'Dark mode'} applied`,
      spacing: () => `More text spacing ${settings.spacing ? 'on' : 'off'}`,
      readableFont: () => `Readable font ${settings.readableFont ? 'on' : 'off'}`,
      underlineLinks: () => `Underline links ${settings.underlineLinks ? 'on' : 'off'}`,
      reducedMotion: () => `Reduce motion ${settings.reducedMotion ? 'on' : 'off'}`
    };

    const updateSetting = (event) => {
      const target = event.target;
      if (!target.name || !(target.name in defaults)) return;

      settings = normalize({
        ...settings,
        [target.name]: target.type === 'checkbox' ? target.checked : target.value
      });
      apply(true, messages[target.name]());
      syncControls();
      save(settings);
    };

    toggle.addEventListener('click', () => setOpen(panel.hidden, !panel.hidden));
    closeButton.addEventListener('click', () => setOpen(false, true));
    form.addEventListener('submit', (event) => event.preventDefault());
    form.addEventListener('input', (event) => {
      if (event.target.name === 'fontScale') updateSetting(event);
    });
    form.addEventListener('change', (event) => {
      if (event.target.name !== 'fontScale') updateSetting(event);
    });

    resetButton.addEventListener('click', () => {
      settings = { ...defaults };
      apply(true, 'All accessibility settings reset');
      syncControls();
      save(settings);
    });

    document.addEventListener('pointerdown', (event) => {
      if (!panel.hidden && !widget.contains(event.target)) setOpen(false);
    });

    document.addEventListener('keydown', (event) => {
      if (panel.hidden) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false, true);
        return;
      }

      if (event.key !== 'Tab') return;
      const focusable = Array.from(panel.querySelectorAll('button, input, select')).filter((element) => !element.disabled);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    window.addEventListener('storage', (event) => {
      if (event.key !== STORAGE_KEY) return;
      settings = load();
      apply();
      syncControls();
    });

    apply();
    syncControls();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
