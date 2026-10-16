const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const reportTools = require('./scripts/checker-report.js');

const report = {
  url: 'https://example.com/', scannedAt: '2026-10-15T22:00:00Z', scanStatus: 'complete',
  coverage: {engine: 'axe-core', warnings: [], manualChecks: ['Test the keyboard']},
  issues: [
    {rule:'contrast-aaa', type:'Enhanced contrast', standard:'Enhanced (AAA)', severity:'serious', element:'#fine', viewports:['Desktop (1440 × 900)']},
    {rule:'button-name', type:'Button needs a name', standard:'WCAG A/AA', severity:'critical', element:'#submit', explanation:'Empty name', fix:'Add a label', viewports:['Mobile (390 × 844)']},
    {rule:'button-name', type:'Button needs a name', standard:'WCAG A/AA', severity:'critical', element:'#next', fix:'Add a label', viewports:['Mobile (390 × 844)']},
    {rule:'region', type:'Content landmarks', standard:'Best practice', severity:'moderate', element:'main', viewports:['Desktop (1440 × 900)']},
  ],
  reviewItems: [{rule:'keyboard-review', type:'Review click action', standard:'Human review', severity:'minor', element:'#action', viewports:['Narrow (320 × 800)']}],
};

test('combined filters search fixes and select the requested screen and standard', () => {
  const selected = reportTools.filter(report, {kind:'confirmed', standard:'WCAG A/AA', severity:'critical', viewport:'Mobile', search:'label submit'});
  assert.equal(selected.length, 1);
  assert.equal(selected[0].element, '#submit');
  assert.equal(reportTools.filter(report, {viewport:'Desktop', standard:'WCAG A/AA'}).length, 0);
  assert.equal(reportTools.filter(report, {kind:'review', viewport:'Narrow'}).length, 1);
});

test('priorities put A/AA barriers before AAA recommendations without losing occurrences', () => {
  const grouped = reportTools.groups(report.issues);
  assert.equal(grouped[0][0].rule, 'button-name');
  assert.equal(grouped[0].length, 2);
  assert.equal(grouped.at(-1)[0].standard, 'Enhanced (AAA)');
  assert.equal(grouped.flat().length, report.issues.length);
  assert.equal(report.issues[0].rule, 'contrast-aaa');
});

test('category counts keep recommendations and reviews separate from A/AA findings', () => {
  assert.deepEqual(reportTools.counts(report), {aa:2, aaa:1, best:1, markup:0, review:1});
});

test('CSV includes all findings, review items and coverage regardless of an earlier filter', () => {
  reportTools.filter(report, {severity:'critical'});
  const csv = reportTools.csv(report);
  assert.equal((csv.match(/"Detected",/g) || []).length, 4);
  assert.equal((csv.match(/"Needs review",/g) || []).length, 1);
  assert.ok(csv.includes('Test the keyboard'));
  assert.ok(csv.includes('Scan summary'));
});

test('CSV safely quotes multiline markup and treats spreadsheet formulas as literal text', () => {
  const csv = reportTools.csv({issues:[{type:'=SUM(1,2)', html:'<a title="Hello">\nText</a>', fix:'+unsafe'}]});
  assert.ok(csv.includes('"\'=SUM(1,2)"'));
  assert.ok(csv.includes('"\'+unsafe"'));
  assert.ok(csv.includes('<a title=""Hello"">\nText</a>'));
});

test('a clean report still exports scope and scan status', () => {
  const csv = reportTools.csv({issues:[], reviewItems:[], scanStatus:'partial', coverage:{warnings:['Styles not loaded']}});
  assert.ok(csv.includes('Styles not loaded'));
  assert.ok(csv.includes('"partial"'));
  assert.ok(csv.includes('0 detected findings; 0 review items'));
});

test('published checker points to the Render API while local previews stay local', () => {
  const html = fs.readFileSync('./checker.html', 'utf8');
  const script = fs.readFileSync('./scripts/checker.js', 'utf8');
  assert.match(html, /name="checker-api-base" content="https:\/\/sliversystem-backend\.onrender\.com"/);
  assert.match(script, /meta\[name="checker-api-base"\]/);
  assert.match(script, /http:\/\/127\.0\.0\.1:5000/);
});
