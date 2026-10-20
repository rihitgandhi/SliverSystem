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
  const coverage = document.getElementById('checker-coverage');
  const warnings = document.getElementById('checker-warnings');
  const aiAnalysis = document.getElementById('checker-ai-analysis');
  const aiSummary = document.getElementById('checker-ai-summary');
  const aiPriorities = document.getElementById('checker-ai-priorities');
  const aiLimit = document.getElementById('checker-ai-limit');
  const filters = document.getElementById('checker-filters');
  const kindFilter = document.getElementById('checker-kind');
  const severityFilter = document.getElementById('checker-severity');
  const filterCount = document.getElementById('checker-filter-count');
  const manual = document.getElementById('checker-manual');
  const manualList = document.getElementById('checker-manual-list');
  const standardFilter = document.getElementById('checker-standard');
  const viewportFilter = document.getElementById('checker-viewport');
  const searchInput = document.getElementById('checker-search');
  const overview = document.getElementById('checker-overview');
  const priorities = document.getElementById('checker-priorities');
  const priorityList = document.getElementById('checker-priority-list');
  const reportActions = document.getElementById('checker-report-actions');
  const reportTools = window.CheckerReport;
  let currentReport = null;
  const isLocalPreview = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
  const configuredApiBase = document.querySelector('meta[name="checker-api-base"]')?.content.trim().replace(/\/+$/, '') || '';
  const apiBase = isLocalPreview
    ? (window.location.port === '5000' ? '' : 'http://127.0.0.1:5000')
    : configuredApiBase;

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

  function renderIssueGroup(issues, needsReview) {
    const issue = issues[0];
    const item = document.createElement('article');
    item.className = 'checker-issue';

    const label = document.createElement('small');
    const criteria = Array.isArray(issue.wcag) && issue.wcag.length ? ` · WCAG ${issue.wcag.join(', ')}` : '';
    const highestSeverity = ['critical', 'serious', 'moderate', 'minor'].find(severity => issues.some(i => i.severity === severity));
    label.textContent = `${needsReview ? 'Needs review' : highestSeverity || 'Finding'} · ${issue.standard || 'Markup check'}${criteria}`;

    const heading = document.createElement('h3');
    heading.textContent = getIssueField(issue, ['type', 'title', 'rule'], 'Accessibility finding');

    const explanation = document.createElement('p');
    explanation.textContent = getIssueField(issue, ['explanation', 'why', 'description', 'message'], 'No explanation was returned by the scanner.');

    const details = document.createElement('details');
    details.className = 'checker-occurrences';
    const detailSummary = document.createElement('summary');
    detailSummary.textContent = `${issues.length} affected ${issues.length === 1 ? 'element' : 'elements'} — locations and fixes`;
    details.append(detailSummary);
    issues.forEach((finding) => {
      const occurrence = document.createElement('div');
      occurrence.className = 'checker-occurrence';
      const location = document.createElement('code');
      location.className = 'checker-selector';
      location.textContent = finding.element || 'Page markup';
      const context = document.createElement('p');
      context.className = 'checker-occurrence-context';
      context.textContent = [finding.frame && finding.frame !== 'main' ? finding.frame : '',
        ...(finding.viewports || [])].filter(Boolean).join(' · ');
      const fix = document.createElement('p');
      fix.className = 'checker-fix';
      fix.textContent = finding.fix || finding.explanation;
      occurrence.append(location, context, fix);
      if (finding.html) {
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = finding.html;
        pre.append(code);
        occurrence.append(pre);
      }
      // Preserve viewport-specific measurements and fix instructions.
      if (Array.isArray(finding.evidence) && finding.evidence.length > 1) {
        finding.evidence.filter(e => e.detail && e.detail !== finding.fix).forEach((evidence) => {
          const detail = document.createElement('p');
          detail.textContent = `${evidence.viewport}: ${evidence.detail}`;
          occurrence.append(detail);
        });
      }
      details.append(occurrence);
    });
    item.append(label, heading, explanation, details);
    if (issue.helpUrl) {
      try {
        const helpUrl = new URL(issue.helpUrl);
        if (helpUrl.protocol === 'https:' && helpUrl.hostname === 'dequeuniversity.com') {
          const link = document.createElement('a');
          link.href = helpUrl.href;
          link.textContent = 'Read the rule and examples ↗';
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          item.append(link);
        }
      } catch (_) {}
    }
    return item;
  }

  function renderFilteredResults() {
    const needsReview = kindFilter?.value === 'review';
    if (!currentReport) return;
    const issues = reportTools.filter(currentReport, {
      kind: kindFilter?.value, severity: severityFilter?.value,
      standard: standardFilter?.value, viewport: viewportFilter?.value, search: searchInput?.value,
    });
    const groups = reportTools.groups(issues);
    issuesList.replaceChildren();
    if (filterCount) {
      const noun = needsReview ? 'review item' : 'finding';
      filterCount.textContent = `${issues.length} ${noun}${issues.length === 1 ? '' : 's'} across ${groups.length} check${groups.length === 1 ? '' : 's'}`;
    }
    if (!issues.length) {
      const success = document.createElement('article');
      success.className = 'checker-success';
      const heading = document.createElement('h3');
      heading.textContent = needsReview ? 'No items match this review filter.' : 'No detected findings match this filter.';
      const copy = document.createElement('p');
      copy.textContent = 'Try another search or reset the filters. A report without automated findings still needs the human checks listed below.';
      success.append(heading, copy);
      issuesList.append(success);
      return;
    }
    groups.forEach(group => issuesList.append(renderIssueGroup(group, needsReview)));
  }

  function resetFilters(kind = 'confirmed') {
    if (kindFilter) kindFilter.value = kind;
    [severityFilter, standardFilter, viewportFilter].forEach(filter => { if (filter) filter.value = 'all'; });
    if (searchInput) searchInput.value = '';
  }

  function renderOverview(data) {
    if (!overview || !priorities || !priorityList) return;
    overview.replaceChildren();
    const counts = reportTools.counts(data);
    const categories = [
      [counts.aa + counts.markup, counts.markup ? 'Markup findings' : 'A/AA findings', counts.markup ? 'Markup check' : 'WCAG A/AA'],
      [counts.aaa, 'AAA enhancements', 'Enhanced (AAA)'],
      [counts.best, 'Best practices', 'Best practice'],
      [counts.review, 'Needs review', 'review'],
    ];
    categories.forEach(([count, title, standard]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('aria-label', `Show ${title.toLowerCase()} (${count})`);
      const number = document.createElement('strong');
      number.textContent = count;
      const label = document.createElement('span');
      label.textContent = title;
      button.append(number, label);
      button.addEventListener('click', () => {
        resetFilters(standard === 'review' ? 'review' : 'confirmed');
        if (standard !== 'review') standardFilter.value = standard;
        renderFilteredResults();
      });
      overview.append(button);
    });
    setHidden(overview, false);
    priorityList.replaceChildren();
    reportTools.groups(data.issues || []).slice(0, 3).forEach(group => {
      const li = document.createElement('li');
      const copy = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = group[0].type;
      const context = document.createElement('span');
      context.textContent = `${group.length} affected ${group.length === 1 ? 'element' : 'elements'} · ${group[0].standard || 'Markup check'}`;
      copy.append(title, context);
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Show findings';
      button.setAttribute('aria-label', `Show findings: ${group[0].type}`);
      button.addEventListener('click', () => {
        resetFilters();
        searchInput.value = group[0].rule || group[0].type;
        renderFilteredResults();
        const details = issuesList.querySelector('details');
        if (details) details.open = true;
        issuesList.scrollIntoView({block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      });
      li.append(copy, button);
      priorityList.append(li);
    });
    setHidden(priorities, !(data.issues || []).length);
    if (reportActions) setHidden(reportActions, false);
  }

  function downloadReport(format) {
    if (!currentReport) return;
    const content = format === 'csv' ? '\ufeff' + reportTools.csv(currentReport) : JSON.stringify(currentReport, null, 2);
    const blob = new Blob([content], {type: format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    let hostname = 'website';
    try { hostname = new URL(currentReport.finalUrl || currentReport.url).hostname.replace(/[^a-z0-9.-]/gi, '-'); } catch (_) {}
    link.href = url;
    link.download = `accessibility-${hostname}-${(currentReport.scannedAt || new Date().toISOString()).slice(0, 10)}.${format}`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportPdf() {
    if (!currentReport) return;
    const printWindow = window.open('', '_blank', 'width=960,height=720');
    if (!printWindow) {
      showError('Your browser blocked the PDF window. Allow pop-ups for this site, then try again.');
      return;
    }
    printWindow.opener = null;
    printWindow.document.open();
    printWindow.document.write(reportTools.pdfHtml(currentReport));
    printWindow.document.close();
  }

  function renderResults(data) {
    currentReport = data;
    setHidden(results, false);
    summary.textContent = formatSummary(data);
    const scan = data.coverage || {};
    const completed = (scan.viewports || []).filter(v => v.completed).map(v => `${v.name} ${v.width}px`);
    if (coverage) coverage.textContent = [
      data.scanStatus === 'partial' ? 'Partial scan' : 'Rendered page scan',
      data.rulesChecked ? `${data.rulesChecked} checks considered${data.rulesApplicable != null ? `; ${data.rulesApplicable} apply to this page` : ''}` : scan.engine,
      completed.join(' + '),
      `${data.reviewCount || 0} ${(data.reviewCount || 0) === 1 ? 'item needs' : 'items need'} human review`,
      'This page only; A/AA, available AAA checks, and best practices.',
    ].filter(Boolean).join(' · ');
    if (warnings) {
      warnings.replaceChildren();
      (scan.warnings || []).forEach(message => {
        const p = document.createElement('p');
        p.textContent = message;
        warnings.append(p);
      });
      setHidden(warnings, !(scan.warnings || []).length);
    }
    if (aiAnalysis && aiSummary && aiPriorities && aiLimit) {
      aiPriorities.replaceChildren();
      if (data.aiPowered && data.aiAnalysis) {
        aiSummary.textContent = data.aiAnalysis.summary || '';
        (data.aiAnalysis.topPriorities || []).forEach(priority => {
          const item = document.createElement('li');
          const title = document.createElement('strong');
          title.textContent = priority.title || priority.rule || 'Priority finding';
          const impact = document.createElement('p');
          impact.textContent = priority.why_it_matters || '';
          const step = document.createElement('p');
          step.textContent = priority.first_step ? `First step: ${priority.first_step}` : '';
          item.append(title, impact, step);
          aiPriorities.append(item);
        });
        aiLimit.textContent = data.aiAnalysis.limitations || '';
        setHidden(aiAnalysis, false);
      } else {
        setHidden(aiAnalysis, true);
      }
    }
    if (kindFilter) {
      kindFilter.value = 'confirmed';
      kindFilter.options[0].textContent = `Detected findings (${data.totalIssues || 0})`;
      kindFilter.options[1].textContent = `Needs human review (${data.reviewCount || 0})`;
    }
    if (severityFilter) severityFilter.value = 'all';
    resetFilters();
    if (filters) setHidden(filters, false);
    if (manual && manualList) {
      manualList.replaceChildren();
      (scan.manualChecks || []).forEach(message => {
        const li = document.createElement('li');
        li.textContent = message;
        manualList.append(li);
      });
      setHidden(manual, false);
    }
    renderOverview(data);
    renderFilteredResults();
  }

  kindFilter?.addEventListener('change', renderFilteredResults);
  severityFilter?.addEventListener('change', renderFilteredResults);
  standardFilter?.addEventListener('change', renderFilteredResults);
  viewportFilter?.addEventListener('change', renderFilteredResults);
  let searchTimer;
  searchInput?.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(renderFilteredResults, 150);
  });
  document.getElementById('checker-reset-filters')?.addEventListener('click', () => { resetFilters(); renderFilteredResults(); });
  document.getElementById('checker-download-pdf')?.addEventListener('click', exportPdf);
  document.getElementById('checker-download-json')?.addEventListener('click', () => downloadReport('json'));
  document.getElementById('checker-download-csv')?.addEventListener('click', () => downloadReport('csv'));
  document.getElementById('checker-expand-all')?.addEventListener('click', () => { issuesList.querySelectorAll('details').forEach(d => { d.open = true; }); });
  document.getElementById('checker-collapse-all')?.addEventListener('click', () => { issuesList.querySelectorAll('details').forEach(d => { d.open = false; }); });

  function setLoading(loading) {
    submit.disabled = loading;
    input.disabled = loading;
    setHidden(status, !loading);
  }

  async function scan(url) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 150000);
    try {
      let response;
      let networkError;

      // Vercel may briefly drop a connection while a container wakes up or a
      // new deployment is promoted. Scans are read-only, so one retry is safe
      // and prevents a transient platform hand-off from becoming a dead end.
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          response = await fetch(`${apiBase}/api/check-accessibility`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
            signal: controller.signal,
            cache: 'no-store',
          });
          networkError = null;
        } catch (error) {
          networkError = error;
        }

        const retryableStatus = response && [502, 503, 504].includes(response.status);
        if (attempt === 0 && (networkError instanceof TypeError || retryableStatus)) {
          await new Promise(resolve => setTimeout(resolve, 1200));
          response = undefined;
          continue;
        }
        break;
      }

      if (networkError) throw networkError;
      if (!response) throw new TypeError('No response from checker');

      if (!response.ok) {
        let message = 'The checker could not complete the scan. Try again in a moment.';
        try {
          const payload = await response.json();
          if (payload?.error) message = payload.error;
        } catch (_) {}
        throw new Error(message);
      }

      return await response.json();
    } catch (scanError) {
      if (scanError.name === 'AbortError') throw new Error('The scan took too long. Try again in a moment.');
      if (scanError instanceof TypeError && isLocalPreview) throw new Error('Cannot reach the checker. Make sure the local API service is running, then try again.');
      if (scanError instanceof TypeError) throw new Error('The checker temporarily lost its connection. Please try the scan again.');
      throw scanError;
    } finally {
      clearTimeout(timeout);
    }
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
