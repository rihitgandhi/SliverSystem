"""Regression tests for the Azure OpenAI client wrapper.

The historical filename is retained so existing test commands keep working.
"""

import unittest
from unittest.mock import patch

import ai_client


class AzureOpenAIClientTests(unittest.TestCase):
    def test_json_parser_accepts_plain_and_fenced_json(self):
        self.assertEqual(ai_client._coerce_json('{"ok": true}'), {'ok': True})
        self.assertEqual(ai_client._coerce_json('```json\n{"ok": true}\n```'), {'ok': True})

    def test_json_parser_rejects_non_json(self):
        with self.assertRaises(ValueError):
            ai_client._coerce_json('not structured output')

    def test_configuration_requires_endpoint_key_and_deployment(self):
        with patch.object(ai_client, 'AZURE_OPENAI_ENDPOINT', 'https://example.test/'), \
             patch.object(ai_client, 'AZURE_OPENAI_API_KEY', 'secret'), \
             patch.object(ai_client, 'AZURE_OPENAI_DEPLOYMENT', 'deployment'):
            self.assertTrue(ai_client.is_configured())
        with patch.object(ai_client, 'AZURE_OPENAI_API_KEY', ''):
            self.assertFalse(ai_client.is_configured())


if __name__ == '__main__':
    unittest.main()
