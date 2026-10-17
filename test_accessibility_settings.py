import json
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parent
STORAGE_KEY = "secondBrainAccessibilitySettings"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class AccessibilitySettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(QuietHandler, directory=str(REPO_ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.page = self.context.new_page()
        self.page.goto(f"{self.base_url}/test-suite.html", wait_until="networkidle")

    def tearDown(self):
        self.context.close()

    def open_panel(self):
        self.page.get_by_role("button", name="Open accessibility settings").click()
        panel = self.page.get_by_role("dialog", name="Accessibility")
        self.assertTrue(panel.is_visible())
        return panel

    def test_every_control_applies_and_reset_restores_defaults(self):
        panel = self.open_panel()

        self.page.locator('[name="fontScale"]').fill("200")
        self.assertEqual(self.page.locator("html").evaluate("el => getComputedStyle(el).fontSize"), "32px")
        self.assertEqual(panel.locator("output").inner_text(), "200%")

        self.page.locator('[name="contrast"]').select_option("dark")
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-contrast"), "dark")
        self.assertEqual(self.page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor"), "rgb(5, 7, 10)")

        self.page.locator('[name="spacing"]').check()
        self.assertNotEqual(self.page.locator("#test-copy").evaluate("el => getComputedStyle(el).letterSpacing"), "normal")

        self.page.locator('[name="readableFont"]').check()
        self.assertIn("Verdana", self.page.locator("body").evaluate("el => getComputedStyle(el).fontFamily"))

        self.page.locator('[name="underlineLinks"]').check()
        self.assertIn("underline", self.page.locator("#test-link").evaluate("el => getComputedStyle(el).textDecorationLine"))

        self.page.locator('[name="reducedMotion"]').check()
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-motion"), "reduce")
        self.assertEqual(self.page.evaluate("window.motionCalls.at(-1)"), "stop")
        self.page.locator('[name="reducedMotion"]').uncheck()
        self.assertEqual(self.page.evaluate("window.motionCalls.at(-1)"), "start")

        self.page.get_by_role("button", name="Reset all settings").click()
        self.assertEqual(self.page.locator("html").evaluate("el => getComputedStyle(el).fontSize"), "16px")
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-contrast"), "default")
        self.assertFalse(self.page.locator('[name="spacing"]').is_checked())
        self.assertFalse(self.page.locator('[name="readableFont"]').is_checked())
        self.assertFalse(self.page.locator('[name="underlineLinks"]').is_checked())
        self.assertFalse(self.page.locator('[name="reducedMotion"]').is_checked())

    def test_settings_persist_validate_and_dialog_keyboard_behavior(self):
        self.open_panel()
        close_button = self.page.get_by_role("button", name="Close accessibility settings", exact=True)
        self.assertEqual(self.page.evaluate("document.activeElement.getAttribute('aria-label')"), "Close accessibility settings")

        close_button.press("Shift+Tab")
        self.assertEqual(self.page.evaluate("document.activeElement.textContent.trim()"), "Reset all settings")
        self.page.get_by_role("button", name="Reset all settings").press("Tab")
        self.assertEqual(self.page.evaluate("document.activeElement.getAttribute('aria-label')"), "Close accessibility settings")

        self.page.locator('[name="fontScale"]').fill("170")
        self.page.locator('[name="contrast"]').select_option("high")
        self.page.locator('[name="spacing"]').check()
        self.page.reload(wait_until="networkidle")

        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-contrast"), "high")
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-spacing"), "true")
        self.assertEqual(self.page.locator("html").evaluate("el => getComputedStyle(el).fontSize"), "27.2px")

        self.open_panel()
        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.get_by_role("dialog", name="Accessibility").is_visible())
        self.assertEqual(self.page.evaluate("document.activeElement.getAttribute('aria-label')"), "Open accessibility settings")

        invalid = json.dumps({"fontScale": 999, "contrast": "unknown", "spacing": "true"})
        self.page.evaluate("([key, value]) => localStorage.setItem(key, value)", [STORAGE_KEY, invalid])
        self.page.reload(wait_until="networkidle")
        self.assertEqual(self.page.locator("html").evaluate("el => getComputedStyle(el).fontSize"), "32px")
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-contrast"), "default")
        self.assertEqual(self.page.locator("html").get_attribute("data-a11y-spacing"), "true")

    def test_panel_stays_usable_on_mobile_at_200_percent(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.open_panel()
        self.page.locator('[name="fontScale"]').fill("200")
        box = self.page.get_by_role("dialog", name="Accessibility").bounding_box()

        self.assertIsNotNone(box)
        self.assertGreaterEqual(box["x"], 0)
        self.assertGreaterEqual(box["y"], 0)
        self.assertLessEqual(box["x"] + box["width"], 390)
        self.assertLessEqual(box["y"] + box["height"], 844)
        self.assertTrue(self.page.get_by_role("button", name="Reset all settings").is_visible())

    def test_cached_legacy_widget_is_replaced_with_current_controls(self):
        self.page.evaluate(
            """() => new Promise((resolve, reject) => {
                document.querySelector('.accessibility-settings')?.remove();
                document.documentElement.dataset.a11yInitialized = 'true';
                document.body.insertAdjacentHTML('beforeend', `
                  <aside class="accessibility-settings">
                    <button class="accessibility-settings__toggle" type="button" aria-label="Open accessibility settings">Open</button>
                    <form class="accessibility-settings__panel" hidden>
                      <button class="accessibility-settings__reset" type="button">Reset</button>
                    </form>
                  </aside>
                `);
                const script = document.createElement('script');
                script.src = './scripts/accessibility-settings.js?v=4&legacy-test=1';
                script.onload = resolve;
                script.onerror = reject;
                document.body.append(script);
            })"""
        )

        widget = self.page.locator('.accessibility-settings')
        self.assertEqual(widget.get_attribute('data-accessibility-version'), '4')
        self.assertEqual(widget.count(), 1)
        self.open_panel()
        self.assertTrue(self.page.get_by_role('button', name='Close accessibility settings').is_visible())
        self.assertTrue(self.page.get_by_role('button', name='Reset all settings').is_visible())


if __name__ == "__main__":
    unittest.main()
