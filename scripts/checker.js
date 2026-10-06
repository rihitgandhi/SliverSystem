(() => {
  'use strict';

  const form = document.getElementById('checker-form');
  const input = document.getElementById('checker-url');
  const error = document.getElementById('checker-error');
  const status = document.getElementById('checker-status');
  const results = document.getElementById('checker-results');
  const summary = document.getElementById('checker-summary');
  const issuesList = document.getElementById('checker-issues');
  const submit = form?.querySelector('button[type="submit"]');

  if (!form || !input || !error || !status || !results || !summary || !issuesList || !submit) return;

  function setHidden(element, hidden) {
    element.hidden = hidden;
  }

  function showError(message) {
    error.textContent = message;
    setHidden(error, false);
  }

  function clearError() {
    error.textContent = '';
    setHidden(error, true);
  }

  function normalizeUrl(value) {
    const trimmed = value.trim();
    if (!trimmed) {
      throw new Error('Enter a URL to scan.');
    }

    const candidate = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    let parsed;

    try {
      parsed = new URL(candidate);
    } catch (_) {
      throw new Error('Enter a valid URL, like https://example.com.');
    }

    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname || !parsed.hostname.includes('.')) {
      throw new Error('Enter a valid website URL, like https://example.com.');
    }

    return parsed.href;
  }

  function formatSummary(data) {
    const issues = Array.isArray(data?.issues) ? data.issues : [];
    const total = Number.isFinite(data?.totalIssues) ? data.totalIssues : issues.length;
    const severity = data?.severity || data?.severityCounts || {};
    const pieces = [];

    ['critical', 'serious', 'moderate', 'minor'].forEach((key) => {
      const value = Number(severity[key]);
      if (Number.isFinite(value) && value > 0) {
        pieces.push(`${value} ${key}`);
      }
    });

    const issueWord = total === 1 ? 'issue' : 'issues';
    return pieces.length ? `${total} ${issueWord} found — ${pieces.join(', ')}` : `${total} ${issueWord} found`;
  }

  function getIssueField(issue, keys, fallback) {
    for (const key of keys) {
      if (typeof issue?.[key] === 'string' && issue[key].trim()) return issue[key].trim();
    }
    return fallback;
  }

  function renderIssue(issue) {
    const item = document.createElement('article');
    item.className = 'checker-issue';

    const label = document.createElement('small');
    label.textContent = getIssueField(issue, ['type', 'rule', 'title', 'name'], 'Accessibility issue');

    const element = document.createElement('h3');
    element.textContent = getIssueField(issue, ['element', 'selector', 'target', 'node'], 'Affected element not specified');

    const explanation = document.createElement('p');
    explanation.textContent = getIssueField(issue, ['explanation', 'why', 'description', 'message'], 'No explanation was returned by the scanner.');

    const fix = document.createElement('p');
    fix.className = 'checker-fix';
    fix.textContent = getIssueField(issue, ['fix', 'suggestedFix', 'recommendation', 'help'], 'No suggested fix was returned by the scanner.');

    item.append(label, element, explanation, fix);
    return item;
  }

  function renderResults(data) {
    const issues = Array.isArray(data?.issues) ? data.issues : [];
    issuesList.replaceChildren();
    setHidden(results, false);

    if (!issues.length) {
      summary.textContent = 'No accessibility issues found.';
      const success = document.createElement('article');
      success.className = 'checker-success';
      const heading = document.createElement('h3');
      heading.textContent = 'No issues were returned for this scan.';
      const copy = document.createElement('p');
      copy.textContent = 'That is a good sign. Keep testing with real users, assistive technology, and accessibility standards as the site changes.';
      success.append(heading, copy);
      issuesList.append(success);
      return;
    }

    summary.textContent = formatSummary(data);
    issues.forEach((issue) => issuesList.append(renderIssue(issue)));
  }

  function setLoading(loading) {
    submit.disabled = loading;
    input.disabled = loading;
    setHidden(status, !loading);
  }

  async function scan(url) {
    // This calls our own backend endpoint, NOT the accessibility API directly. The backend endpoint is responsible for holding the real API key and calling the actual accessibility-checking API server-side, then returning results to this page. This keeps the API key private. [PLACEHOLDER: backend endpoint not yet built — this will 404 until the server-side piece exists]
    const response = await fetch('/api/check-accessibility', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      throw new Error('The checker backend is not available yet. The secure server-side endpoint still needs to be built before scans can run.');
    }

    return response.json();
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearError();
    issuesList.replaceChildren();
    setHidden(results, true);

    let url;
    try {
      url = normalizeUrl(input.value);
    } catch (validationError) {
      showError(validationError.message);
      input.focus();
      return;
    }

    setLoading(true);

    try {
      const data = await scan(url);
      renderResults(data);
    } catch (scanError) {
      showError(scanError.message || 'The scan failed. Try again later.');
    } finally {
      setLoading(false);
    }
  });
})();
