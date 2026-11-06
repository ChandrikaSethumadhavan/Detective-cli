import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from secret_finder.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AWS = "AKIAIOSFODNN7EXAMPLE"
LEAK = f'+++ b/cfg.py\n@@ -0,0 +1 @@\n+KEY = "{AWS}"\n'
CLEAN = "+++ b/ok.py\n@@ -0,0 +1 @@\n+x = 1\n"
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def run(argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        prev = os.getcwd()
        self.addCleanup(os.chdir, prev)
        os.chdir(tmp.name)

    def test_stdin_leak_and_clean(self):
        code, out, _ = run(["scan", "-"], LEAK)
        self.assertEqual(code, 1)
        self.assertIn("cfg.py:1", out)
        self.assertIn("aws-access-key", out)
        self.assertIn("fix: Deactivate it", out)
        self.assertNotIn(AWS, out)
        self.assertEqual(run(["scan", "-"], CLEAN), (0, "", ""))

    def test_json_output_has_fix_and_no_raw_secret(self):
        code, out, _ = run(["scan", "-", "--json"], LEAK)
        (item,) = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual((item["file"], item["line"], item["rule_id"]), ("cfg.py", 1, "aws-access-key"))
        self.assertTrue(item["fix"])
        self.assertNotIn(AWS, out)
        self.assertEqual(run(["scan", "-", "--json"], CLEAN)[1], "[]\n")

    def test_tool_errors_exit_2(self):
        for argv in (["scan", "/no/such.diff"], ["scan", "x", "--commit", "y"], ["bogus"]):
            code, out, _ = run(argv)
            self.assertEqual((code, out), (2, ""), argv)

    def test_commit_and_working_dir_modes(self):
        with tempfile.TemporaryDirectory() as d:
            prev = os.getcwd()
            self.addCleanup(os.chdir, prev)
            os.chdir(d)
            g = lambda *a: subprocess.run(["git", *a], check=True, capture_output=True, text=True, env=ENV).stdout.strip()
            g("init", "-q")
            with open("cfg.py", "w") as f:
                f.write(f'KEY = "{AWS}"\n')
            g("add", "cfg.py")
            g("commit", "-q", "-m", "root")
            self.assertEqual(run(["scan", "--commit", g("rev-parse", "HEAD")])[0], 1)
            self.assertEqual(run(["scan"])[0], 0)
            with open("cfg.py", "a") as f:
                f.write(f'OTHER = "{AWS}"\n')
            code, out, _ = run(["scan"])
            self.assertEqual(code, 1)
            self.assertIn("cfg.py:2", out)

    def test_module_entry_point_runs_offline(self):
        p = subprocess.run([sys.executable, "-m", "secret_finder", "scan", "-"], input=LEAK,
                           capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ROOT})
        self.assertEqual(p.returncode, 1)
        self.assertIn("cfg.py:1", p.stdout)


if __name__ == "__main__":
    unittest.main()
