import re
from dataclasses import dataclass


@dataclass
class SecurityScanResult:
    is_safe: bool
    sanitized_text: str
    detected_threats: list[str]
    redacted_pii_count: int


class EnterpriseGuardrails:
    # 1. PII Patterns
    PII_PATTERNS = {
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
        "API_KEY": r"\b(?:sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36})\b",
        "PHONE": r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.]?\d{3}[-.]?\d{4}\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    }

    # 2. Prompt Injection & Jailbreak Signatures
    INJECTION_SIGNATURES = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
        r"you\s+are\s+now\s+(a\s+)?(developer|admin|unrestricted|god\s+mode)",
        r"bypass\s+(all\s+)?security\s+protocols?",
        r"system\s*:?\s*override",
        r"disregard\s+(the\s+above|(all\s+)?(previous|prior)\s+instructions?)",
        r"jailbreak",
        r"reveal\s+(all\s+)?(api\s+keys?|passwords?|secrets?)",
    ]

    # 3. Role-Based Tool Allow-List (Least Privilege Enforcement)
    ALLOWED_TOOLS = {
        "triage_agent": [],
        "research_agent": ["search_it_knowledge_base", "lookup_user_history"],
        "action_agent": ["modify_ticket_priority"],
    }

    @classmethod
    def redact_pii(cls, text: str) -> tuple[str, int]:
        """Redacts sensitive PII before text is passed to any LLM or external API."""
        sanitized = text
        total_redactions = 0

        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, sanitized, flags=re.IGNORECASE)
            total_redactions += len(matches)
            sanitized = re.sub(pattern, f"<REDACTED_{pii_type}>", sanitized, flags=re.IGNORECASE)

        return sanitized, total_redactions

    @classmethod
    def detect_prompt_injection(cls, text: str) -> list[str]:
        """Scans for adversarial prompt injection and jailbreak payloads."""
        threats_found = []
        for pattern in cls.INJECTION_SIGNATURES:
            if re.search(pattern, text, flags=re.IGNORECASE):
                threats_found.append(f"Prompt Injection Signature: '{pattern}'")
        return threats_found

    @classmethod
    def scan_input(cls, raw_text: str) -> SecurityScanResult:
        """Full incoming security scan: runs PII redaction and injection detection."""
        threats = cls.detect_prompt_injection(raw_text)
        sanitized_text, pii_count = cls.redact_pii(raw_text)

        is_safe = len(threats) == 0
        return SecurityScanResult(
            is_safe=is_safe,
            sanitized_text=sanitized_text,
            detected_threats=threats,
            redacted_pii_count=pii_count,
        )

    @classmethod
    def validate_tool_permission(cls, agent_role: str, tool_name: str) -> bool:
        """Enforces least-privilege tool access based on agent role."""
        allowed = cls.ALLOWED_TOOLS.get(agent_role, [])
        return tool_name in allowed
