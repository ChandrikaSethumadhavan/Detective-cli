import os
import unittest

from secret_finder.rules import RULES
from secret_finder.triage import PROMPT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class DocsTest(unittest.TestCase):
    def test_readme_covers_install_use_and_ai(self):
        text = read("README.md")
        for needle in ("## Install", "pipx install", "docker build", "secret-finder scan", "--commit", "--json", "SF_AI_API_KEY", "secret-finder demo", "docker run --rm secret-finder demo", "runs locally"):
            self.assertIn(needle, text)
        self.assertIn("## Gaps in this project", text)

    def test_prompt_file_matches_the_prompt_in_code(self):
        self.assertEqual(read("prompts", "triage.txt").strip(), PROMPT.strip())

    def test_log_exists_and_architecture_lists_every_rule(self):
        self.assertTrue(read("docs", "ai-log.md").strip())
        html = read("docs", "architecture.html")
        for rule in RULES:
            self.assertIn(f"<code>{rule.id}</code>", html)


if __name__ == "__main__":
    unittest.main()
