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


class AppEndpointCoverageTests(unittest.TestCase):
    """Additional tests to improve code-path coverage across all API endpoints."""

    def setUp(self):
        self.client = app_module.app.test_client()
        self._original_api_key = app_module.GEMINI_API_KEY
        app_module.conversations.clear()

    def tearDown(self):
        app_module.GEMINI_API_KEY = self._original_api_key
        app_module.conversations.clear()

    # ------------------------------------------------------------------ #
    # /api/health                                                          #
    # ------------------------------------------------------------------ #

    def test_health_api_key_configured_status(self):
        """Health endpoint reports 'configured' when API key is set."""
        app_module.GEMINI_API_KEY = "my-test-key"
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["api_key"], "configured")

    def test_health_api_key_not_configured_status(self):
        """Health endpoint reports 'not configured' when API key is empty."""
        app_module.GEMINI_API_KEY = ""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["api_key"], "not configured")

    # ------------------------------------------------------------------ #
    # /api/chat                                                            #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_chat_default_conversation_id(self, model_cls):
        """When conversation_id is omitted the endpoint uses 'default'."""
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("hi there")
        response = self.client.post("/api/chat", json={"message": "Hello"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["conversation_id"], "default")
        self.assertIn("default", app_module.conversations)

    @patch("app.genai.GenerativeModel")
    def test_chat_history_accumulates_across_requests(self, model_cls):
        """Each call appends user+assistant messages to the conversation history."""
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse("ok")
        cid = "hist_test"
        self.client.post("/api/chat", json={"message": "First", "conversation_id": cid})
        self.client.post("/api/chat", json={"message": "Second", "conversation_id": cid})
        history = app_module.conversations[cid]
        self.assertEqual(len(history), 4)  # 2 user + 2 assistant
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "First")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[2]["role"], "user")
        self.assertEqual(history[2]["content"], "Second")

    @patch("app.genai.GenerativeModel")
    def test_chat_history_limits_prompt_to_last_ten_messages(self, model_cls):
        """Prompt is built from the last 10 history entries so old messages are excluded."""
        app_module.GEMINI_API_KEY = "configured"
        # Pre-populate 11 messages so the oldest one should be dropped from the prompt
        app_module.conversations["trim"] = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"oldmsg{i}",
                "timestamp": "2024-01-01",
            }
            for i in range(11)
        ]
        captured = {}

        def fake_generate(prompt, **kwargs):
            captured["prompt"] = prompt
            return FakeGeminiResponse("reply")

        model_cls.return_value.generate_content.side_effect = fake_generate
        self.client.post("/api/chat", json={"message": "new", "conversation_id": "trim"})
        # The very first old message must not appear in the generated prompt
        self.assertNotIn("oldmsg0", captured.get("prompt", ""))

    # ------------------------------------------------------------------ #
    # /api/score                                                           #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_score_json_embedded_in_surrounding_text(self, model_cls):
        """JSON embedded in surrounding prose is extracted and parsed correctly."""
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            'Analysis complete:\n{"score": 82, "wcag_standards": {"non_compliant": []}}\nDone.'
        )
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 82)

    @patch("app.genai.GenerativeModel")
    def test_score_malformed_embedded_json_returns_fallback_score_65(self, model_cls):
        """When extracted JSON text cannot be parsed, fallback score of 65 is returned."""
        app_module.GEMINI_API_KEY = "configured"
        # Has braces (passes the regex) but is not valid JSON → triggers inner parse-error fallback
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            "{score: definitely-not-valid}"
        )
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 65)

    @patch("app.genai.GenerativeModel")
    def test_score_model_exception_returns_500(self, model_cls):
        """Unhandled model error in /api/score falls through to the outer handler → 500."""
        app_module.GEMINI_API_KEY = "configured"
        model_cls.return_value.generate_content.side_effect = Exception("API failure")
        response = self.client.post("/api/score", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    # ------------------------------------------------------------------ #
    # /api/score-details                                                   #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_score_details_model_exception_returns_500(self, model_cls):
        """Unhandled model error in /api/score-details returns 500 with error key."""
        model_cls.return_value.generate_content.side_effect = Exception("API failure")
        response = self.client.post(
            "/api/score-details",
            json={"url": "https://example.com", "non_compliant_standards": ["1.1.1"]},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())

    # ------------------------------------------------------------------ #
    # /api/alt-text                                                        #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_alt_text_raw_base64_without_data_prefix(self, model_cls):
        """Image data supplied as raw base64 (no data-URL prefix) is accepted."""
        import base64

        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"main_alt_text": "A red circle", "alternatives": ["circle", "shape", "red shape"]}'
        )
        raw_b64 = base64.b64encode(b"fake image bytes").decode()
        response = self.client.post(
            "/api/alt-text",
            json={"image": raw_b64, "detail_level": "concise"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["main_alt_text"], "A red circle")

    @patch("app.genai.GenerativeModel")
    def test_alt_text_detailed_level(self, model_cls):
        """detail_level='detailed' is accepted and response is returned successfully."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"main_alt_text": "Detailed description of a graph", "alternatives": ["a", "b", "c"]}'
        )
        response = self.client.post(
            "/api/alt-text",
            json={"image": "data:image/png;base64,aGVsbG8=", "detail_level": "detailed"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["main_alt_text"], "Detailed description of a graph")

    @patch("app.genai.GenerativeModel")
    def test_alt_text_with_context_and_tone(self, model_cls):
        """Optional context and tone parameters are forwarded without errors."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"main_alt_text": "A formal bar chart", "alternatives": ["chart", "graph", "data"]}'
        )
        response = self.client.post(
            "/api/alt-text",
            json={
                "image": "data:image/jpeg;base64,aGVsbG8=",
                "detail_level": "standard",
                "context": "Financial report",
                "tone": "formal",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("main_alt_text", response.get_json())

    # ------------------------------------------------------------------ #
    # /api/review-code                                                     #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_review_code_markdown_wrapped_json(self, model_cls):
        """JSON response wrapped in ```json fences is stripped and parsed correctly."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '```json\n{"score": 75, "issues": [], "recommendations": ["Use semantic HTML"]}\n```'
        )
        response = self.client.post(
            "/api/review-code", json={"code": "<div>text</div>", "code_type": "html"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 75)

    @patch("app.genai.GenerativeModel")
    def test_review_code_css_type(self, model_cls):
        """CSS code type is accepted and the response is returned successfully."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"score": 60, "issues": [], "recommendations": []}'
        )
        response = self.client.post(
            "/api/review-code",
            json={"code": "body { color: red; }", "code_type": "css"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["score"], 60)

    # ------------------------------------------------------------------ #
    # /api/simplify-content                                                #
    # ------------------------------------------------------------------ #

    @patch("app.genai.GenerativeModel")
    def test_simplify_content_markdown_wrapped_json(self, model_cls):
        """JSON response wrapped in ```json fences is stripped and parsed correctly."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '```json\n{"original_content":"Hard","simplified_content":"Easy","improvements":[]}\n```'
        )
        response = self.client.post(
            "/api/simplify-content",
            json={
                "content": "Hard text to simplify",
                "reading_level": "elementary",
                "simplification_level": "aggressive",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["simplified_content"], "Easy")

    @patch("app.genai.GenerativeModel")
    def test_simplify_content_college_reading_level(self, model_cls):
        """College reading level maps correctly and returns a successful response."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"original_content":"Text","simplified_content":"Cleaner text","improvements":["shorter sentences"]}'
        )
        response = self.client.post(
            "/api/simplify-content",
            json={
                "content": "Complex academic prose",
                "reading_level": "college",
                "simplification_level": "light",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("simplified_content", response.get_json())

    @patch("app.genai.GenerativeModel")
    def test_simplify_content_with_content_type_param(self, model_cls):
        """Optional content_type parameter is accepted without errors."""
        model_cls.return_value.generate_content.return_value = FakeGeminiResponse(
            '{"original_content":"Medical jargon","simplified_content":"Plain language","improvements":[]}'
        )
        response = self.client.post(
            "/api/simplify-content",
            json={
                "content": "Medical jargon heavy text",
                "reading_level": "middle",
                "simplification_level": "moderate",
                "content_type": "medical",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["simplified_content"], "Plain language")


if __name__ == "__main__":
    unittest.main()
