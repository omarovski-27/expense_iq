"""Read a forwarded bank SMS and decide whether it is a spend to log.

Built from real Arab Bank messages (Arabic purchase alerts, English CliQ
credit alerts, eStatement notices). Mixed Arabic/English text can reach us in
a different character order than the phone displays it, so nothing here
depends on word order: the amount, merchant, date and time are found by
shape, wherever they sit.

Safety rule: only a message that is clearly a purchase becomes an expense.
Anything else, including any message we don't recognise, is skipped with a
reason, so the worst case is a missed expense, never a wrong one.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

# Invisible direction marks phones insert around mixed Arabic/English text.
_BIDI = re.compile("[‎‏‪-‮⁦-⁩؜﻿]")

# Checked in this order; the first match decides. Credits and reversals come
# before the purchase check because their texts can also mention a purchase.
_SKIP_RULES: list[tuple[str, re.Pattern]] = [
    ("otp", re.compile(r"\b(otp|one[- ]time|verification code|passcode)\b|رمز|كلمة (ال)?سر|كلمة المرور", re.I)),
    ("declined", re.compile(r"declin|reject|unsuccessful|failed|insufficient|مرفوض|رفض|لم تتم|فشل|غير كاف", re.I)),
    ("refund", re.compile(r"refund|revers|cancel|استرداد|استرجاع|عكس|إلغاء|الغاء|مسترد", re.I)),
    ("credit", re.compile(r"credited|deposit|received|إيداع|ايداع|لحسابكم|وارد|دائن", re.I)),
    ("atm", re.compile(r"\batm\b|سحب نقدي|صراف", re.I)),
]
_PURCHASE = re.compile(r"شراء|\bpurchase\b|\bpos\b", re.I)

_AMOUNT = re.compile(r"(?:JOD|JD)\s*(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:JOD|JD)\b", re.I)
_BALANCE = re.compile(r"(?:الرصيد|balance)\s*:?\s*$", re.I)
_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_MASK = re.compile(r"\S*\d\*+\d\S*|\*+\d+")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9&'.\-]*")
_NOT_MERCHANT = {"jo", "jod", "jd", "pos", "purchase"}


@dataclass
class SmsResult:
    skipped: Optional[str] = None  # reason, or None when this is an expense
    amount: float = 0.0
    merchant: str = ""
    date: Optional[date] = None


def normalize(text: str) -> str:
    return " ".join(_BIDI.sub("", text).split())


def text_hash(text: str) -> str:
    """Stable fingerprint of a message, so the same SMS sent twice logs once."""
    return hashlib.sha256(normalize(text).lower().encode()).hexdigest()


def _amount(text: str) -> Optional[float]:
    for m in _AMOUNT.finditer(text):
        if _BALANCE.search(text[: m.start()][-15:]):
            continue  # "Balance 69.329JOD" is the balance, not the spend
        raw = (m.group(1) or m.group(2)).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 0:
            return value
    return None


def _merchant(text: str) -> str:
    # Drop everything that is clearly not the shop name, keep the Latin words.
    cleaned = _MASK.sub(" ", _TIME.sub(" ", _DATE.sub(" ", _AMOUNT.sub(" ", text))))
    words = [w for w in _LATIN_WORD.findall(cleaned) if w.lower() not in _NOT_MERCHANT]
    if words:
        return " ".join(words).strip(" .-")
    # Arabic shop name: the words between "من" (from) and "بمبلغ" (amount).
    m = re.search(r"من\s+((?:(?!من\s|بمبلغ)\S+\s+){1,5}?)بمبلغ", cleaned)
    return " ".join(m.group(1).split()) if m else ""


def _date(text: str) -> Optional[date]:
    m = _DATE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def parse_bank_sms(raw: str) -> SmsResult:
    text = normalize(raw)
    for reason, pattern in _SKIP_RULES:
        if pattern.search(text):
            return SmsResult(skipped=reason)
    if not _PURCHASE.search(text):
        return SmsResult(skipped="not_a_purchase")
    amount = _amount(text)
    if amount is None:
        return SmsResult(skipped="no_amount")
    return SmsResult(amount=amount, merchant=_merchant(text) or "Card purchase", date=_date(text))
