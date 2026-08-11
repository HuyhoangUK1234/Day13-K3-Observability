from __future__ import annotations

import hashlib
import re

# scrub_text thay thế tuần tự theo thứ tự dict, nên email phải đứng trước các pattern số:
# nếu phone_vn chạy trước, "user0901234567@example.com" bị cắt thành
# "user[REDACTED_PHONE_VN]@example.com" và tên miền vẫn lộ.
# Các pattern số còn lại độc lập với nhau vì \b chặn dãy ngắn khớp bên trong dãy dài.
PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport_vn": r"\b[A-Z]\d{7}\b",
    "cmnd": r"\b\d{9}\b",
    "dob": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
    "address_vn": r"(?i)\b(?:số nhà|ngõ|ngách|đường|phố|phường|quận|huyện)\s+[^\n,;]{1,40}",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
