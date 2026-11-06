import contextlib
import http.client as hc
import io
import json
import os
import socket
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

from secret_finder.ai import get_provider, http
from secret_finder.ai.base import ProviderError
from secret_finder.ai.google import Google
from secret_finder.ai.openrouter import OpenRouter
from secret_finder.cli import main

KEY = "sk-test-KEY-1234567890"
PWD = "hunter2hunter2"


class Resp:
    def __init__(self, body, delay=0):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.pos, self.delay = 0, delay

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        time.sleep(self.delay)
        chunk = self.body[self.pos:self.pos + n]
        self.pos += len(chunk)
        return chunk


class Net:
    def __init__(self, *results):
        self.results, self.requests = list(results), []

    def __call__(self, req, timeout):
        self.requests.append(req)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "msg", {}, None)


def http_lib_error():
    return hc.BadStatusLine("\x1b[2J")


def patched(net):
    return mock.patch.object(http, "_open", net)


class ProviderTest(unittest.TestCase):
    def setUp(self):
        for patch in (mock.patch.object(http, "BACKOFF", 0),):
            patch.start()
            self.addCleanup(patch.stop)

    def test_google_request_and_reply(self):
        net = Net(Resp({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}))
        with patched(net):
            self.assertEqual(Google("models/some-model", KEY).complete("hello"), "[]")
        (req,) = net.requests
        self.assertEqual(req.full_url, "https://generativelanguage.googleapis.com/v1beta/models/some-model:generateContent")
        self.assertEqual(req.get_header("X-goog-api-key"), KEY)
        self.assertNotIn(KEY, req.full_url + req.data.decode())
        self.assertEqual(json.loads(req.data)["contents"][0]["parts"][0]["text"], "hello")

    def test_openrouter_request_and_reply(self):
        net = Net(Resp({"choices": [{"message": {"content": "[]"}}]}))
        with patched(net):
            self.assertEqual(OpenRouter("vendor/model:free", KEY).complete("hi"), "[]")
        (req,) = net.requests
        self.assertEqual(req.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), f"Bearer {KEY}")
        body = json.loads(req.data)
        self.assertEqual((body["model"], body["messages"][0]["content"]), ("vendor/model:free", "hi"))

    def test_failures_become_provider_errors_without_leaking_the_key(self):
        cases = {
            "rate limit retries once": ([http_error(429)], 2),
            "server error retries once": ([http_error(503)], 2),
            "timeout retries once": ([socket.timeout("slow")], 2),
            "bad request does not retry": ([http_error(401)], 1),
            "redirect is refused": ([http_error(302)], 1),
            "not json": ([Resp(b"<html>")], 1),
            "wrong shape": ([Resp({"unexpected": 1})], 1),
            "text is not a string": ([Resp({"choices": [{"message": {"content": 5}}]})], 1),
            "too large": ([Resp(b"x" * (http.MAX_BYTES + 5))], 1),
            "bad status line with escapes": ([http_lib_error()], 2),
            "incomplete read": ([hc.IncompleteRead(b"x")], 2),
            "deeply nested json": ([Resp(b"[" * 200000)], 1),
            "unexpected exception": ([RuntimeError("\x1b[2Jsecret text")], 1),
        }
        for name, (results, attempts) in cases.items():
            net = Net(*results)
            with patched(net), self.assertRaises(ProviderError, msg=name) as ctx:
                OpenRouter("m", KEY).complete("p")
            self.assertEqual(len(net.requests), attempts, name)
            self.assertNotIn(KEY, str(ctx.exception), name)
            self.assertTrue(str(ctx.exception).isprintable(), name)

    def test_slow_drip_response_hits_the_total_deadline(self):
        net = Net(Resp(b"x" * 200000, delay=0.05))
        with patched(net), mock.patch.object(http, "DEADLINE", 0.01), self.assertRaises(ProviderError):
            OpenRouter("m", KEY).complete("p")
        self.assertEqual(len(net.requests), 2)

    def test_retry_can_recover_and_bad_header_is_rejected(self):
        good = Resp({"choices": [{"message": {"content": "ok"}}]})
        with patched(Net(http_error(429), good)):
            self.assertEqual(OpenRouter("m", KEY).complete("p"), "ok")
        with patched(Net(ValueError("Invalid header value"))), self.assertRaises(ProviderError):
            OpenRouter("m", KEY + "\nX-Evil: 1").complete("p")

    def test_get_provider_reads_only_environment_and_validates_it(self):
        env = {"SF_AI_PROVIDER": "Google", "SF_AI_MODEL": "m1", "SF_AI_API_KEY": KEY}
        self.assertIsInstance(get_provider(env), Google)
        self.assertIsInstance(get_provider({**env, "SF_AI_PROVIDER": "openrouter"}), OpenRouter)
        for broken, var in (({"SF_AI_PROVIDER": "nope"}, "SF_AI_PROVIDER"), ({"SF_AI_MODEL": ""}, "SF_AI_MODEL"),
                            ({"SF_AI_API_KEY": ""}, "SF_AI_API_KEY"), ({"SF_AI_MODEL": "../x?y=1"}, "SF_AI_MODEL"),
                            ({"SF_AI_MODEL": "gemini\n"}, "SF_AI_MODEL"), ({"SF_AI_MODEL": ".."}, "SF_AI_MODEL"),
                            ({"SF_AI_PROVIDER": "openrouter", "SF_AI_MODEL": "a/../b"}, "SF_AI_MODEL")):
            with self.assertRaises(ProviderError) as ctx:
                get_provider({**env, **broken})
            self.assertIn(var, str(ctx.exception))
            self.assertNotIn(KEY, str(ctx.exception))

    def test_unreachable_provider_leaves_output_and_exit_code_unchanged_and_writes_no_key(self):
        diff = f'+++ b/c.py\n@@ -0,0 +1 @@\n+db_password = "{PWD}"\n'
        env = {"SF_AI_PROVIDER": "google", "SF_AI_MODEL": "m1", "SF_AI_API_KEY": KEY}

        def run(argv):
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdin", io.StringIO(diff)), mock.patch.dict(os.environ, env), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                return main(argv), out.getvalue(), err.getvalue()

        with tempfile.TemporaryDirectory() as d:
            prev = os.getcwd()
            self.addCleanup(os.chdir, prev)
            os.chdir(d)
            plain = run(["scan", "-"])
            for failure in (urllib.error.URLError("down"), Resp(b"not json")):
                with patched(Net(failure)):
                    code, out, err = run(["scan", "-", "--ai"])
                self.assertEqual((code, out), plain[:2])
                self.assertNotIn(KEY, out + err)
            for root, _, files in os.walk(d):
                for name in files:
                    with open(os.path.join(root, name), errors="replace") as f:
                        self.assertNotIn(KEY, f.read(), name)


if __name__ == "__main__":
    unittest.main()
