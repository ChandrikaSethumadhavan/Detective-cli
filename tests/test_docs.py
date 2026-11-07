import os
import unittest

from secret_finder.rules import RULES
from secret_finder.triage import PROMPT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class DocsTest(unittest.TestCase):
    def test_readme_is_short_and_covers_running_and_failures(self):
        text = read("README.md")
        self.assertLessEqual(len(text.splitlines()), 90)
        for needle in ("## How to run", "docker build", "docker run --rm -it", "pipx install", "#master", "@master",
                       "Try it on your own folder", "secret-finder scan --range HEAD", "runs locally",
                       "## Where it fails (gaps in this project)", "docs/usage.md", "docs/prompts.md"):
            self.assertIn(needle, text)

    def test_usage_guide_covers_the_options_the_readme_leaves_out(self):
        text = read("docs", "usage.md")
        for needle in ("--json", "--quiet", "--commit", "--range", "secret-finder demo", "pre-commit", "allowlist", "SF_AI_API_KEY"):
            self.assertIn(needle, text)

    def test_prompts_are_quoted_and_the_challenge_folder_is_not_published(self):
        self.assertIn("I need to first make a plan and plan the architecture", read("docs", "prompts.md"))
        self.assertIn("info/", read(".gitignore").splitlines())

    def test_prompt_file_matches_the_prompt_in_code(self):
        self.assertEqual(read("prompts", "triage.txt").strip(), PROMPT.strip())

    def test_log_exists_and_architecture_lists_every_rule(self):
        self.assertTrue(read("docs", "ai-log.md").strip())
        html = read("docs", "architecture.html")
        for rule in RULES:
            self.assertIn(f"<code>{rule.id}</code>", html)


if __name__ == "__main__":
    unittest.main()
