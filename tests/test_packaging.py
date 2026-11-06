import os
import re
import unittest

from secret_finder import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class PackagingTest(unittest.TestCase):
    def test_console_script_points_at_a_real_function_and_all_packages_are_listed(self):
        text = read("pyproject.toml")
        self.assertIn('secret-finder = "secret_finder.cli:main"', text)
        self.assertTrue(callable(cli.main))
        listed = set(re.search(r"packages = \[(.*?)\]", text, re.S).group(1).replace('"', "").replace(" ", "").split(","))
        found = set()
        for dirpath, _, files in os.walk(os.path.join(ROOT, "secret_finder")):
            if "__init__.py" in files:
                found.add(os.path.relpath(dirpath, ROOT).replace(os.sep, "."))
        self.assertEqual(listed, found)

    def test_dockerfile_has_python_git_safe_directory_and_entrypoint(self):
        text = read("Dockerfile")
        self.assertRegex(text, r"(?m)^FROM python:")
        self.assertIn("install -y --no-install-recommends git", text)
        self.assertIn("safe.directory /repo", text)
        self.assertIn('ENTRYPOINT ["secret-finder"]', text)
        self.assertNotIn(".secretfinder", [line for line in text.splitlines() if line.startswith("COPY")])
        self.assertIn(".git", read(".dockerignore").splitlines())


if __name__ == "__main__":
    unittest.main()
