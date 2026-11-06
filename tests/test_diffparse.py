import unittest

from secret_finder.diffparse import Added, parse

TWO_HUNKS = """\
diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -1,2 +1,2 @@
-old = 1
+new = 1
 keep = 2
@@ -10,2 +40,3 @@ def f():
 ctx = 3
-gone = 4
+first = 5
+KEY = "AKIAIOSFODNN7EXAMPLE"
"""


class ParseTest(unittest.TestCase):
    def test_line_numbers_across_hunks(self):
        got = list(parse(TWO_HUNKS.splitlines(True)))
        self.assertEqual(
            got,
            [
                Added("app.py", 1, "new = 1"),
                Added("app.py", 41, "first = 5"),
                Added("app.py", 42, 'KEY = "AKIAIOSFODNN7EXAMPLE"'),
            ],
        )

    def test_content_that_looks_like_headers_is_not_a_header(self):
        diff = "+++ b/x.py\n@@ -1,2 +1,2 @@\n--- removed text\n+++ added text\n"
        self.assertEqual(list(parse(diff.splitlines(True))), [Added("x.py", 1, "++ added text")])

    def test_deleted_and_binary_files_are_skipped(self):
        diff = (
            "diff --git a/d b/d\n--- a/d\n+++ /dev/null\n@@ -1 +0,0 @@\n-secret\n"
            "diff --git a/img b/img\nBinary files a/img and b/img differ\n"
            "diff --git a/n b/n\n--- /dev/null\n+++ b/n\n@@ -0,0 +1 @@\n+ok\n"
        )
        self.assertEqual(list(parse(diff.splitlines(True))), [Added("n", 1, "ok")])

    def test_no_newline_marker_is_ignored(self):
        diff = "+++ b/a\n@@ -1 +1 @@\n-x\n\\ No newline at end of file\n+y\n\\ No newline at end of file\n"
        self.assertEqual(list(parse(diff.splitlines(True))), [Added("a", 1, "y")])


if __name__ == "__main__":
    unittest.main()
