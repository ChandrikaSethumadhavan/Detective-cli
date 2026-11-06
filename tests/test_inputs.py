import io
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from secret_finder import inputs
from secret_finder.diffparse import Added, parse

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, env=ENV).stdout.strip()


def scan(**kw):
    return list(parse(inputs.read_diff(**kw)))


class InputsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prev = os.getcwd()
        self.addCleanup(os.chdir, self.prev)
        os.chdir(self.tmp.name)
        git("init", "-q")

    def commit(self, name, text):
        with open(name, "a") as f:
            f.write(text)
        git("add", name)
        git("commit", "-q", "-m", "c")
        return git("rev-parse", "HEAD")

    def test_root_and_normal_commit(self):
        root = self.commit("a.txt", "one\n")
        second = self.commit("a.txt", "two\n")
        self.assertEqual(scan(commit=root), [Added("a.txt", 1, "one")])
        self.assertEqual(scan(commit=second), [Added("a.txt", 2, "two")])

    def test_working_dir_covers_staged_and_unstaged(self):
        self.commit("a.txt", "one\n")
        self.commit("b.txt", "x\n")
        with open("a.txt", "a") as f:
            f.write("unstaged\n")
        with open("b.txt", "a") as f:
            f.write("staged\n")
        git("add", "b.txt")
        self.assertEqual(
            sorted(scan()), [Added("a.txt", 2, "unstaged"), Added("b.txt", 2, "staged")]
        )

    def test_working_dir_without_commits_uses_index(self):
        with open("a.txt", "w") as f:
            f.write("new\n")
        git("add", "a.txt")
        self.assertEqual(scan(), [Added("a.txt", 1, "new")])

    def test_file_and_stdin(self):
        diff = "+++ b/f\n@@ -0,0 +1 @@\n+hit\n"
        with open("p.diff", "w") as f:
            f.write(diff)
        self.assertEqual(scan(source="p.diff"), [Added("f", 1, "hit")])
        with mock.patch("sys.stdin", io.StringIO(diff)):
            self.assertEqual(scan(source="-"), [Added("f", 1, "hit")])

    def test_errors(self):
        self.commit("a.txt", "one\n")
        for kw in ({"commit": "nope"}, {"commit": "--output=x"}, {"source": "missing.diff"},
                   {"source": "x", "commit": "y"}):
            with self.assertRaises(inputs.InputError):
                scan(**kw)


if __name__ == "__main__":
    unittest.main()
