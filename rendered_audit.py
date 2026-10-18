"""Rendered accessibility checks, with every affected element retained."""

from functools import lru_cache
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urljoin, urlparse

import requests

from web_audit import _is_private_host


PROJECT_ROOT = Path(__file__).resolve().parent
VERCEL_BROWSER_DIR = PROJECT_ROOT / '.playwright'

# The Vercel build installs Chromium into the project so the Python function
# bundler can include it. Point Playwright at that bundled browser at runtime.
if os.getenv('VERCEL') and VERCEL_BROWSER_DIR.exists():
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(VERCEL_BROWSER_DIR)

AXE_PATH = Path(__file__).resolve().parent / 'vendor' / 'axe-core' / 'axe.min.js'
VIEWPORTS = [('Desktop', 1440, 900), ('Mobile', 390, 844), ('Narrow', 320, 800)]
SCAN_SLOTS = threading.BoundedSemaphore(2)
SCAN_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa',
             'wcag2aaa', 'wcag21aaa', 'wcag22aaa', 'best-practice']
MANUAL_CHECKS = [
    'Use the keyboard to test menus, dialogs, focus order, traps, and visible focus in every interactive state.',
    'Check that image descriptions, link names, headings, and error messages make sense in context.',
    'Test with a screen reader, 200–400% zoom, text spacing overrides, and reduced motion.',
    'Review captions, audio descriptions, drag alternatives, authentication, and complete form workflows.',
    'Scan other pages and logged-in states separately; this report covers the submitted page only.',
]


class ScanUnavailable(RuntimeError):
    pass


def _public_url(url):
    parsed = urlparse(url)
    return (parsed.scheme in ('http', 'https') and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and not _is_private_host(parsed.hostname))


class PublicResources:
    """Serve public resources to the scan browser without unchecked redirects.

    The browser never continues a network request itself. Redirects are followed
    here, validating every hop, and only the final response is fulfilled.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'AccessAI-Accessibility-Checker/2.0'
        self.started = time.monotonic()
        self.requests = 0
        self.blocked = set()
        self.cache = {}
        self.is_public = lru_cache(maxsize=512)(_public_url)

    def handle(self, route):
        request = route.request
        if request.method not in ('GET', 'HEAD') or request.resource_type == 'media':
            self.blocked.add('Media downloads and requests that submit data were not loaded.')
            return route.abort()
        try:
            resource = self.fetch(request.url, request.headers.get('user-agent', ''))
            if resource[0] >= 400:
                self.blocked.add('Some page resources returned HTTP errors; content or styling may be incomplete.')
            route.fulfill(status=resource[0], headers=resource[1], body=resource[2])
        except Exception:
            self.blocked.add('Some page resources could not be loaded; their content may need a separate review.')
            route.abort()

    def fetch(self, url, user_agent=''):
        cache_key = url, user_agent
        if cache_key in self.cache:
            return self.cache[cache_key]
        self.requests += 1
        if self.requests > 500 or time.monotonic() - self.started > 75:
            raise ScanUnavailable('Resource or time budget reached')
        for _ in range(6):
            if not self.is_public(url):
                raise ValueError('Private or unsupported URL')
            headers = {'User-Agent': user_agent} if user_agent else {}
            with self.session.get(url, headers=headers, allow_redirects=False, stream=True, timeout=(5, 8)) as response:
                if 300 <= response.status_code < 400 and response.headers.get('Location'):
                    url = urljoin(url, response.headers['Location'])
                    continue
                chunks, size = [], 0
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > 8 * 1024 * 1024:
                        raise ValueError('Resource exceeds scan size limit')
                    chunks.append(chunk)
                # requests already decompresses the response body.
                headers = {k: v for k, v in response.headers.items()
                           if k.lower() not in ('content-encoding', 'content-length',
                                                'transfer-encoding', 'connection', 'set-cookie')}
                result = response.status_code, headers, b''.join(chunks)
                self.cache[cache_key] = result
                return result
        raise ValueError('Too many redirects')

    def close(self):
        self.session.close()


def _launch(playwright):
    candidates = []
    channel = os.getenv('CHECKER_BROWSER_CHANNEL', '').strip()
    if channel:
        candidates.append({'channel': channel})
    if Path(playwright.chromium.executable_path).exists():
        candidates.append({'channel': 'chromium'})
    candidates.extend([{'channel': 'msedge'}, {'channel': 'chrome'}])
    for options in candidates:
        try:
            return playwright.chromium.launch(headless=True, chromium_sandbox=True,
                                               timeout=15000, **options)
        except Exception:
            continue
    raise ScanUnavailable('A rendering browser is unavailable. Install Chromium with python -m playwright install chromium.')


def _criterion(tags):
    return [f'{match[1]}.{match[2]}.{match[3]}' for tag in tags
            if (match := re.fullmatch(r'wcag(\d)(\d)(\d+)', tag))]


def merge_axe_results(reports):
    """Keep every node, merge repeated desktop/mobile findings by rule + target."""
    findings = {'violations': {}, 'incomplete': {}}
    passed, checked, applicable, failed_or_review = set(), set(), set(), set()
    impact_rank = {'minor': 0, 'moderate': 1, 'serious': 2, 'critical': 3}
    for report in reports:
        viewport = report['viewport']
        frame = report.get('frame', 'main')
        data = report['result']
        checked.update(rule['id'] for kind in ('violations', 'incomplete', 'passes', 'inapplicable')
                       for rule in data.get(kind, []))
        passed.update(rule['id'] for rule in data.get('passes', []))
        applicable.update(rule['id'] for kind in ('violations', 'incomplete', 'passes')
                          for rule in data.get(kind, []))
        failed_or_review.update(rule['id'] for kind in ('violations', 'incomplete')
                                for rule in data.get(kind, []))
        for kind in findings:
            for rule in data.get(kind, []):
                tags = rule.get('tags', [])
                criteria = _criterion(tags)
                standard = 'Enhanced (AAA)' if any(tag.endswith('aaa') for tag in tags) else (
                    'WCAG A/AA' if criteria else 'Best practice')
                for node in rule.get('nodes', []):
                    target = node.get('target') or ['document']
                    selector = ' → '.join(' → '.join(t) if isinstance(t, list) else str(t) for t in target)
                    key = rule['id'], frame, selector
                    checks = node.get('any', []) + node.get('all', []) + node.get('none', [])
                    detail = node.get('failureSummary') or '\n'.join(
                        check.get('message', '') for check in checks if check.get('message'))
                    item = findings[kind].setdefault(key, {
                        'type': rule.get('help', rule['id']), 'rule': rule['id'],
                        'severity': node.get('impact') or rule.get('impact') or 'minor',
                        'element': selector, 'frame': frame, 'html': node.get('html', ''),
                        'explanation': rule.get('description', ''), 'fix': detail or rule.get('help', ''),
                        'helpUrl': rule.get('helpUrl', ''), 'wcag': criteria, 'standard': standard,
                        'viewports': [], 'evidence': [], 'engine': 'axe-core',
                    })
                    impact = node.get('impact') or rule.get('impact') or 'minor'
                    if impact_rank.get(impact, 0) > impact_rank.get(item['severity'], 0):
                        item['severity'] = impact
                    if viewport not in item['viewports']:
                        item['viewports'].append(viewport)
                        item['evidence'].append({'viewport': viewport, 'detail': detail,
                                                 'checks': [{'id': c.get('id'), 'message': c.get('message'),
                                                             'data': c.get('data')} for c in checks]})
    # Do not lose a mobile review item just because desktop confirmed a failure.
    for key, confirmed in findings['violations'].items():
        review = findings['incomplete'].get(key)
        if review:
            review['viewports'] = [v for v in review['viewports'] if v not in confirmed['viewports']]
            review['evidence'] = [e for e in review['evidence'] if e['viewport'] in review['viewports']]
            if not review['viewports']:
                findings['incomplete'].pop(key)
    return {'issues': list(findings['violations'].values()),
            'reviewItems': list(findings['incomplete'].values()),
            'rulesChecked': len(checked), 'rulesPassed': len(passed - failed_or_review),
            'rulesApplicable': len(applicable), 'rulesNotApplicable': len(checked - applicable)}


AXE_RUN = """async (tags) => {
  return await Promise.race([
    axe.run(document, {runOnly: {type: 'tag', values: tags},
      iframes: false, resultTypes: ['violations', 'incomplete', 'passes', 'inapplicable'],
      rules: {'color-contrast-enhanced': {enabled: true}}}),
    new Promise((_, reject) => setTimeout(() => reject(new Error('Audit time limit')), 25000))
  ]);
}"""

EXTRA_REVIEW = """() => {
  const items = [];
  const path = el => {
    if (el.id) return '#' + CSS.escape(el.id);
    const parts = [];
    for (let node = el; node && node.nodeType === 1 && parts.length < 6; node = node.parentElement) {
      let part = node.localName;
      const siblings = node.parentElement ? [...node.parentElement.children].filter(s => s.localName === part) : [];
      if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
      parts.unshift(part);
    }
    return parts.join(' > ');
  };
  for (const el of document.querySelectorAll('body *')) {
    const style = getComputedStyle(el), box = el.getBoundingClientRect();
    if (box.width === 0 || box.height === 0 || style.visibility === 'hidden' || style.display === 'none') continue;
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText && parseFloat(style.fontSize) < 12 && el.namespaceURI === 'http://www.w3.org/1999/xhtml') {
      items.push({rule: 'small-text-review', type: 'Review small text', element: path(el),
        html: el.outerHTML.slice(0, 1500), explanation: 'This text is ' + style.fontSize + '. Small text can be hard to read.',
        fix: 'Consider a larger font and test zoom and user font settings. WCAG does not prescribe a universal minimum font size.'});
    }
    if (typeof el.onclick === 'function' && el.tabIndex < 0 &&
        !el.matches('button,input,select,textarea,summary,a[href]') &&
        !el.querySelector('button,input,select,textarea,summary,a[href],[tabindex="0"]')) {
      items.push({rule: 'custom-control-keyboard-review', type: 'Review keyboard access for a custom click control',
        element: path(el), html: el.outerHTML.slice(0, 1500),
        explanation: 'This visible element has a click handler but is not in the normal Tab order.',
        fix: 'Test the action with the keyboard. Prefer a native button or link. Custom controls need an accessible name, role, keyboard operation, and an appropriate focus strategy.'});
    }
  }
  if (innerWidth <= 400 && document.documentElement.scrollWidth > innerWidth + 1) {
    items.push({rule: 'reflow-review', type: 'Review horizontal scrolling on small screens', element: 'html', html: '',
      explanation: 'The page is ' + document.documentElement.scrollWidth + 'px wide in a ' + innerWidth + 'px viewport.',
      fix: 'Check for clipped text or two-dimensional scrolling. Tables, maps, and similar content may qualify for exceptions.'});
  }
  return items;
}"""


def audit_rendered_page(url):
    if not _public_url(url):
        raise ScanUnavailable('Only public HTTP and HTTPS pages can be scanned.')
    if not SCAN_SLOTS.acquire(blocking=False):
        raise ScanUnavailable('The checker is busy. Try again after the current scans finish.')
    resources = PublicResources()
    reports, warnings, extra, coverage = [], [], [], []
    started = time.monotonic()
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScanUnavailable('Install the checker requirements to enable rendered scans.') from exc
        axe_source = AXE_PATH.read_text(encoding='utf-8')
        with sync_playwright() as playwright:
            browser = _launch(playwright)
            try:
                for label, width, height in VIEWPORTS:
                    if time.monotonic() - started > 100:
                        warnings.append(f'{label}: scan time limit reached before this viewport was tested.')
                        coverage.append({'name': label, 'width': width, 'height': height, 'completed': False})
                        continue
                    name = f'{label} ({width} × {height})'
                    device_options = {}
                    if label == 'Mobile':
                        device_options = {key: value for key, value in playwright.devices['Pixel 7'].items()
                                          if key in ('user_agent', 'is_mobile', 'has_touch', 'device_scale_factor')}
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  service_workers='block', accept_downloads=False,
                                                  **device_options)
                    context.route('**/*', resources.handle)
                    context.route_web_socket('**/*', lambda socket: socket.close())
                    page = context.new_page()
                    page.on('dialog', lambda dialog: dialog.dismiss())
                    page.set_default_timeout(12000)
                    viewport_ok = False
                    try:
                        response = page.goto(url, wait_until='domcontentloaded', timeout=25000)
                        if response and response.status >= 400:
                            raise ScanUnavailable(f'The page returned HTTP {response.status}.')
                        try:
                            page.wait_for_load_state('networkidle', timeout=4000)
                        except Exception:
                            warnings.append(f'{label}: the page was still loading; later content may differ.')
                        # Trigger lazy content without clicking or submitting forms.
                        page.evaluate("async () => { const end = Math.min(document.documentElement.scrollHeight, 16000); for (let y=0; y<end; y+=innerHeight) { scrollTo(0,y); await new Promise(r=>setTimeout(r,50)); } scrollTo(0,0); }")
                        for index, frame in enumerate(page.frames):
                            if time.monotonic() - started > 100:
                                warnings.append(f'{label}: scan time limit reached; some frames were not tested.')
                                break
                            frame_name = 'main' if index == 0 else f'frame {index}: {frame.url}'
                            try:
                                frame.evaluate(axe_source)
                                result = frame.evaluate(AXE_RUN, SCAN_TAGS)
                                reports.append({'viewport': name, 'frame': frame_name, 'result': result})
                                for item in frame.evaluate(EXTRA_REVIEW):
                                    item.update({'severity': 'minor', 'frame': frame_name, 'standard': 'Human review',
                                                 'viewports': [name], 'engine': 'readability-review', 'wcag': [],
                                                 'evidence': [{'viewport': name, 'detail': item['explanation'] + '\n' + item['fix']}]})
                                    extra.append(item)
                                if index == 0:
                                    viewport_ok = True
                            except Exception:
                                warnings.append(f'{label}: {frame_name} could not be fully tested.')
                        coverage.append({'name': label, 'width': width, 'height': height, 'completed': viewport_ok})
                    except Exception as exc:
                        warnings.append(f'{label} scan incomplete: {str(exc).splitlines()[0][:200]}')
                        coverage.append({'name': label, 'width': width, 'height': height, 'completed': False})
                    finally:
                        context.close()
            finally:
                browser.close()
        if not reports:
            raise ScanUnavailable('The rendered page could not be tested. ' + ' '.join(warnings))
        merged = merge_axe_results(reports)
        extra_by_target = {}
        for item in extra:
            key = item['rule'], item['frame'], item['element']
            if key in extra_by_target:
                extra_by_target[key]['viewports'].extend(item['viewports'])
                extra_by_target[key]['evidence'].extend(item['evidence'])
            else:
                extra_by_target[key] = item
        merged['reviewItems'].extend(extra_by_target.values())
        merged['coverage'] = {
            'engine': 'axe-core', 'version': reports[0]['result'].get('testEngine', {}).get('version', ''),
            'viewports': coverage, 'framesScanned': len(reports), 'scope': 'Submitted page; initial rendered state',
            'standards': ['WCAG 2.0–2.2 A/AA', 'Available AAA checks', 'Best practices'],
            'warnings': sorted(set(warnings) | resources.blocked),
            'manualChecks': MANUAL_CHECKS, 'elapsedSeconds': round(time.monotonic() - started, 1),
        }
        return merged
    finally:
        resources.close()
        SCAN_SLOTS.release()
