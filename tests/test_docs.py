import os
import unittest

from secret_finder.rules import RULES
from secret_finder.triage import PROMPT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class DocsTest(unittest.TestCase):
    def test_readme_covers_running_ai_and_failures(self):
        text = read("README.md")
        for needle in ("python3 -m secret_finder scan", "--commit", "--json", "SF_AI_API_KEY", "## Where it fails"):
            self.assertIn(needle, text)

    def test_prompt_file_matches_the_prompt_in_code(self):
        self.assertEqual(read("prompts", "triage.txt").strip(), PROMPT.strip())

    def test_log_exists_and_architecture_lists_every_rule(self):
        self.assertTrue(read("docs", "ai-log.md").strip())
        html = read("docs", "architecture.html")
        for rule in RULES:
            self.assertIn(f"<code>{rule.id}</code>", html)


if __name__ == "__main__":
    unittest.main()
