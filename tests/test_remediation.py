import unittest

from secret_finder.detect import detect
from secret_finder.diffparse import Added
from secret_finder.rules import RULES

SAMPLES = {
    "aws-access-key": 'k = "AKIAIOSFODNN7EXAMPLE"',
    "private-key-block": "-----BEGIN OPENSSH PRIVATE KEY-----",
    "github-token": 'tok = "ghp_' + ("aB3dE5gH7j" * 4)[:36] + '"',
    "slack-token": 'tok = "xoxb-1234567890-abcdefghij"',
    "google-api-key": 'k = "AIza' + "Ab3" * 11 + 'Zz"',
    "jwt": 'h = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27u"',
    "generic-assignment": 'db_password = "hunter2hunter2"',
    "high-entropy-string": 'blob = "q8Zr3Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe"',
}
RAW = ["AKIAIOSFODNN7EXAMPLE", "hunter2hunter2", "q8Zr3Lm0Xv7Tn2KpW5yB9cDfG1hJ4sUe", "xoxb-1234567890-abcdefghij",
       "eyJhbGciOiJIUzI1NiJ9", "ghp_" + ("aB3dE5gH7j" * 4)[:36], "AIza" + "Ab3" * 11 + "Zz"]


class RemediationTest(unittest.TestCase):
    def test_every_rule_has_a_short_fix(self):
        for r in RULES:
            self.assertTrue(r.fix.strip(), r.id)
            self.assertLessEqual(len(r.fix), 300, r.id)

    def test_every_rule_is_exercised_and_fix_is_static_and_clean(self):
        self.assertEqual(set(SAMPLES), {r.id for r in RULES})
        fixes = {r.id: r.fix for r in RULES}
        for rule_id, text in SAMPLES.items():
            found = list(detect([Added("f", 1, text)], salt=b"t"))
            self.assertEqual([f.rule_id for f in found], [rule_id], rule_id)
            self.assertEqual(found[0].fix, fixes[rule_id])
            for raw in RAW:
                self.assertNotIn(raw, found[0].fix)


if __name__ == "__main__":
    unittest.main()
