import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from secret_finder.cli import main
from secret_finder.detect import detect
from secret_finder.diffparse import Added
from secret_finder.store import LocalStore

AWS = "AKIAIOSFODNN7EXAMPLE"
LINE = f'k = "{AWS}"'


def findings(file="cfg/app.py", **kw):
    return list(detect([Added(file, 1, LINE)], salt=b"t", **kw))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, ".secretfinder")
        os.makedirs(self.root)

    def allowlist(self, text):
        with open(os.path.join(self.root, "allowlist"), "w") as f:
            f.write(text)
        return LocalStore(self.root)

    def test_allowlist_by_rule_glob_wildcard_and_fingerprint(self):
        (f,) = findings(allow=lambda _: False)
        for entry, hit in (
            ("aws-access-key cfg/*", True),
            ("* cfg/app.py", True),
            ("aws-access-key", True),
            (f.fingerprint, True),
            ("github-token cfg/*", False),
            ("aws-access-key docs/*", False),
            ("# aws-access-key cfg/*", False),
        ):
            store = self.allowlist(f"\n{entry}\n")
            self.assertEqual(findings(allow=store.is_allowed) == [], hit, entry)

    def test_default_allowlist_is_read_from_cwd_by_detect_and_cli(self):
        self.allowlist("aws-access-key cfg/*\n")
        prev = os.getcwd()
        self.addCleanup(os.chdir, prev)
        os.chdir(self.tmp.name)
        self.assertEqual(findings(), [])
        diff = f"+++ b/cfg/app.py\n@@ -0,0 +1 @@\n+{LINE}\n"
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(diff)), contextlib.redirect_stdout(out):
            self.assertEqual(main(["scan", "-"]), 0)
        self.assertEqual(out.getvalue(), "")

    def test_cache_round_trip_survives_corruption_and_holds_no_secret(self):
        (f,) = findings(allow=lambda _: False)
        verdict = {"verdict": "secret", "reason": "real key"}
        LocalStore(self.root).put(f.fingerprint, verdict)
        self.assertEqual(LocalStore(self.root).get(f.fingerprint), verdict)
        self.assertIsNone(LocalStore(self.root).get("0" * 64))
        with open(os.path.join(self.root, "cache.json")) as fh:
            self.assertNotIn(AWS, fh.read())
        with open(os.path.join(self.root, "cache.json"), "w") as fh:
            fh.write("{broken")
        store = LocalStore(self.root)
        self.assertIsNone(store.get(f.fingerprint))
        store.put(f.fingerprint, verdict)
        self.assertEqual(LocalStore(self.root).get(f.fingerprint), verdict)

    def test_salt_is_private_stable_and_not_the_raw_value(self):
        salt = LocalStore(self.root).salt
        self.assertEqual(len(salt), 32)
        self.assertEqual(LocalStore(self.root).salt, salt)
        self.assertEqual(os.stat(os.path.join(self.root, "salt")).st_mode & 0o077, 0)

    def test_bad_salt_and_allowlist_files_never_crash_or_change_between_runs(self):
        salt_path = os.path.join(self.root, "salt")
        for bad in ("zz", "", "ab" * 5):
            with open(salt_path, "w") as f:
                f.write(bad)
            first = LocalStore(self.root).salt
            self.assertEqual((len(first), LocalStore(self.root).salt), (32, first), bad)
        with open(os.path.join(self.root, "allowlist"), "wb") as f:
            f.write(b"\xff\xfe\x00")
        self.assertEqual(LocalStore(self.root).rules, [])

    def test_local_state_is_gitignored(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, ".gitignore")) as f:
            lines = f.read().splitlines()
        self.assertIn(".secretfinder/salt", lines)
        self.assertIn(".secretfinder/cache.json", lines)

    def test_write_failures_leave_no_temp_files_and_never_raise(self):
        store = LocalStore(self.root)
        os.makedirs(os.path.join(self.root, "salt"))
        self.assertEqual(len(LocalStore(self.root).salt), 32)
        store.put("0" * 64, {"bad": {1, 2}})
        self.assertNotIn("0" * 64, LocalStore(self.root).cache)
        self.assertEqual(sorted(os.listdir(self.root)), ["salt"])


if __name__ == "__main__":
    unittest.main()
