import contextlib
import glob
import io
import os
import subprocess
import sys
import tempfile
import unittest

from secret_finder import demo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DemoTest(unittest.TestCase):
    def test_demo_lists_findings_cleans_up_and_leaves_the_cwd_alone(self):
        before = os.getcwd()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = demo.run()
        text = out.getvalue()
        self.assertEqual((code, os.getcwd()), (0, before))
        for needle in ("config.py:1", "settings.json:2", "deploy.sh:2", "high", "medium", "fix:"):
            self.assertIn(needle, text)
        self.assertNotIn("notes.py:", text)
        for raw in ("AKIAIOSFODNN7EXAMPLE", "hunter2hunter2", demo.TOKEN):
            self.assertNotIn(raw, text + err.getvalue())
        self.assertIn("3 findings", err.getvalue())
        self.assertEqual(glob.glob(os.path.join(tempfile.gettempdir(), "secret-finder-demo-*")), [])

    def test_demo_command_runs_from_the_module_entry_point(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, "-m", "secret_finder", "demo"], capture_output=True, text=True,
                               cwd=d, env={**os.environ, "PYTHONPATH": ROOT})
            self.assertEqual(os.listdir(d), [])
        self.assertEqual(p.returncode, 0)
        self.assertIn("aws-access-key", p.stdout)


if __name__ == "__main__":
    unittest.main()
