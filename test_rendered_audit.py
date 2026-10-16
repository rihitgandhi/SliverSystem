"""Real browser integration and regression tests for the detailed scan engine."""

import unittest
from unittest.mock import Mock, patch

from rendered_audit import PublicResources, audit_rendered_page, merge_axe_results
from web_audit import fetch_page


FIXTURE = '''<!doctype html><html><head><title>Accessibility fixture</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body { margin: 20px; background: white; color: #111; font: 16px Arial; }
#low { color: #aaa; background: white; }
#tiny { font-size: 9px; }
.target { display:inline-block; width:8px; height:8px; margin:0; padding:0; }
.wide { width: 600px; }
</style></head><body>
<h1>Fixture</h1><h3>Skipped heading</h3>
<p id="low">Low contrast text that should be detected from actual computed styles.</p>
<p id="tiny">Very small supporting text</p>
<img id="image-a" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">
<img id="image-b" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">
<input id="unlabeled"><button id="empty-button"></button><a id="empty-link" href="/next"></a>
<div role="checkbox" id="missing-state" tabindex="0">Option</div>
<table><tr><td>Heading</td><td>Other heading</td></tr><tr><td>Value</td><td>Value</td></tr></table>
<button class="target" aria-label="One"></button><button class="target" aria-label="Two"></button>
<div class="wide">Content wider than a narrow viewport</div>
<div id="shadow-host"></div>
<div id="custom-click" onclick="this.textContent='Activated'">Custom action</div>
<script>
document.querySelector('#shadow-host').attachShadow({mode:'open'}).innerHTML='<button id="shadow-button"></button>';
setTimeout(() => { const img = document.createElement('img'); img.id='dynamic-image';
img.src='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='; document.body.append(img); }, 100);
</script></body></html>'''


class RenderedAuditTests(unittest.TestCase):
    def test_resource_redirect_to_private_host_is_not_followed(self):
        resources = PublicResources()
        response = Mock(status_code=302, headers={'Location': 'http://127.0.0.1/secret'})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        resources.session.get = Mock(return_value=response)
        resources.is_public = lambda url: '127.0.0.1' not in url
        try:
            with self.assertRaises(ValueError):
                resources.fetch('https://public.example/')
            self.assertEqual(resources.session.get.call_count, 1)
        finally:
            resources.close()

    @patch('web_audit._is_private_host', side_effect=lambda host: host == '127.0.0.1')
    @patch('web_audit.requests.get')
    def test_initial_fetch_checks_redirect_destination(self, get, _private):
        get.return_value = Mock(status_code=302, headers={'Location': 'http://127.0.0.1/'})
        result = fetch_page('https://public.example/')
        self.assertFalse(result['ok'])
        self.assertEqual(get.call_count, 1)

    def test_merge_preserves_all_nodes_and_viewport_measurements(self):
        def report(viewport, kind):
            return {'viewport': viewport, 'result': {kind: [{
                'id': 'color-contrast', 'help': 'Contrast', 'tags': ['wcag143', 'wcag2aa'],
                'impact': 'serious', 'nodes': [{'target': [f'#text-{i}'], 'html': '<p>Text</p>',
                                               'failureSummary': viewport + ' contrast evidence'} for i in range(12)]
            }]}}
        merged = merge_axe_results([report('Desktop', 'violations'), report('Mobile', 'violations'),
                                    report('Mobile', 'incomplete')])
        self.assertEqual(len(merged['issues']), 12)
        self.assertEqual(len(merged['reviewItems']), 0)
        self.assertTrue(all(i['viewports'] == ['Desktop', 'Mobile'] for i in merged['issues']))
        self.assertEqual(merged['issues'][0]['wcag'], ['1.4.3'])
        self.assertEqual(len(merged['issues'][0]['evidence']), 2)

    def test_merge_uses_highest_impact_and_retains_other_viewport_reviews(self):
        def report(viewport, impact, kind):
            rule = {'id': 'contrast', 'help': 'Contrast', 'tags': ['wcag143', 'wcag2aa'],
                    'impact': impact, 'nodes': [{'target': ['#text'], 'impact': impact}]}
            return {'viewport': viewport, 'result': {kind: [rule], 'passes': [{'id': 'contrast'}]}}
        result = merge_axe_results([report('Desktop', 'minor', 'violations'),
                                    report('Mobile', 'critical', 'violations'),
                                    report('Narrow', None, 'incomplete')])
        self.assertEqual(result['issues'][0]['severity'], 'critical')
        self.assertEqual(result['reviewItems'][0]['viewports'], ['Narrow'])
        self.assertEqual(result['rulesPassed'], 0)
        self.assertEqual(result['rulesApplicable'], 1)

    def test_resource_cache_separates_mobile_and_desktop_responses(self):
        resources = PublicResources()
        resources.is_public = lambda url: True
        response = Mock(status_code=200, headers={'content-type': 'text/html'})
        response.iter_content.return_value = [b'<p>Page</p>']
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        resources.session.get = Mock(return_value=response)
        try:
            resources.fetch('https://public.example/', 'Desktop browser')
            resources.fetch('https://public.example/', 'Desktop browser')
            resources.fetch('https://public.example/', 'Mobile browser')
            self.assertEqual(resources.session.get.call_count, 2)
            self.assertEqual(resources.session.get.call_args.kwargs['headers']['User-Agent'], 'Mobile browser')
        finally:
            resources.close()

    @patch('rendered_audit._is_private_host', return_value=False)
    @patch.object(PublicResources, 'fetch', return_value=(200, {'content-type': 'text/html'}, FIXTURE.encode()))
    def test_real_browser_finds_rendered_css_dynamic_and_shadow_issues(self, _fetch, _private):
        result = audit_rendered_page('https://audit-fixture.example/')
        rules = {item['rule'] for item in result['issues']}
        self.assertTrue({'color-contrast', 'image-alt', 'button-name', 'label',
                         'html-has-lang', 'aria-required-attr'}.issubset(rules), rules)
        images = [i for i in result['issues'] if i['rule'] == 'image-alt']
        self.assertEqual(len(images), 3, images)
        self.assertTrue(any('dynamic-image' in i['element'] for i in images))
        self.assertTrue(any('shadow-button' in i['element'] for i in result['issues']))
        self.assertTrue(all(len(i['viewports']) == 3 for i in images))
        self.assertEqual([v['width'] for v in result['coverage']['viewports']], [1440, 390, 320])
        self.assertGreater(result['rulesChecked'], 80)
        self.assertTrue(all(v['completed'] for v in result['coverage']['viewports']))
        reviews = {i['rule'] for i in result['reviewItems']}
        self.assertIn('small-text-review', reviews)
        self.assertIn('reflow-review', reviews)
        self.assertIn('custom-control-keyboard-review', reviews)


if __name__ == '__main__':
    unittest.main()
