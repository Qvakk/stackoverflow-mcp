import re
from typing import Any, Iterable, List, Optional

# Limits
MAX_QUERY_LENGTH = 2000
MAX_TAGS = 10
MAX_TAG_LENGTH = 50
MAX_LIMIT = 100

SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(previous|all|earlier|prior)\s+instructions", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"you\s+are\s+now", re.I),
    re.compile(r"disregard\s+(earlier|previous|all)", re.I),
    re.compile(r"role\s*:\s*system", re.I),
]


class ValidationError(Exception):
    pass


def validate_query(query: str) -> str:
    if not query or not query.strip():
        raise ValidationError("Query must be non-empty")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValidationError(f"Query too long (max {MAX_QUERY_LENGTH} characters)")

    # Basic suspicious pattern detection
    for p in SUSPICIOUS_PATTERNS:
        if p.search(query):
            raise ValidationError("Suspicious content detected in query")

    # Remove control characters
    query = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query


def validate_tags(tags: Optional[Iterable[str]]) -> Optional[List[str]]:
    if tags is None:
        return None
    validated: List[str] = []
    for t in tags:
        if not isinstance(t, str) or not t.strip():
            continue
        tok = t.strip()
        if len(tok) > MAX_TAG_LENGTH:
            continue
        if len(validated) >= MAX_TAGS:
            break
        # Only allow alphanum, hyphen, underscore
        if not re.match(r"^[A-Za-z0-9_-]+$", tok):
            continue
        validated.append(tok.lower())
    return validated or None


def validate_limit(limit: Any) -> int:
    try:
        n = int(limit)
    except Exception:
        return 10
    if n <= 0:
        return 10
    return min(n, MAX_LIMIT)


def validate_question_id(qid: Any) -> int:
    try:
        n = int(qid)
    except Exception:
        raise ValidationError("Invalid question_id")
    if n <= 0:
        raise ValidationError("Invalid question_id")
    return n


def validate_error_message(error_message: str) -> str:
    if not error_message or not error_message.strip():
        raise ValidationError("error_message must be non-empty")
    if len(error_message) > 5000:
        raise ValidationError("error_message too long")
    # Strip paths and line numbers to reduce risk
    clean = re.sub(r"[\"\'].*?[\"\']", "", error_message)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean
