import re
from typing import NamedTuple


class Rule(NamedTuple):
    id: str
    pattern: re.Pattern
    confidence: str
    reason: str
    fix: str
    mask: bool = True


def mask(value: str) -> str:
    return value[: max(2, min(4, len(value) // 4))] + "****"


ROTATE_ENV = "then load the new one from an environment variable or a secrets manager."

RULES = [
    Rule("aws-access-key", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"), "high",
         "Matches the AWS access key id format.",
         "Deactivate it: aws iam update-access-key --access-key-id <KEY_ID> --status Inactive. Create a replacement, " + ROTATE_ENV),
    Rule("private-key-block", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"), "high",
         "A private key header was added.",
         "Treat the key as compromised: generate a new key pair, replace the public key wherever it is authorized, "
         "and keep the private key outside the repository.", mask=False),
    Rule("github-token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,255})\b"), "high",
         "Matches the GitHub token format.",
         "Revoke it at github.com/settings/tokens, issue a new one, " + ROTATE_ENV),
    Rule("slack-token", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b"), "high",
         "Matches the Slack token format.",
         "Revoke it with the Slack auth.revoke method or in the app settings, issue a new one, " + ROTATE_ENV),
    Rule("google-api-key", re.compile(r"\b(AIza[0-9A-Za-z_-]{35})\b"), "high",
         "Matches the Google API key format.",
         "Regenerate it under APIs & Services, Credentials in Google Cloud and restrict the new key by API and referrer, " + ROTATE_ENV),
    Rule("jwt", re.compile(r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"), "medium",
         "Looks like a JSON Web Token.",
         "Invalidate the token or rotate the signing secret, and keep tokens out of source."),
    Rule("generic-assignment",
         re.compile(r"""(?i)(?<![\w.-])[\w.-]{0,64}(?:password|passwd|secret|token|api[_-]?key)[\w.-]{0,64}['"]?\s*(?::=|[:=])\s*['"]([^'"\s]{8,1024})['"]"""),
         "medium", "A credential-like name is assigned a literal value.",
         "Change the credential, " + ROTATE_ENV),
    Rule("high-entropy-string", re.compile(r"""['"]([A-Za-z0-9+/=_-]{20,})['"]"""), "low",
         "Random-looking string, possibly a key.",
         "If it is a credential, rotate it, " + ROTATE_ENV),
]

ENTROPY_MIN = 4.2  # ponytail: hex keys top out near 4.0 and are missed; add a hex-specific threshold if needed
