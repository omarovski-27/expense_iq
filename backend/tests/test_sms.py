"""Bank SMS capture (POST /api/ingest/sms).

REAL_* texts are typed from Omar's screenshots: Arab Bank (18 Nov 2026) and
Bank al Etihad (24 Nov 2026; those messages are from 2023).
SYNTHETIC_* texts are invented to cover message kinds we have no real
sample of yet; replace them with real ones when they arrive.
"""
from datetime import date

import pytest
from sqlmodel import Session, select

from models import Category, Expense, SmsIngest
from services.sms_service import normalize, parse_bank_sms, text_hash
from tests.conftest import TODAY

REAL_PURCHASE = (
    "JO\nتم قيد حركة شراء من حسابكم 0119*500 من Careem Food بمبلغ JOD 5.220 "
    "بتاريخ 17/11/2026 14:48 .الرصيد 64.109 دينار اردني."
)
REAL_PURCHASE_2 = (
    "JO\nتم قيد حركة شراء من حسابكم 0119*500 من Careem Food بمبلغ JOD 7.140 "
    "بتاريخ 16/05/2026 09:46 .الرصيد 56.969 دينار اردني."
)
# The same message in the order the phone *displays* it, with direction marks.
REAL_PURCHASE_VISUAL = (
    "JO\n‏تم قيد حركة شراء من حسابكم\n‎0119*500 من Careem Food بمبلغ\n"
    "17/11/2026 بتاريخ JOD 5.220\n14:48 .الرصيد 64.109 دينار اردني."
)
REAL_CLIQ_CREDIT = (
    "JOD25.000 has been credited to 0119*500 from SOMEONE as CliQ transfer. "
    "Balance 69.329JOD"
)
REAL_ESTATEMENT = (
    "Your eStatement has been issued for **2654. You can view it on Arabi Online "
    "or Arabi Mobile Tel 4600900"
)
ETIHAD_PURCHASE = "Purchase of JOD 7.313 from Patreon* Membership.\nAvailable balance: JOD 40.793."
ETIHAD_PURCHASE_AT = "7.313 JOD at CKO*Patreon.\nAvailable balance: 33.483 JOD."
ETIHAD_SECURITY_CODE = (
    "Bank al Etihad Transfer Security Code: 615236\nThis code will be used to "
    "perform a transfer of 28 JOD from your account"
)
ETIHAD_PROMO = (
    "Book your tickets to the Amman Chamber Orchestra concert, an initiative of Bank al "
    "Etihad Foundation, featuring MISK Dance Company https://etih.ad/e/ACOjune17"
)
# The recipient's name is hidden in the screenshot; the rest is real.
ETIHAD_CLIQ_SENT = "28.000 JOD CliQ transfer to Test Person.\nAvailable balance: 5.480 JOD."
SYNTHETIC_ARABIC_MERCHANT = (
    "تم قيد حركة شراء من حسابكم 0119*500 من سامح مول بمبلغ JOD 12.500 "
    "بتاريخ 15/05/2026 18:02 .الرصيد 40.000 دينار اردني."
)
SYNTHETIC_SKIPS = {
    "otp": "رمز التحقق الخاص بكم هو 482913 لعملية شراء بمبلغ JOD 9.000",
    "declined": "تم رفض حركة شراء من Zara بمبلغ JOD 30.000",
    "refund": "تم عكس حركة شراء من Careem Food بمبلغ JOD 5.220",
    "atm": "تم قيد حركة سحب نقدي من صراف آلي بمبلغ JOD 20.000",
}


@pytest.fixture(autouse=True)
def _frozen_today(monkeypatch):
    import routers.ingest as ingest_module
    monkeypatch.setattr(ingest_module, "today_jordan", lambda: date.fromisoformat(TODAY))


def _sms(client, text):
    return client.post("/api/ingest/sms", json={"text": text})


def _expenses(engine):
    with Session(engine) as s:
        return s.exec(select(Expense).order_by(Expense.id)).all()


class TestParser:
    def test_reads_real_purchase(self):
        r = parse_bank_sms(REAL_PURCHASE)
        assert r.skipped is None
        assert (r.amount, r.merchant, r.date.isoformat()) == (5.22, "Careem Food", "2026-11-17")

    def test_display_order_and_direction_marks_read_the_same(self):
        a, b = parse_bank_sms(REAL_PURCHASE), parse_bank_sms(REAL_PURCHASE_VISUAL)
        assert (a.amount, a.merchant, a.date) == (b.amount, b.merchant, b.date)

    def test_balance_is_never_taken_as_the_amount(self):
        assert parse_bank_sms(REAL_PURCHASE).amount != 64.109

    def test_arabic_shop_name(self):
        r = parse_bank_sms(SYNTHETIC_ARABIC_MERCHANT)
        assert (r.amount, r.merchant) == (12.5, "سامح مول")

    def test_real_credit_and_statement_are_skipped(self):
        assert parse_bank_sms(REAL_CLIQ_CREDIT).skipped == "credit"
        assert parse_bank_sms(REAL_ESTATEMENT).skipped == "not_a_purchase"

    def test_other_kinds_are_skipped(self):
        for reason, text in SYNTHETIC_SKIPS.items():
            assert parse_bank_sms(text).skipped == reason, reason

    def test_unknown_message_is_skipped(self):
        assert parse_bank_sms("Hello from Arab Bank").skipped == "not_a_purchase"

    def test_etihad_purchases_both_wordings(self):
        a, b = parse_bank_sms(ETIHAD_PURCHASE), parse_bank_sms(ETIHAD_PURCHASE_AT)
        assert (a.skipped, a.amount, a.merchant, a.date) == (None, 7.313, "Patreon* Membership", None)
        assert (b.skipped, b.amount, b.merchant) == (None, 7.313, "CKO*Patreon")

    def test_etihad_cliq_sent_is_logged(self):
        r = parse_bank_sms(ETIHAD_CLIQ_SENT)
        assert (r.skipped, r.amount, r.merchant) == (None, 28.0, "CliQ to Test Person")

    def test_etihad_code_and_promo_are_skipped(self):
        assert parse_bank_sms(ETIHAD_SECURITY_CODE).skipped == "otp"
        assert parse_bank_sms(ETIHAD_PROMO).skipped == "not_a_purchase"

    def test_hash_ignores_spacing_and_direction_marks(self):
        assert text_hash(REAL_PURCHASE) == text_hash("‏" + REAL_PURCHASE.replace(" ", "  "))
        assert normalize("a \n b") == "a b"


class TestEndpoint:
    def test_purchase_becomes_expense(self, client, engine):
        r = _sms(client, REAL_PURCHASE_2)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True and "skipped" not in body
        (e,) = _expenses(engine)
        assert (e.amount, e.merchant, e.notes) == (7.14, "Careem Food", "via sms")
        assert e.date.isoformat() == "2026-05-16"
        assert body["expense"]["category"]["name"] == "Food"

    def test_same_sms_twice_logs_once(self, client, engine):
        _sms(client, REAL_PURCHASE_2)
        r = _sms(client, REAL_PURCHASE_2)
        assert r.json() == {"ok": True, "skipped": "duplicate", "message": "Already logged."}
        assert len(_expenses(engine)) == 1
        with Session(engine) as s:
            assert len(s.exec(select(SmsIngest)).all()) == 1

    def test_skips_write_nothing(self, client, engine):
        for text in [REAL_CLIQ_CREDIT, REAL_ESTATEMENT, ETIHAD_SECURITY_CODE, ETIHAD_PROMO,
                     *SYNTHETIC_SKIPS.values()]:
            body = _sms(client, text).json()
            assert body["ok"] is True and body["skipped"]
        assert _expenses(engine) == []

    def test_date_after_today_is_logged_today(self, client, engine):
        # REAL_PURCHASE is dated 17/11/2026, after the frozen test "today".
        _sms(client, REAL_PURCHASE)
        assert _expenses(engine)[0].date.isoformat() == TODAY

    def test_reuses_the_shops_last_category(self, client, engine):
        with Session(engine) as s:
            bills = s.exec(select(Category).where(Category.name == "Bills")).one()
            s.add(Expense(amount=1, description="Careem Food", merchant="Careem Food",
                          category_id=bills.id, date=date(2026, 5, 1)))
            s.commit()
        assert _sms(client, REAL_PURCHASE_2).json()["expense"]["category"]["name"] == "Bills"

    def test_etihad_purchase_without_date_is_logged_today(self, client, engine):
        body = _sms(client, ETIHAD_PURCHASE_AT).json()
        assert body["ok"] is True and "skipped" not in body
        (e,) = _expenses(engine)
        assert (e.amount, e.merchant, e.date.isoformat()) == (7.313, "CKO*Patreon", TODAY)

    def test_unknown_shop_goes_to_other(self, client):
        body = _sms(client, SYNTHETIC_ARABIC_MERCHANT).json()
        assert body["expense"]["category"]["name"] == "Other"

    def test_deleting_an_sms_expense_still_works(self, client, engine):
        expense_id = _sms(client, REAL_PURCHASE_2).json()["expense"]["id"]
        assert client.delete(f"/api/expenses/{expense_id}").status_code == 200
        # The fingerprint stays, so a resent copy is not re-added.
        assert _sms(client, REAL_PURCHASE_2).json()["skipped"] == "duplicate"

    def test_needs_key(self, anon_client):
        assert _sms(anon_client, REAL_PURCHASE).status_code == 401
