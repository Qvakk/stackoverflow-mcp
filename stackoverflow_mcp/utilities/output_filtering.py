import re
from typing import Tuple

PII_PATTERNS = [
    re.compile(r"\b\d{11}\b"),  # Norwegian national ID
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Credit card
    re.compile(r"\b(?:\+47\s?)?\d{8}\b"),  # Norwegian phone
]

INJECTION_PATTERNS = [
    re.compile(r"<\|im_start\|>"),
    re.compile(r"<\|im_end\|>"),
    re.compile(r"\[INST\]"),
]


def sanitize_output(text: str) -> Tuple[str, int, int]:
    """Return sanitized text, (pii_count, injection_count)"""
    pii_count = 0
    inj_count = 0

    sanitized = text
    # redact PII
    for p in PII_PATTERNS:
        matches = p.findall(sanitized)
        if matches:
            pii_count += len(matches)
            sanitized = p.sub("[REDACTED]", sanitized)

    # remove injection tokens
    for p in INJECTION_PATTERNS:
        matches = p.findall(sanitized)
        if matches:
            inj_count += len(matches)
            sanitized = p.sub("", sanitized)

    # strip control chars
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)
    # normalize whitespace
    sanitized = re.sub(r"\n{4,}", "\n\n\n", sanitized)

    return sanitized, pii_count, inj_count
