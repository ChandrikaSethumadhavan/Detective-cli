import inspect
import time
import unittest

from secret_finder.detect import detect
from secret_finder.diffparse import Added, parse
from secret_finder.entropy import shannon
from secret_finder.rules import RULES

AWS = "AKIAIOSFODNN7EXAMPLE"
SALT = b"test-salt"
GH = "ghp_" + ("aB3dE5gH7j" * 4)[:36]

DIFF = f"""\
+++ b/cfg.py
@@ -1,3 +1,6 @@
-OLD_KEY = "{AWS}"
+AWS_KEY = "{AWS}"
+-----BEGIN RSA PRIVATE KEY-----
+password = "changeme"
+ID = "123e4567-e89b-12d3-a456-426614174000"
+REV = "{'a1b2c3d4e5' * 4}"
"""


def run(text, file="f.py", line=1):
    return list(detect([Added(file, line, text)], salt=SALT))


class DetectTest(unittest.TestCase):
    def test_diff_yields_only_the_two_real_secrets(self):
        found = list(detect(parse(DIFF.splitlines(True)), salt=SALT))
        self.assertEqual([(f.rule_id, f.line) for f in found], [("aws-access-key", 1), ("private-key-block", 2)])

    def test_every_finding_has_reason_fix_and_no_raw_value(self):
        for text in (f'k = "{AWS}"', f'tok = "{GH}"', 'db_password = "hunter2hunter2"',
                     'blob = "q8Zr3Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe"'):
            (f,) = run(text)
            self.assertTrue(f.reason and f.fix, f.rule_id)
            for raw in (AWS, GH, "hunter2hunter2", "q8Zr3Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe"):
                self.assertNotIn(raw, f.snippet)
                self.assertNotIn(raw, f.fingerprint)
        self.assertTrue(all(r.reason and r.fix for r in RULES))

    def test_one_finding_per_value_and_inline_ignore(self):
        self.assertEqual([f.rule_id for f in run(f'token = "{GH}"')], ["github-token"])
        self.assertEqual(run(f'k = "{AWS}"  # secret-finder: ignore'), [])
        self.assertEqual(run('token = os.environ["API_TOKEN_VALUE_X"]'), [])

    def test_entropy_and_laziness(self):
        self.assertEqual(shannon(""), 0.0)
        self.assertAlmostEqual(shannon("abab"), 1.0)
        self.assertTrue(inspect.isgenerator(detect([])))

    def test_fingerprint_is_keyed_to_the_value_and_the_salt(self):
        fp = lambda text, salt=SALT: list(detect([Added("f.py", 1, text)], salt=salt))[0].fingerprint
        a, b = 'db_password = "hunter2hunter2"', 'db_password = "hunREALsecret9"'
        self.assertEqual(fp(a), fp(a))
        self.assertNotEqual(fp(a), fp(b))
        self.assertNotEqual(fp(a), fp(a, b"other-salt"))
        self.assertNotIn("hunter2", fp(a))

    def test_skips_apply_to_the_value_not_the_whole_line(self):
        self.assertEqual(len(run('password = "R3alS3cret99"  # not read from environ')), 1)
        self.assertEqual(len(run('password = "MyExamplePassw0rd"')), 1)
        self.assertEqual(len(run('x = os.environ.get("X", "Zq8Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe")')), 1)
        self.assertEqual(len(run('environment_password = "R3alS3cret99"')), 1)
        self.assertEqual(len(run('const a = process.env.X, password = "R3alS3cret99"')), 1)
        self.assertEqual(run('x = os.environ["Zq8Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe"]'), [])
        self.assertEqual(len(run('password = "exampleR3alS3cret99"')), 1)
        self.assertEqual(run('password = "your_password_here"'), [])
        self.assertEqual(run('password = "changeme"'), [])
        for real in ("changeme123", "changeme_Xk9fQ2wLp7", "your_Kx9fQ2wLp7Zr4Tb8Vn3M", "<Kx9fQ2wLp7Zr4Tb8Vn3M>", "Kx9f****Q2wLp7Zr4"):
            self.assertEqual(len(run(f'password = "{real}"')), 1, real)

    def test_every_secret_on_a_line_is_masked_and_bad_bytes_do_not_crash(self):
        line = f'password = "R3alS3cret99"; aws = "{AWS}"'
        found = run(line)
        self.assertEqual(len(found), 2)
        for f in found:
            self.assertNotIn("R3alS3cret99", f.snippet)
            self.assertNotIn(AWS, f.snippet)
        self.assertNotEqual(found[0].fingerprint, found[1].fingerprint)
        (other,) = run(f'k = "{AWS}"; pw = os.getenv("Kx9fQ2wLp7Zr4Tb8Vn3MqP1sD")')
        self.assertNotIn("Kx9fQ2wLp7Zr4Tb8Vn3MqP1sD", other.snippet)
        self.assertEqual(len(run('password = "R3al\udcffS3cret99"')), 1)
        key = '"private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiGAAAA\\n-----END PRIVATE KEY-----",'
        (pk,) = run(key)
        self.assertNotIn("MIIEvQ", pk.snippet)

    def test_no_rule_is_slow_on_very_long_lines(self):
        for line in ("password." * 3000, "a." * 10000, "xoxb-" * 4000, "token=" * 4000, "eyJ" * 6000, "-eyJ" * 20000, '"' + "a" * 30000,
                     ' password="Rx7kQ2pZ"' * 4000, ' "Kx9fQ2wLp7Zr4Tb8Vn3MqP1sD"' * 3000):
            start = time.monotonic()
            run(line)
            self.assertLess(time.monotonic() - start, 2.0, line[:12])

    def test_json_go_and_long_values_are_caught_and_glued_text_stays_out_of_snippets(self):
        for line in ('{"password": "R3alS3cret99"}', 'password := "R3alS3cret99"', "password = '" + "hunter2!Pass" * 40 + "'"):
            self.assertEqual([f.rule_id for f in run(line)], ["generic-assignment"], line[:30])
        (f,) = run('x=Zq9Lm2Vb7Xc4key="Kx9fQ2wLp7Zr4Tb8Vn3MqP1sD"')
        self.assertNotIn("Zq9Lm2", f.snippet)
        (g,) = run(f'Hunter2RawPass_AdminUser={AWS}')
        self.assertNotIn("Hunter2", g.snippet)
        self.assertEqual(run('aws_key = "AKIAIOSFODNN7EXAMPLE"')[0].snippet, 'aws_key = "AKIA****"')

    def test_each_finding_snippet_comes_from_its_own_value(self):
        (pw,) = run('x = "ab****"; db_password = "RealPassw0rdXYZ"')
        self.assertEqual(pw.snippet, 'db_password = "Rea****"')
        aws, jwt = sorted(run(f'k = "{AWS}"; t = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27u"'),
                          key=lambda f: f.rule_id)
        self.assertEqual((aws.snippet, jwt.snippet), ('"AKIA****"', '"eyJh****"'))

    def test_console_script_entry_points_are_skipped_only_in_packaging_manifests(self):
        line = 'secret-finder = "secret_finder.cli:main"'
        for manifest in ("pyproject.toml", "setup.cfg", "pkg/pyproject.toml"):
            self.assertEqual(run(line, manifest), [], manifest)
        self.assertEqual(len(run(line, "app.py")), 1)
        for credential in ("admin:hunter2hunter2", "john.smith:Passw0rd", "hunter2hunter2"):
            self.assertEqual(len(run(f'password = "{credential}"', "pyproject.toml")), 1, credential)


if __name__ == "__main__":
    unittest.main()
