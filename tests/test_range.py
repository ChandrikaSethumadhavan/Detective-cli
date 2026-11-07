import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from secret_finder.cli import main

AWS = "AKIAIOSFODNN7EXAMPLE"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, env=ENV).stdout.strip()


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO("")), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(["scan", *argv])
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class RangeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        self.addCleanup(os.chdir, prev)
        os.chdir(tmp.name)
        git("init", "-q", "-b", "main")
        self.c1 = self.commit("README.md", "# hi\n", "first")
        self.c2 = self.commit("config.py", f'KEY = "{AWS}"\n', f"add key {AWS}")
        self.c3 = self.commit("config.py", "KEY = None\n", "remove key")

    def commit(self, name, text, message):
        with open(name, "w") as f:
            f.write(text)
        git("add", name)
        git("commit", "-q", "-m", message)
        return git("rev-parse", "HEAD")

    def test_history_finds_a_key_that_was_later_removed_and_names_its_commit(self):
        code, out, err = run("--range", "HEAD")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("commit "), 1)
        self.assertIn(f"commit {self.c2[:7]}", out)
        self.assertIn("config.py:1", out)
        self.assertNotIn(AWS, out + err)
        self.assertIn("scanned 3 commits", err)
        self.assertIn("1 finding (1 high) in 1 commit", err)

    def test_clean_and_empty_ranges_exit_0_and_say_so(self):
        code, out, err = run("--range", self.c1)
        self.assertEqual((code, out), (0, ""))
        self.assertIn("scanned 1 commit", err)
        self.assertIn("no secrets found", err)
        code, out, err = run("--range", "HEAD..HEAD")
        self.assertEqual((code, out), (0, ""))
        self.assertIn("no commits matched HEAD..HEAD", err)

    def test_json_has_a_full_commit_hash_on_every_finding_and_stdout_stays_pure(self):
        code, out, _ = run("--range", f"{self.c1}..{self.c3}", "--json")
        data = json.loads(out)
        self.assertEqual((code, [d["commit"] for d in data]), (1, [self.c2]))
        self.assertEqual(data[0]["rule_id"], "aws-access-key")

    def test_a_merged_secret_is_reported_once(self):
        git("checkout", "-q", "-b", "feature", self.c1)
        self.commit("leak.py", f'T = "{AWS}"\n', "leak")
        git("checkout", "-q", "main")
        git("merge", "-q", "--no-ff", "feature", "-m", "merge feature")
        code, out, _ = run("--range", "HEAD", "--json")
        files = sorted(d["file"] for d in json.loads(out))
        self.assertEqual((code, files), (1, ["config.py", "leak.py"]))

    def test_limits_and_bad_input_exit_2_and_print_no_findings(self):
        for argv in (["--range", "HEAD", "--max-commits", "2"], ["--range", "nope"], ["--range", "-x"],
                     ["--range", "--all"], ["--range", "HEAD", "--commit", "HEAD"], ["--range", "HEAD", "some.diff"]):
            code, out, err = run(*argv)
            self.assertEqual((code, out), (2, ""), argv)
            self.assertIn("error" if "-x" in argv or "--all" in argv else "secret-finder:", err)
        self.assertIn("more than 2 commits", run("--range", "HEAD", "--max-commits", "2")[2])

    def test_commit_messages_are_never_printed(self):
        _, out, err = run("--range", "HEAD", "--json")
        self.assertNotIn("add key", out + err)


if __name__ == "__main__":
    unittest.main()
