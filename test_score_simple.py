"""Compatibility regression checks for the current website checker."""

import unittest

from app import app


class CheckerValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_checker_rejects_an_empty_url(self):
        response = self.client.post('/api/check-accessibility', json={'url': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error'], 'No URL provided')

    def test_checker_requires_json(self):
        response = self.client.post('/api/check-accessibility', data='url=https://example.com')
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
