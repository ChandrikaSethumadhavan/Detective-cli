import contextlib
import fnmatch
import json
import os
import re
import sys
import tempfile
from typing import Optional, Protocol

FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class Store(Protocol):
    def is_allowed(self, finding) -> bool: ...
    def get(self, fingerprint: str) -> Optional[dict]: ...
    def put(self, fingerprint: str, verdict: dict) -> None: ...


class LocalStore:
    def __init__(self, root: str = ".secretfinder"):
        self.root = root
        self.rules = []
        self.fingerprints = set()
        self._load_allowlist()
        self.cache = self._read_cache()
        self._salt = None

    def _load_allowlist(self):
        try:
            with open(os.path.join(self.root, "allowlist"), encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, ValueError):
            return
        for line in lines:
            line = line.split("#", 1)[0].strip()
            if FINGERPRINT.match(line):
                self.fingerprints.add(line)
            elif line:
                rule, _, glob = line.partition(" ")
                self.rules.append((rule, glob.strip() or "*"))

    def _read_cache(self) -> dict:
        try:
            with open(os.path.join(self.root, "cache.json"), encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @property
    def salt(self) -> bytes:
        if self._salt is None:
            path = os.path.join(self.root, "salt")
            self._salt = self._read_salt(path)
            if self._salt is None:
                self._salt = os.urandom(32)
                try:
                    self._write_atomic(path, self._salt.hex(), os.link)
                except FileExistsError:
                    existing = self._read_salt(path)
                    if existing:
                        self._salt = existing
                    else:
                        print(f"secret-finder: replacing invalid {path}; fingerprint allowlist entries must be regenerated",
                              file=sys.stderr)
                        with contextlib.suppress(OSError):
                            self._write_atomic(path, self._salt.hex())
                except OSError:
                    pass  # unwritable: fingerprints last for this run only
        return self._salt

    def _write_atomic(self, path: str, text: str, publish=os.replace) -> None:
        os.makedirs(self.root, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            publish(tmp, path)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)

    @staticmethod
    def _read_salt(path: str) -> Optional[bytes]:
        try:
            with open(path, encoding="utf-8") as f:
                salt = bytes.fromhex(f.read().strip())
        except (OSError, ValueError):
            return None
        return salt if len(salt) == 32 else None

    def is_allowed(self, finding) -> bool:
        return finding.fingerprint in self.fingerprints or any(
            rule in ("*", finding.rule_id) and fnmatch.fnmatch(finding.file, glob)
            for rule, glob in self.rules
        )

    def get(self, fingerprint: str) -> Optional[dict]:
        return self.cache.get(fingerprint)

    def put(self, fingerprint: str, verdict: dict) -> None:
        self.cache[fingerprint] = verdict
        try:
            self._write_atomic(os.path.join(self.root, "cache.json"), json.dumps(self.cache))
        except (OSError, TypeError, ValueError):
            pass  # the cache is best effort; a scan must not fail because it cannot write
