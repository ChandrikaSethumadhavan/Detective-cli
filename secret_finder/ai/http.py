import http.client
import json
import time
import urllib.error
import urllib.request

from .base import ProviderError

TIMEOUT = 20
BACKOFF = 2.0
MAX_BYTES = 1_000_000
DEADLINE = 30


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _open(req, timeout):
    return urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout)


def _read(resp) -> bytes:
    end = time.monotonic() + DEADLINE
    chunks, size = [], 0
    while chunk := resp.read(65536):
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_BYTES:
            raise ProviderError("response too large")
        if time.monotonic() > end:
            raise TimeoutError("deadline")
    return b"".join(chunks)


def post_json(url: str, headers: dict, payload: dict):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    failure = "request failed"
    for attempt in range(2):
        if attempt:
            time.sleep(BACKOFF)
        try:
            with _open(req, TIMEOUT) as resp:
                body = _read(resp)
        except urllib.error.HTTPError as e:
            failure = f"HTTP {e.code}"
            if e.code != 429 and e.code < 500:
                break
            continue
        except ProviderError:
            raise
        except ValueError:
            raise ProviderError("invalid request header or URL")
        except (OSError, http.client.HTTPException) as e:
            failure = type(e).__name__
            continue
        except Exception as e:
            raise ProviderError(type(e).__name__)
        try:
            return json.loads(body)
        except (ValueError, RecursionError):
            raise ProviderError("invalid JSON response")
    raise ProviderError(failure)
