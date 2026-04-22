import unittest
from unittest.mock import patch

import app as app_module


class FakeGeminiResponse:
    def __init__(self, text):
        self.text = text


class AppEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self._original_api_key = app_module.GEMINI_API_KEY
        app_module.conversations.clear()

    def tearDown(self):
        app_module.GEMINI_API_KEY = self._original_api_key
        app_module.conversations.clear()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "healthy")
        self.assertIn("timestamp", payload)
        self.assertIn("api_key", payload)

    def test_static_routes(self):
        for route in ["/", "/chat.html", "/simple-chat.html", "/test-chatbot.html", "/score.html", "/help.html"]:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.content_type)
                self.assertIn("<html", response.get_data(as_text=True).lower())
                response.close()

    def test_chat_options(self):
        response = self.client.open("/api/chat", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_chat_empty_message_returns_400(self):
        response = self.client.post("/api/chat", json={"message": "", "conversation_id": "c1"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_chat_fallback_without_api_key_and_conversation_history(self):
        app_module.GEMINI_API_KEY = ""
        response = self.client.post("/api/chat", json={"message": "Hello", "conversation_id": "c1"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["conversation_id"], "c1")
        self.assertIn("disabled", payload["response"].lower())
        self.assertEqual(len(app_module.conversations["c1"]), 2)

    @patch("app.genai.GenerativeModel")
    def test_chat_with_model_response(self, model_cls):
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("assistant output")
        response = self.client.post("/api/chat", json={"message": "Hi", "conversation_id": "c2"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["response"], "assistant output")

    def test_chat_invalid_json_returns_500(self):
        response = self.client.post("/api/chat", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    def test_score_options(self):
        response = self.client.open("/api/score", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_score_non_json_returns_400(self):
        response = self.client.post("/api/score", data="url=https://example.com", content_type="text/plain")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Content-Type", response.get_json()["error"])

    def test_score_invalid_json_returns_400(self):
        response = self.client.post("/api/score", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON format", response.get_json()["error"])

    def test_score_missing_url_returns_400(self):
        response = self.client.post("/api/score", json={"url": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "No URL provided")

    def test_score_fallback_without_api_key(self):
        app_module.GEMINI_API_KEY = ""
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["score"], 50)
        self.assertIn("API_KEY_MISSING", payload["wcag_standards"]["non_compliant"])

    @patch("app.genai.GenerativeModel")
    def test_score_uses_model_when_api_key_present(self, model_cls):
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse('{"score": 88, "wcag_standards": {"non_compliant": []}}')
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 88)

    @patch("app.genai.GenerativeModel")
    def test_score_model_non_json_fallback(self, model_cls):
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("plain text response")
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 70)

    def test_score_details_options(self):
        response = self.client.open("/api/score-details", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_score_details_validation_errors(self):
        non_json = self.client.post("/api/score-details", data="x", content_type="text/plain")
        self.assertEqual(non_json.status_code, 400)

        invalid_json = self.client.post("/api/score-details", data="{", content_type="application/json")
        self.assertEqual(invalid_json.status_code, 400)

        no_url = self.client.post("/api/score-details", json={"url": "", "non_compliant_standards": ["1.1.1"]})
        self.assertEqual(no_url.status_code, 400)

        no_standards = self.client.post("/api/score-details", json={"url": "https://example.com", "non_compliant_standards": []})
        self.assertEqual(no_standards.status_code, 400)

    @patch("app.genai.GenerativeModel")
    def test_score_details_success_with_model_json(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse('{"summary": "ok", "fixes": []}')
        response = self.client.post(
            "/api/score-details",
            json={"url": "https://example.com", "non_compliant_standards": ["1.1.1"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["summary"], "ok")

    @patch("app.genai.GenerativeModel")
    def test_score_details_fallback_when_no_json_found(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("analysis without json")
        response = self.client.post(
            "/api/score-details",
            json={"url": "https://example.com", "non_compliant_standards": ["1.1.1"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("summary", response.get_json())

    @patch("app.genai.GenerativeModel")
    def test_score_details_parse_error_returns_500(self, model_cls):
        # Deliberately malformed JSON to exercise parse-error handling.
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse('{"key": invalid}')
        response = self.client.post(
            "/api/score-details",
            json={"url": "https://example.com", "non_compliant_standards": ["1.1.1"]},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    def test_cors_test_endpoint(self):
        options_resp = self.client.open("/api/cors-test", method="OPTIONS")
        self.assertEqual(options_resp.status_code, 200)
        get_resp = self.client.get("/api/cors-test", headers={"Origin": "https://example.com"})
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.get_json()["message"], "CORS test successful")

    @patch("app.genai.GenerativeModel")
    def test_alt_text_endpoint_success(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '```json\n{"main_alt_text":"A chart","alternatives":["a","b","c"]}\n```'
        )
        response = self.client.post(
            "/api/alt-text",
            json={"image": "data:image/jpeg;base64,aGVsbG8=", "detail_level": "standard"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["main_alt_text"], "A chart")

    def test_alt_text_endpoint_error(self):
        response = self.client.post("/api/alt-text", json={"image": "not-base64"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    def test_alt_text_options(self):
        response = self.client.open("/api/alt-text", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_review_code_options(self):
        response = self.client.open("/api/review-code", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    @patch("app.genai.GenerativeModel")
    def test_review_code_endpoint_success(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"score":90,"issues":[],"recommendations":["Good semantic markup"]}'
        )
        response = self.client.post("/api/review-code", json={"code": "<img alt='x'>", "code_type": "html"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 90)

    @patch("app.genai.GenerativeModel")
    def test_review_code_endpoint_error(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("invalid")
        response = self.client.post("/api/review-code", json={"code": "<img>", "code_type": "html"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    def test_simplify_content_options(self):
        response = self.client.open("/api/simplify-content", method="OPTIONS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    @patch("app.genai.GenerativeModel")
    def test_simplify_content_endpoint_success(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"original_content":"Hard text","simplified_content":"Simple text","improvements":["Shorter sentences"]}'
        )
        response = self.client.post(
            "/api/simplify-content",
            json={"content": "Hard text", "reading_level": "middle", "simplification_level": "moderate"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["simplified_content"], "Simple text")

    @patch("app.genai.GenerativeModel")
    def test_simplify_content_endpoint_error(self, model_cls):
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("invalid")
        response = self.client.post(
            "/api/simplify-content",
            json={"content": "Hard text", "reading_level": "middle", "simplification_level": "moderate"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
