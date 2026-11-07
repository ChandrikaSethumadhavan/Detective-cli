import contextlib
import glob
import io
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from secret_finder import menu
from secret_finder.cli import main

AWS = "AKIAIOSFODNN7EXAMPLE"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=ENV).stdout.strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def drive(answers):
    out = io.StringIO()
    feed = mock.patch("builtins.input", side_effect=answers)
    with feed, contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = menu.run()
    return code, out.getvalue()


class MenuTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = os.path.realpath(tmp.name)
        prev = os.getcwd()
        self.addCleanup(os.chdir, prev)
        a = os.path.join(self.base, "a")
        os.makedirs(a)
        git(a, "init", "-q", "-b", "main")
        write(os.path.join(a, "README.md"), "# a\n")
        git(a, "add", "-A")
        git(a, "commit", "-q", "-m", "first")
        write(os.path.join(a, "config.py"), f'KEY = "{AWS}"\n')
        git(a, "add", "-A")
        git(a, "commit", "-q", "-m", "add config")
        write(os.path.join(a, "new.py"), f'TOKEN = "{AWS}"\n')
        git(a, "add", "new.py")
        os.makedirs(os.path.join(self.base, "plain", "deep"))
        os.makedirs(os.path.join(self.base, "empty"))
        git(os.path.join(self.base, "empty"), "init", "-q")
        os.chdir(self.base)

    def test_full_walkthrough_returns_to_the_menu_after_every_step(self):
        before = os.getcwd()
        code, out = drive(["1", "2", "1", "1", "2", "3", "4"])
        self.assertEqual((code, os.getcwd()), (0, before))
        self.assertEqual(out.count("What would you like to do?"), 2)
        self.assertEqual(out.count("What would you like to see?"), 4)
        for needle in ("Demo: a throwaway git repo", "  1) a", '"rule_id": "aws-access-key"', "commit ",
                       "scanned 2 commits", "config.py:1", "Goodbye."):
            self.assertIn(needle, out)
        self.assertNotIn(AWS, out)
        self.assertNotIn("Traceback", out)
        self.assertEqual(glob.glob(os.path.join(tempfile.gettempdir(), "secret-finder-demo-*")), [])

    def test_bad_input_never_ends_the_menu(self):
        code, out = drive(["x", "9", "", "2", "nope-folder", "plain", "", "3"])
        self.assertEqual(code, 0)
        for needle in ("Please type a number from 1 to 3.", "I cannot find that folder.", "not a git repository", "Goodbye."):
            self.assertIn(needle, out)
        self.assertNotIn("Traceback", out)

    def test_empty_repo_explains_instead_of_failing_and_f_changes_folder(self):
        code, out = drive(["2", "empty", "2", "f", "1", "1", "q"])
        self.assertEqual(code, 0)
        self.assertIn("no commits yet", out)
        self.assertEqual(out.count("Folder: "), 4)
        self.assertIn(os.path.join(self.base, "a"), out)
        self.assertNotIn("Traceback", out)

    def test_ctrl_c_and_end_of_input_say_goodbye(self):
        for error in (KeyboardInterrupt, EOFError):
            code, out = drive(error)
            self.assertEqual(code, 0)
            self.assertIn("Goodbye.", out)

    def test_find_repos_skips_hidden_and_vendor_folders_and_respects_limits(self):
        for name in (".hidden/r", "node_modules/r", "x/y/z/w/too_deep", "x/y/ok"):
            os.makedirs(os.path.join(self.base, name, ".git"))
        found = [os.path.relpath(p, self.base) for p in menu.find_repos(self.base)]
        self.assertEqual(found, ["a", "empty", os.path.join("x", "y", "ok")])
        self.assertEqual(len(menu.find_repos(self.base, limit=1)), 1)

    def test_no_arguments_without_a_terminal_prints_usage_and_the_docker_hint(self):
        err = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO("")), contextlib.redirect_stderr(err):
            code = main([])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err.getvalue())
        self.assertIn("docker run --rm -it", err.getvalue())

    def test_menu_command_works_without_a_terminal(self):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=["3"]), contextlib.redirect_stdout(out):
            self.assertEqual(main(["menu"]), 0)
        self.assertIn("runs on your machine", out.getvalue())


if __name__ == "__main__":
    unittest.main()
