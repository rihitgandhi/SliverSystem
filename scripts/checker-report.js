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

  const api = { groups, filter, counts, csv };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CheckerReport = api;
})(typeof window !== 'undefined' ? window : globalThis);
