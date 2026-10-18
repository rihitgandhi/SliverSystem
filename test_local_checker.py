"""Regression checks for the local preview's connection to the real checker."""

import unittest
import os
import subprocess
import sys
from unittest.mock import patch

from app import app


class LocalCheckerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_local_preview_preflight_is_allowed(self):
        for origin in ('http://127.0.0.1:8877', 'http://localhost:8031'):
            with self.subTest(origin=origin):
                response = self.client.options('/api/check-accessibility', headers={
                    'Origin': origin,
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'content-type',
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), origin)

    def test_unrelated_origin_is_not_allowed(self):
        response = self.client.options('/api/check-accessibility', headers={
            'Origin': 'https://untrusted.example',
            'Access-Control-Request-Method': 'POST',
        })
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    @patch('ai_client.is_configured', return_value=False)
    @patch('rendered_audit.audit_rendered_page')
    @patch('web_audit.fetch_page')
    def test_scan_returns_real_markup_findings_without_ai(self, fetch_page, rendered, _configured):
        from rendered_audit import ScanUnavailable
        rendered.side_effect = ScanUnavailable('Browser unavailable for this test')
        fetch_page.return_value = {
            'ok': True, 'status': 200, 'final_url': 'https://example.com/',
            'html': '<html><head><title>Fixture</title></head><body><img src="photo.jpg"><input></body></html>',
        }
        response = self.client.post('/api/check-accessibility',
                                    json={'url': 'https://example.com/'},
                                    headers={'Origin': 'http://127.0.0.1:8877'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'http://127.0.0.1:8877')
        payload = response.get_json()
        self.assertFalse(payload['aiPowered'])
        rules = {issue['rule'] for issue in payload['issues']}
        self.assertIn('1.1.1', rules)
        self.assertIn('3.3.2', rules)
        self.assertEqual(payload['totalIssues'], len(payload['issues']))
        self.assertEqual(payload['scanStatus'], 'partial')

    @patch('app._checker_ai_analysis', return_value={
        'summary': 'Fix the missing image description first.',
        'topPriorities': [{
            'rule': '1.1.1', 'title': 'Describe the image',
            'why_it_matters': 'Screen reader users need an equivalent.',
            'first_step': 'Add an accurate alt attribute.',
        }],
        'manualReviewFocus': ['Check whether the description is meaningful.'],
        'limitations': 'Automated checks cannot prove full conformance.',
    })
    @patch('ai_client.is_configured', return_value=True)
    @patch('rendered_audit.audit_rendered_page')
    @patch('web_audit.fetch_page')
    def test_scan_includes_ai_explanation_when_configured(
            self, fetch_page, rendered, _configured, _analysis):
        from rendered_audit import ScanUnavailable
        rendered.side_effect = ScanUnavailable('Browser unavailable for this test')
        fetch_page.return_value = {
            'ok': True, 'status': 200, 'final_url': 'https://example.com/',
            'html': '<html lang="en"><head><title>Fixture</title></head><body><img src="photo.jpg"></body></html>',
        }
        response = self.client.post('/api/check-accessibility', json={'url': 'https://example.com/'})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['aiPowered'])
        self.assertEqual(payload['aiStatus'], 'complete')
        self.assertEqual(payload['aiAnalysis']['topPriorities'][0]['rule'], '1.1.1')

    def test_bad_payloads_return_validation_errors(self):
        for payload in ([], None, {'url': 123}, {'url': ''}):
            with self.subTest(payload=payload):
                response = self.client.post('/api/check-accessibility', json=payload)
                self.assertEqual(response.status_code, 400)

    @patch('web_audit.fetch_page', return_value={'ok': False, 'error': 'Private host blocked'})
    def test_blocked_scan_is_an_error_not_a_finding(self, _fetch):
        response = self.client.post('/api/check-accessibility', json={'url': 'http://127.0.0.1/'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('issues', response.get_json())

    @patch('web_audit.fetch_page', return_value={'ok': True, 'status': 403, 'html': '<h1>Denied</h1>'})
    def test_http_error_page_is_not_reported_as_the_target_website(self, _fetch):
        response = self.client.post('/api/check-accessibility', json={'url': 'https://example.com/'})
        self.assertEqual(response.status_code, 422)
        self.assertIn('HTTP 403', response.get_json()['error'])

    def test_production_checker_can_start_without_ai_credentials(self):
        environment = os.environ.copy()
        environment.update({'APP_ENV': 'production', 'FLASK_SECRET_KEY': 'deployment-test-secret'})
        for name in ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_DEPLOYMENT'):
            environment.pop(name, None)
        result = subprocess.run(
            [sys.executable, '-c', 'import config; assert config.APP_ENV == "production"'],
            cwd=os.path.dirname(__file__), env=environment, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
