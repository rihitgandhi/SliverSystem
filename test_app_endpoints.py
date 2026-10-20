"""Endpoint tests for the current Azure OpenAI-backed application."""

import base64
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


class AppEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_health_endpoint(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'healthy')

    def test_current_static_routes(self):
        for route in ('/', '/checker.html', '/learn.html', '/mission.html',
                      '/privacy.html', '/second-brain.html', '/second-brain-landing.html'):
            with self.subTest(route=route):
                response = self.client.get(route)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('text/html', response.content_type)
                finally:
                    response.close()

    def test_ai_endpoint_preflights(self):
        for route in ('/api/alt-text', '/api/review-code', '/api/simplify-content'):
            with self.subTest(route=route):
                response = self.client.options(route)
                self.assertEqual(response.status_code, 200)

    def test_ai_endpoint_validation(self):
        cases = (
            ('/api/alt-text', {}, 'No image provided'),
            ('/api/review-code', {'code': ''}, 'No code provided'),
            ('/api/simplify-content', {'content': ''}, 'No content provided'),
        )
        for route, payload, message in cases:
            with self.subTest(route=route):
                response = self.client.post(route, json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()['error'], message)

    @patch('ai_client.generate_json_with_image')
    @patch('ai_client.is_configured', return_value=True)
    def test_alt_text_uses_vision_model_and_preserves_evidence(self, _configured, generate):
        generate.return_value = {
            'main_alt_text': 'Blue bars compare three accessibility scores.',
            'alternatives': [],
            'wcag_pattern': 'complex',
            'pattern_rationale': 'The file analysis identifies a chart.',
            'long_description_recommended': True,
            'long_description_draft': 'Three bars show increasing scores.',
            'warnings': [],
            'html_snippet_suggestion': '<img src="chart.png" alt="Blue bars compare three accessibility scores.">',
        }
        encoded = base64.b64encode(Path('test_chart.png').read_bytes()).decode()
        response = self.client.post('/api/alt-text', json={
            'image': f'data:image/png;base64,{encoded}',
            'detail_level': 'concise',
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['wcag_pattern'], 'complex')
        self.assertTrue(payload['evidence']['ok'])
        self.assertEqual(generate.call_args.kwargs['mime_type'], 'image/png')

    @patch('ai_client.generate_json')
    @patch('ai_client.is_configured', return_value=True)
    def test_code_review_uses_ai_and_returns_lint_evidence(self, _configured, generate):
        generate.return_value = {
            'score': 72,
            'score_explanation': 'A missing image alternative lowers the score.',
            'summary_counts': {'critical': 0, 'high': 1, 'moderate': 0, 'low': 0},
            'issues': [],
            'recommendations': ['Add meaningful alternative text.'],
            'next_steps': 'Fix and retest.',
        }
        response = self.client.post('/api/review-code', json={
            'code': '<img src="photo.jpg">', 'code_type': 'html',
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['score'], 72)
        self.assertIn('evidence', payload)

    @patch('ai_client.generate_json')
    @patch('ai_client.is_configured', return_value=True)
    def test_content_simplifier_measures_ai_output(self, _configured, generate):
        generate.return_value = {
            'simplified_content': 'Teams must work together to make the plan succeed.',
            'improvements': ['Uses shorter words and a direct sentence.'],
            'jargon_replacements': [], 'preserved_facts': [], 'remaining_concerns': [],
        }
        response = self.client.post('/api/simplify-content', json={
            'content': ('The utilization of multifaceted methodologies necessitates '
                        'comprehensive stakeholder collaboration for implementation.'),
            'reading_level': 'middle',
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('before_evidence', payload)
        self.assertIn('after_evidence', payload)
        self.assertIn('deltas', payload)

    @patch('ai_client.is_configured', return_value=False)
    def test_ai_features_degrade_safely_without_credentials(self, _configured):
        review = self.client.post('/api/review-code', json={
            'code': '<button></button>', 'code_type': 'html',
        })
        simplify = self.client.post('/api/simplify-content', json={
            'content': 'A short sentence.',
        })
        self.assertEqual(review.status_code, 200)
        self.assertIn('evidence', review.get_json())
        self.assertEqual(simplify.status_code, 200)
        self.assertEqual(simplify.get_json()['_fallback_reason'], 'ai_not_configured')


if __name__ == '__main__':
    unittest.main()
