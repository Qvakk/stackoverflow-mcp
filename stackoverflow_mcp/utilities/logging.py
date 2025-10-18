import logging
from enum import Enum
from typing import Any, Dict

logger = logging.getLogger("stackoverflow_mcp.security")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("[SECURITY][%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def log_event(event_type: str, severity: Severity, message: str, metadata: Dict[str, Any] | None = None) -> None:
    md = {}
    if metadata:
        # redact common secrets
        for k, v in metadata.items():
            if any(s in k.lower() for s in ("key", "token", "secret", "password")):
                md[k] = "[REDACTED]"
            else:
                md[k] = v if (isinstance(v, (str, int, float, bool)) and len(str(v)) < 200) else str(v)[:200] + "..."
    logger.info(f"{event_type} | {severity.value} | {message} | {md}")
