/* Report operations shared by the page and regression tests. */
((root) => {
  'use strict';
  const severityRank = { critical: 0, serious: 1, moderate: 2, minor: 3 };
  const standardRank = { 'WCAG A/AA': 0, 'Markup check': 1, 'Best practice': 2, 'Enhanced (AAA)': 3 };

  function groups(findings) {
    const grouped = new Map();
    findings.forEach(finding => {
      const key = `${finding.engine || ''}:${finding.rule || finding.type}:${finding.standard || ''}`;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(finding);
    });
    return [...grouped.values()].sort((a, b) =>
      (standardRank[a[0].standard || 'Markup check'] ?? 4) - (standardRank[b[0].standard || 'Markup check'] ?? 4) ||
      Math.min(...a.map(i => severityRank[i.severity] ?? 3)) - Math.min(...b.map(i => severityRank[i.severity] ?? 3)) ||
      b.length - a.length || String(a[0].type).localeCompare(String(b[0].type)));
  }

  function filter(report, options = {}) {
    const list = options.kind === 'review' ? report.reviewItems : report.issues;
    const words = (options.search || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
    return (Array.isArray(list) ? list : []).filter(issue => {
      if (options.severity && options.severity !== 'all' && issue.severity !== options.severity) return false;
      if (options.standard && options.standard !== 'all' && (issue.standard || 'Markup check') !== options.standard) return false;
      if (options.viewport && options.viewport !== 'all' &&
          !(issue.viewports || []).some(v => v === options.viewport || v.startsWith(options.viewport + ' ('))) return false;
      const text = [issue.type, issue.rule, issue.element, issue.explanation, issue.fix,
        ...(issue.wcag || []), ...(issue.viewports || [])].join(' ').toLowerCase();
      return words.every(word => text.includes(word));
    });
  }

  function counts(report) {
    const issues = Array.isArray(report.issues) ? report.issues : [];
    const count = standard => issues.filter(i => i.standard === standard).length;
    return { aa: count('WCAG A/AA'), aaa: count('Enhanced (AAA)'), best: count('Best practice'),
      markup: issues.filter(i => !i.standard || i.standard === 'Markup check').length,
      review: (report.reviewItems || []).length };
  }

  function csv(report) {
    const cell = value => {
      let text = value == null ? '' : String(value);
      // Treat untrusted page text as literal data when opened in a spreadsheet.
      if (/^\s*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
      return '"' + text.replace(/"/g, '""') + '"';
    };
    const rows = [['Status', 'Severity', 'Standard', 'Rule', 'WCAG', 'Finding', 'Element',
      'Frame', 'Viewports', 'Explanation', 'Fix', 'HTML', 'Reference', 'Scanned URL', 'Scanned at',
      'Viewport evidence', 'Scan coverage', 'Scan status']];
    const coverage = JSON.stringify({...report.coverage, rulesChecked: report.rulesChecked,
      rulesApplicable: report.rulesApplicable, rulesPassed: report.rulesPassed});
    const summary = Array(rows[0].length).fill('');
    summary[0] = 'Scan summary';
    summary[5] = `${(report.issues || []).length} detected findings; ${(report.reviewItems || []).length} review items`;
    summary[13] = report.finalUrl || report.url;
    summary[14] = report.scannedAt;
    summary[16] = coverage;
    summary[17] = report.scanStatus;
    rows.push(summary);
    for (const [status, findings] of [['Detected', report.issues], ['Needs review', report.reviewItems]]) {
      (findings || []).forEach(issue => rows.push([status, issue.severity, issue.standard, issue.rule,
        (issue.wcag || []).join(', '), issue.type, issue.element, issue.frame,
        (issue.viewports || []).join('; '), issue.explanation, issue.fix, issue.html, issue.helpUrl,
        report.finalUrl || report.url, report.scannedAt,
        (issue.evidence || []).map(e => `${e.viewport}: ${e.detail}`).join('\n'), coverage, report.scanStatus]));
    }
    return rows.map(row => row.map(cell).join(',')).join('\r\n');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function pdfHtml(report) {
    const detected = Array.isArray(report.issues) ? report.issues : [];
    const review = Array.isArray(report.reviewItems) ? report.reviewItems : [];
    const coverage = report.coverage || {};
    const scannedUrl = report.finalUrl || report.url || 'Unknown URL';
    const scannedAt = report.scannedAt || '';
    const severityRows = ['critical', 'serious', 'moderate', 'minor']
      .map(severity => [severity, detected.filter(issue => issue.severity === severity).length])
      .filter(([, total]) => total > 0)
      .map(([severity, total]) => `<span><strong>${total}</strong> ${escapeHtml(severity)}</span>`)
      .join('');

    const renderList = (items) => items.length
      ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
      : '<p>None reported.</p>';

    const renderGroups = (items, needsReview) => {
      if (!items.length) return '<p class="empty">None reported.</p>';
      return groups(items).map(group => {
        const issue = group[0] || {};
        const criteria = Array.isArray(issue.wcag) && issue.wcag.length ? ` · WCAG ${issue.wcag.join(', ')}` : '';
        const label = `${needsReview ? 'Needs review' : issue.severity || 'Finding'} · ${issue.standard || 'Markup check'}${criteria}`;
        const title = issue.type || issue.title || issue.rule || 'Accessibility finding';
        const explanation = issue.explanation || issue.why || issue.description || issue.message || 'No explanation was returned by the scanner.';
        const occurrences = group.map(finding => {
          const location = finding.element || 'Page markup';
          const context = [finding.frame && finding.frame !== 'main' ? finding.frame : '', ...(finding.viewports || [])].filter(Boolean).join(' · ');
          const fix = finding.fix || finding.explanation || '';
          const markup = finding.html ? `<pre><code>${escapeHtml(finding.html)}</code></pre>` : '';
          const evidence = Array.isArray(finding.evidence)
            ? finding.evidence.filter(item => item && item.detail).map(item => `<li>${escapeHtml(`${item.viewport || 'Evidence'}: ${item.detail}`)}</li>`).join('')
            : '';
          return `<div class="occurrence">
            <code class="selector">${escapeHtml(location)}</code>
            ${context ? `<p class="context">${escapeHtml(context)}</p>` : ''}
            ${fix ? `<p><strong>Fix:</strong> ${escapeHtml(fix)}</p>` : ''}
            ${markup}
            ${evidence ? `<ul class="evidence">${evidence}</ul>` : ''}
          </div>`;
        }).join('');
        return `<article class="finding">
          <p class="label">${escapeHtml(label)}</p>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(explanation)}</p>
          <p class="occurrence-count">${group.length} affected ${group.length === 1 ? 'element' : 'elements'}</p>
          ${occurrences}
        </article>`;
      }).join('');
    };

    const viewportSummary = Array.isArray(coverage.viewports)
      ? coverage.viewports.map(viewport => `${viewport.name || viewport.viewport || 'Viewport'}${viewport.width ? ` ${viewport.width}px` : ''}: ${viewport.completed === false ? 'incomplete' : 'completed'}`)
      : [];
    const coverageFacts = [
      coverage.engine ? `Engine: ${coverage.engine}` : '',
      report.rulesChecked != null ? `Checks considered: ${report.rulesChecked}` : '',
      report.rulesApplicable != null ? `Applicable checks: ${report.rulesApplicable}` : '',
      report.rulesPassed != null ? `Passed checks: ${report.rulesPassed}` : '',
      ...viewportSummary,
    ].filter(Boolean);
    const ai = report.aiPowered && report.aiAnalysis ? report.aiAnalysis : null;
    const aiPriorities = ai && Array.isArray(ai.topPriorities)
      ? ai.topPriorities.map(priority => `<li><strong>${escapeHtml(priority.title || priority.rule || 'Priority finding')}</strong>${priority.why_it_matters ? `<p>${escapeHtml(priority.why_it_matters)}</p>` : ''}${priority.first_step ? `<p><strong>First step:</strong> ${escapeHtml(priority.first_step)}</p>` : ''}</li>`).join('')
      : '';

    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AccessAI Accessibility Report</title>
  <style>
    @page { size: A4; margin: 16mm; }
    * { box-sizing: border-box; }
    body { margin: 0; color: #17202b; font: 10pt/1.5 Arial, sans-serif; }
    h1, h2, h3, p { margin-top: 0; }
    h1 { margin-bottom: 8px; font-size: 25pt; line-height: 1.05; }
    h2 { margin: 28px 0 12px; border-bottom: 2px solid #075fc9; padding-bottom: 7px; font-size: 16pt; }
    h3 { margin-bottom: 6px; font-size: 12pt; }
    ul, ol { margin-top: 6px; padding-left: 20px; }
    .meta { margin: 20px 0; border: 1px solid #cfd8e3; border-radius: 8px; padding: 14px; background: #f5f8fc; }
    .meta p { margin-bottom: 4px; }
    .counts { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 12px; text-transform: capitalize; }
    .finding { break-inside: avoid; margin-bottom: 18px; border: 1px solid #d8dee7; border-radius: 8px; padding: 14px; }
    .label { margin-bottom: 7px; color: #075fc9; font-size: 8pt; font-weight: 700; text-transform: uppercase; }
    .occurrence-count { margin: 10px 0 6px; font-weight: 700; }
    .occurrence { break-inside: avoid; margin-top: 8px; border-top: 1px solid #e2e6ec; padding-top: 9px; }
    .occurrence p { margin: 5px 0; }
    .selector { display: block; overflow-wrap: anywhere; color: #202b37; font-weight: 700; }
    .context { color: #596675; font-size: 8.5pt; }
    pre { overflow-wrap: anywhere; white-space: pre-wrap; border-radius: 5px; padding: 8px; background: #f3f5f8; font-size: 8pt; }
    .evidence { font-size: 8.5pt; }
    .empty { color: #596675; font-style: italic; }
    .footer { margin-top: 30px; border-top: 1px solid #cfd8e3; padding-top: 10px; color: #596675; font-size: 8pt; }
    @media print { body { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
  </style>
</head>
<body>
  <header>
    <h1>AccessAI Accessibility Report</h1>
    <p>Automated findings and human-review guidance for one rendered page.</p>
  </header>
  <section class="meta">
    <p><strong>Scanned URL:</strong> ${escapeHtml(scannedUrl)}</p>
    <p><strong>Scanned at:</strong> ${escapeHtml(scannedAt || 'Not provided')}</p>
    <p><strong>Scan status:</strong> ${escapeHtml(report.scanStatus || 'unknown')}</p>
    <p><strong>Summary:</strong> ${detected.length} detected ${detected.length === 1 ? 'finding' : 'findings'}; ${review.length} ${review.length === 1 ? 'item' : 'items'} needing human review.</p>
    ${severityRows ? `<div class="counts">${severityRows}</div>` : ''}
  </section>
  <section>
    <h2>Scan Coverage</h2>
    ${renderList(coverageFacts)}
    <h3>Warnings</h3>
    ${renderList(Array.isArray(coverage.warnings) ? coverage.warnings : [])}
  </section>
  ${ai ? `<section><h2>AI Explanation</h2><p>${escapeHtml(ai.summary || '')}</p>${aiPriorities ? `<ol>${aiPriorities}</ol>` : ''}${ai.limitations ? `<p><strong>Limitations:</strong> ${escapeHtml(ai.limitations)}</p>` : ''}</section>` : ''}
  <section>
    <h2>Detected Findings</h2>
    ${renderGroups(detected, false)}
  </section>
  <section>
    <h2>Needs Human Review</h2>
    ${renderGroups(review, true)}
  </section>
  <section>
    <h2>Manual Checks</h2>
    ${renderList(Array.isArray(coverage.manualChecks) ? coverage.manualChecks : [])}
  </section>
  <p class="footer">Automated testing cannot establish full accessibility or find every problem. Review the page with assistive technology and people with disabilities.</p>
  <script>window.addEventListener('load', function () { setTimeout(function () { window.focus(); window.print(); }, 150); });<\/script>
</body>
</html>`;
  }

  const api = { groups, filter, counts, csv, pdfHtml };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CheckerReport = api;
})(typeof window !== 'undefined' ? window : globalThis);
