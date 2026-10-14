(() => {
  'use strict';

  const key = 'secondBrainAccessibilitySettings';
  const defaults = {
    fontScale: 100,
    contrast: 'default',
    spacing: false,
    readableFont: false,
    underlineLinks: false,
    reducedMotion: false
  };

  const root = document.documentElement;

  function load() {
    try {
      return { ...defaults, ...JSON.parse(window.localStorage.getItem(key) || '{}') };
    } catch (_) {
      return { ...defaults };
    }
  }

  function save(settings) {
    try {
      window.localStorage.setItem(key, JSON.stringify(settings));
    } catch (_) {}
  }

  function buildWidget() {
    const existing = document.querySelector('.accessibility-settings');
    if (existing) return existing;

    const widget = document.createElement('aside');
    widget.className = 'accessibility-settings';
    widget.setAttribute('aria-label', 'Accessibility appearance settings');
    widget.innerHTML = `
      <button class="accessibility-settings__toggle" type="button" aria-label="Open accessibility settings" aria-expanded="false" aria-controls="accessibility-settings-panel">
        <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
          <circle cx="12" cy="4.5" r="2.2"></circle>
          <path d="M4.8 8.2h14.4"></path>
          <path d="M12 6.8v6.1"></path>
          <path d="M8.1 20.2l2.1-6.7"></path>
          <path d="M15.9 20.2l-2.1-6.7"></path>
        </svg>
      </button>
      <form class="accessibility-settings__panel" id="accessibility-settings-panel" hidden>
        <div class="accessibility-settings__heading">
          <strong>Accessibility</strong>
          <span>Appearance</span>
        </div>
        <label class="accessibility-settings__field">
          <span>Text size <output for="a11y-text-size" data-a11y-size-output>100%</output></span>
          <input id="a11y-text-size" name="fontScale" type="range" min="100" max="130" step="10" value="100">
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
        <button class="accessibility-settings__reset" type="button">Reset</button>
      </form>
    `;
    document.body.append(widget);
    return widget;
  }

  function init() {
    if (root.dataset.a11yInitialized === 'true') return;
    root.dataset.a11yInitialized = 'true';

    const widget = buildWidget();
    const toggle = widget.querySelector('.accessibility-settings__toggle');
    const panel = widget.querySelector('.accessibility-settings__panel');
    const form = panel;
    const sizeOutput = widget.querySelector('[data-a11y-size-output]');
    let settings = load();

    const syncControls = () => {
      form.elements.fontScale.value = String(settings.fontScale);
      form.elements.contrast.value = settings.contrast;
      form.elements.spacing.checked = settings.spacing;
      form.elements.readableFont.checked = settings.readableFont;
      form.elements.underlineLinks.checked = settings.underlineLinks;
      form.elements.reducedMotion.checked = settings.reducedMotion;
      sizeOutput.value = `${settings.fontScale}%`;
    };

    const apply = () => {
      root.style.setProperty('--a11y-font-scale', settings.fontScale / 100);
      root.dataset.a11yContrast = settings.contrast;
      root.dataset.a11ySpacing = String(settings.spacing);
      root.dataset.a11yReadableFont = String(settings.readableFont);
      root.dataset.a11yUnderlineLinks = String(settings.underlineLinks);
      root.dataset.a11yMotion = settings.reducedMotion ? 'reduce' : 'default';

      if (settings.reducedMotion && window.accessAILenis && typeof window.accessAILenis.destroy === 'function') {
        window.accessAILenis.destroy();
        window.accessAILenis = null;
      }
    };

    const setOpen = (open) => {
      panel.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close accessibility settings' : 'Open accessibility settings');
    };

    toggle.addEventListener('click', () => {
      setOpen(panel.hidden);
    });

    form.addEventListener('input', (event) => {
      const target = event.target;
      if (!target.name) return;
      settings = {
        ...settings,
        [target.name]: target.type === 'checkbox' ? target.checked : target.value
      };
      if (target.name === 'fontScale') {
        settings.fontScale = Number(target.value);
      }
      apply();
      syncControls();
      save(settings);
    });

    form.addEventListener('change', (event) => {
      if (event.target.name !== 'contrast') return;
      settings.contrast = event.target.value;
      apply();
      save(settings);
    });

    widget.querySelector('.accessibility-settings__reset').addEventListener('click', () => {
      settings = { ...defaults };
      apply();
      syncControls();
      save(settings);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') setOpen(false);
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
