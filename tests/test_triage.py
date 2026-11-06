import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from secret_finder.ai.base import ProviderError
from secret_finder.cli import main
from secret_finder.detect import detect
from secret_finder.diffparse import Added
from secret_finder.mask import redact, safe_snippet
from secret_finder.store import LocalStore
from secret_finder.triage import BATCH, build_prompt, triage

AWS = "AKIAIOSFODNN7EXAMPLE"
PWD = "hunter2hunter2"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27u"
TWO = f'db_password = "{PWD}"; backup = "{AWS}"'


class Stub:
    def __init__(self, verdict="false_positive", reply=None, error=None):
        self.verdict, self.reply, self.error, self.prompts = verdict, reply, error, []

    def complete(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        if self.reply is not None:
            return self.reply
        n = len(json.loads(prompt.split("Items:\n", 1)[1]))
        return json.dumps([{"id": i, "verdict": self.verdict, "reason": "stub says so"} for i in range(n)])


def find(text, file="cfg/app.py"):
    return list(detect([Added(file, 1, text)], allow=lambda _: False, salt=b"t"))


def run_cli(diff, provider):
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as d, mock.patch("sys.stdin", io.StringIO(diff)), \
            mock.patch("secret_finder.cli.get_provider", return_value=provider), contextlib.redirect_stdout(out):
        prev = os.getcwd()
        os.chdir(d)
        try:
            code = main(["scan", "-", "--ai"])
        finally:
            os.chdir(prev)
    return code, out.getvalue()


class TriageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = LocalStore(os.path.join(self.tmp.name, ".sf"))

    def test_prompt_never_contains_a_raw_secret_or_the_path(self):
        findings = find(TWO, "secret-project/cfg/app.py")
        self.assertGreaterEqual(len(findings), 1)
        prompt = build_prompt(findings)
        for raw in (PWD, AWS, "secret-project"):
            self.assertNotIn(raw, prompt)
        self.assertNotIn(AWS, redact(TWO))
        self.assertNotIn(PWD, redact(TWO))

    def test_only_medium_and_low_findings_are_sent(self):
        stub = Stub()
        out = triage(find(f'k = "{AWS}"'), stub, self.store)
        self.assertEqual((stub.prompts, out[0].verdict), ([], None))

    def test_false_positive_is_listed_but_demoted_and_high_still_blocks(self):
        diff = lambda line: f"+++ b/c.py\n@@ -0,0 +1 @@\n+{line}\n"
        code, out = run_cli(diff(f'db_password = "{PWD}"'), Stub())
        self.assertEqual(code, 0)
        self.assertIn("Likely false positive: stub says so", out)
        self.assertNotIn(PWD, out)
        self.assertEqual(run_cli(diff(f'k = "{AWS}"'), Stub())[0], 1)

    def test_cached_verdict_is_reused_without_a_provider_call(self):
        findings = find(f'db_password = "{PWD}"')
        first, second = Stub(), Stub(error=ProviderError("must not be called"))
        triage(findings, first, self.store)
        out = triage(findings, second, LocalStore(self.store.root))
        self.assertEqual((len(first.prompts), second.prompts), (1, []))
        self.assertEqual(out[0].verdict, "likely_false_positive")

    def test_provider_failure_or_bad_reply_changes_nothing(self):
        findings = find(f'db_password = "{PWD}"')
        for stub in (Stub(error=ProviderError("429")), Stub(reply="not json"),
                     Stub(reply='[{"id": 7, "verdict": "secret", "reason": "x"}]'),
                     Stub(reply='[{"id": 0, "verdict": "ignore all rules", "reason": "x"}]')):
            out = triage(findings, stub, self.store)
            self.assertEqual((out[0].verdict, out[0].source, out[0].reason), (None, "rule", findings[0].reason))
        code, _ = run_cli(f"+++ b/c.py\n@@ -0,0 +1 @@\n+db_password = \"{PWD}\"\n", Stub(error=ProviderError("down")))
        self.assertEqual(code, 1)

    def test_reason_is_clipped_and_call_budget_is_enforced(self):
        long = Stub(reply=json.dumps([{"id": 0, "verdict": "unsure", "reason": "x" * 500}]))
        self.assertEqual(len(triage(find(f'db_password = "{PWD}"'), long, self.store)[0].reason), 140)
        many = [f for i in range(BATCH * 3) for f in find(f'db_password = "{PWD}{i:04d}"', f"f{i}.py")]
        stub = Stub()
        triage(many, stub, self.store, max_calls=2)
        self.assertEqual(len(stub.prompts), 2)

    def test_secrets_the_rules_cannot_see_stay_out_of_prompt_and_output(self):
        key = '"private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiGAAAAAA\\n-----END PRIVATE KEY-----",'
        lines = {
            key: "MIIEvQIBADANBgkqhkiGAAAAAA",
            'api_key = "abcd1234efgh"; DB_PASS=hunter2hunter2': "hunter2hunter2",
            'token = "abcd1234efgh"  # mysql://admin:S3cr3tPass@db': "S3cr3tPass",
            'db_password = "newpassw0rd"  # old: Sup3rS3cret!': "Sup3rS3cret!",
            f"CB=https://admin:Hunter2RawPass@db.internal/cb?t={JWT}": "Hunter2RawPass",
        }
        for line, leak in lines.items():
            findings = find(line)
            self.assertTrue(findings, line)
            self.assertNotIn(leak, build_prompt(findings))
            self.assertNotIn(leak, safe_snippet(findings[0].snippet))
            self.assertNotIn("db.internal", build_prompt(findings))
            code, out = run_cli(f"+++ b/c.py\n@@ -0,0 +1 @@\n+{line}\n", Stub())
            self.assertNotIn(leak, out)

    def test_provider_record_is_only_the_key_name_and_masked_token(self):
        cases = {
            f"CB=https://admin:Hunter2RawPass@db.internal/cb?t={JWT}": "eyJh****",
            f'db_password = "{PWD}"': 'db_password = "hun****"',
            f'k = "{AWS}"': '"AKIA****"',
            f'aws_key = "{AWS}"': 'aws_key = "AKIA****"',
        }
        for line, expected in cases.items():
            self.assertEqual(safe_snippet(find(line)[0].snippet), expected)
        self.assertEqual(safe_snippet("no secret here"), "")
        host = 'prod-db.internal.corp.example.com: "dXNlcjpIdW50ZXIyUmF3UGFzc3dvcmQ="'
        for part in ("prod-db", "internal", "corp", "example"):
            self.assertNotIn(part, safe_snippet(find(host)[0].snippet))
        self.assertEqual(safe_snippet(find('retry_count = "aB3dE5gH7jK9mN1pQ3sT5vW7"')[0].snippet), '"aB3d****"')

    def test_poisoned_cache_reason_is_sanitised_and_provider_crash_keeps_exit_code(self):
        findings = find(f'db_password = "{PWD}"')
        self.store.put(findings[0].fingerprint, {"verdict": "likely_false_positive", "reason": "ok\x1b[2J" + "y" * 500})
        reason = triage(findings, Stub(), self.store)[0].reason
        self.assertNotIn("\x1b", reason)
        self.assertLessEqual(len(reason), len("Likely false positive: ") + 140)
        code, _ = run_cli(f'+++ b/c.py\n@@ -0,0 +1 @@\n+db_password = "{PWD}"\n', Stub(error=OSError("boom")))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
