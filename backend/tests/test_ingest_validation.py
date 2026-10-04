"""Ingest hardening that needs no database: typed-field validation, JSON number
handling, and the two-layer rate limiter (pre-auth per IP, per tenant after auth)."""
import inspect
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.routers import ingest
from app.utils.deps import authenticate_api_key

FIELD_MAP = {
    "transaction_id": "txn.ref_id",
    "transaction_amount": "txn.amount",
    "transaction_currency": "txn.currency",
    "transaction_type": "txn.type",
    "risk_score": "risk.score",
}


def _status_detail(fn, *args):
    with pytest.raises(HTTPException) as exc:
        fn(*args)
    return exc.value.status_code, exc.value.detail


class TestParseAmount:
    def test_numbers_and_numeric_strings(self):
        assert ingest._parse_amount({"transaction_amount": 990000}, FIELD_MAP) == Decimal("990000")
        assert ingest._parse_amount({"transaction_amount": 12.5}, FIELD_MAP) == Decimal("12.5")
        assert ingest._parse_amount({"transaction_amount": " 990000.00 "}, FIELD_MAP) == Decimal("990000")

    def test_missing_is_null(self):
        assert ingest._parse_amount({}, FIELD_MAP) is None
        assert ingest._parse_amount({"transaction_amount": None}, FIELD_MAP) is None
        assert ingest._parse_amount({"transaction_amount": ""}, FIELD_MAP) is None

    @pytest.mark.parametrize("value", ["N/A", "1,000", True, {"v": 1}, [1]])
    def test_non_numeric_is_422_naming_field(self, value):
        status, detail = _status_detail(ingest._parse_amount, {"transaction_amount": value}, FIELD_MAP)
        assert status == 422
        assert "transaction_amount (txn.amount)" in detail

    @pytest.mark.parametrize("value", ["inf", "-Infinity", "NaN", float("inf"), float("nan")])
    def test_non_finite_is_422(self, value):
        status, detail = _status_detail(ingest._parse_amount, {"transaction_amount": value}, FIELD_MAP)
        assert status == 422
        assert "finite" in detail

    @pytest.mark.parametrize("value", [1e308, -1e16, 10 ** 400, "1e999999999999", "9999999999999999.99995"])
    def test_out_of_numeric_range_is_422(self, value):
        status, detail = _status_detail(ingest._parse_amount, {"transaction_amount": value}, FIELD_MAP)
        assert status == 422
        assert "out of range" in detail

    def test_largest_storable_amount_and_rounding(self):
        assert ingest._parse_amount({"transaction_amount": "9999999999999999.9999"}, FIELD_MAP) == Decimal("9999999999999999.9999")
        assert ingest._parse_amount({"transaction_amount": "0.00005"}, FIELD_MAP) == Decimal("0.0001")


class TestTextFields:
    @pytest.mark.parametrize("field,limit", [
        ("transaction_id", 255), ("transaction_currency", 10), ("transaction_type", 50),
    ])
    def test_over_column_width_is_422(self, field, limit):
        assert ingest._clean_text_field({field: "x" * limit}, FIELD_MAP, field) == "x" * limit
        status, detail = _status_detail(ingest._clean_text_field, {field: "x" * (limit + 1)}, FIELD_MAP, field)
        assert status == 422
        assert detail.startswith(f"{field} (") and f"at most {limit}" in detail

    def test_currency_from_bug_report(self):
        status, detail = _status_detail(
            ingest._clean_text_field, {"transaction_currency": "RUPEES-LONG-CURRENCY-CODE"},
            FIELD_MAP, "transaction_currency")
        assert status == 422 and "transaction_currency" in detail

    @pytest.mark.parametrize("value", [{"a": 1}, ["x"], True])
    def test_non_scalar_is_422(self, value):
        status, _ = _status_detail(ingest._clean_text_field, {"transaction_id": value}, FIELD_MAP, "transaction_id")
        assert status == 422

    def test_nul_is_422(self):
        status, _ = _status_detail(ingest._clean_text_field, {"transaction_type": "WIRE\x00"}, FIELD_MAP, "transaction_type")
        assert status == 422

    @pytest.mark.parametrize("field", ["transaction_id", "transaction_currency", "transaction_type"])
    def test_unpaired_surrogate_is_422_naming_field(self, field):
        # psycopg2 cannot UTF-8 encode it: was a UnicodeEncodeError (500) at flush
        status, detail = _status_detail(ingest._clean_text_field, {field: "A\ud800"}, FIELD_MAP, field)
        assert status == 422
        assert detail.startswith(f"{field} (") and "surrogate" in detail

    def test_missing_or_blank_is_none_never_the_string_none(self):
        for normalized in ({}, {"transaction_id": None}, {"transaction_id": "  "}):
            assert ingest._clean_text_field(normalized, FIELD_MAP, "transaction_id") is None

    def test_numeric_id_is_kept_as_text(self):
        assert ingest._clean_text_field({"transaction_id": 123456}, FIELD_MAP, "transaction_id") == "123456"


class TestTimestamp:
    def test_iso_8601(self):
        ts = ingest._parse_txn_timestamp("2026-06-10T09:30:00Z")
        assert ts.utcoffset() == timedelta(0) and ts.hour == 9

    def test_missing_is_none(self):
        assert ingest._parse_txn_timestamp(None) is None
        assert ingest._parse_txn_timestamp("") is None

    @pytest.mark.parametrize("value", ["yesterday", "2026-13-45", 1718000000, {"t": 1}])
    def test_unparseable_raises(self, value):
        with pytest.raises(ValueError) as exc:
            ingest._parse_txn_timestamp(value)
        assert not isinstance(exc.value, ingest._TimestampOutOfRange)

    @pytest.mark.parametrize("value", [
        # Valid ISO 8601, but the UTC instant Postgres stores is outside Python's
        # years 1-9999: committed fine, then every read of the alert raised
        "9999-12-31T23:00:00-05:00",
        "0001-01-01T00:00:00+05:30",  # .NET DateTime.MinValue with an IST offset
        "0001-01-01T00:00:00Z",
        "1899-12-31T23:59:59Z",
        "2101-01-01T00:00:00",
        "2100-12-31T23:00:00-05:00",  # 2101 in UTC
    ])
    def test_out_of_range_raises(self, value):
        with pytest.raises(ingest._TimestampOutOfRange):
            ingest._parse_txn_timestamp(value)

    @pytest.mark.parametrize("value", ["1900-01-01T00:00:00Z", "2100-12-31T23:59:59Z", "2100-12-31T23:59:59"])
    def test_range_bounds_inclusive(self, value):
        assert ingest._parse_txn_timestamp(value) is not None


class TestRiskScore:
    @pytest.mark.parametrize("value", [87, "87", "high", None, {"x": 1}])
    def test_tolerated(self, value):
        ingest._check_risk_score({"risk_score": value}, FIELD_MAP)

    @pytest.mark.parametrize("value", [float("inf"), "1e999", "nan", 10 ** 400])
    def test_non_finite_is_422(self, value):
        status, detail = _status_detail(ingest._check_risk_score, {"risk_score": value}, FIELD_MAP)
        assert status == 422 and "risk_score" in detail


class TestLoadsPayload:
    def test_plain_json(self):
        assert ingest._loads_payload(b'{"a": 1.5, "b": [2]}') == ({"a": 1.5, "b": [2]}, False)

    @pytest.mark.parametrize("body", [b'{"a": NaN}', b'{"a": [Infinity]}', b'{"a": {"b": 1e400}}'])
    def test_flags_non_finite(self, body):
        assert ingest._loads_payload(body)[1] is True


class TestEncodesAsUtf8:
    @pytest.mark.parametrize("body", [b'{"a": "\\ud800"}', b'{"a": {"b": ["x\\udfff"]}}', b'{"\\ud800": 1}'])
    def test_lone_surrogate_anywhere(self, body):
        assert ingest._encodes_as_utf8(ingest._loads_payload(body)[0]) is False

    def test_paired_surrogates_and_non_ascii_pass(self):
        payload, _ = ingest._loads_payload('{"a": "\\ud83d\\ude00", "b": "₹ 990000"}'.encode())
        assert payload["a"] == "\U0001F600"
        assert ingest._encodes_as_utf8(payload) is True


class TestHandlerRunsInThreadpool:
    def test_ingest_payload_is_sync(self):
        # A coroutine handler ran its blocking DB calls on the event loop and froze
        # the worker under load; a plain def is dispatched to the threadpool.
        assert not inspect.iscoroutinefunction(ingest.ingest_payload)


class TestClientIpKey:
    def _req(self, host):
        return SimpleNamespace(client=SimpleNamespace(host=host))

    def test_ipv4(self):
        assert ingest._client_ip_key(self._req("203.0.113.7")) == "203.0.113.7"

    def test_ipv6_grouped_by_64(self):
        a = ingest._client_ip_key(self._req("2001:db8:1:2::1"))
        b = ingest._client_ip_key(self._req("2001:db8:1:2:ffff::9"))
        assert a == b == "2001:db8:1:2::/64"

    def test_ipv4_mapped(self):
        assert ingest._client_ip_key(self._req("::ffff:203.0.113.7")) == "203.0.113.7"


class TestSlidingWindowLimiter:
    def test_429_after_limit_with_retry_after(self):
        limiter = ingest._SlidingWindowLimiter()
        for _ in range(3):
            limiter.hit("k", 3)
        with pytest.raises(HTTPException) as exc:
            limiter.hit("k", 3)
        assert exc.value.status_code == 429
        assert int(exc.value.headers["Retry-After"]) >= 1
        limiter.hit("other", 3)  # buckets are independent

    def test_bucket_table_is_capped(self):
        limiter = ingest._SlidingWindowLimiter(max_buckets=2)
        limiter.hit("a", 5)
        limiter.hit("b", 5)
        with pytest.raises(HTTPException) as exc:
            limiter.hit("c", 5)
        assert exc.value.status_code == 429


@pytest.fixture
def limited_client(monkeypatch):
    """Ingest router alone (no logging middleware/DB) with fresh limiters."""
    monkeypatch.setattr(ingest, "_ip_rate_limiter", ingest._SlidingWindowLimiter())
    monkeypatch.setattr(ingest, "_tenant_rate_limiter", ingest._SlidingWindowLimiter())
    app = FastAPI()
    app.include_router(ingest.router)
    yield app, TestClient(app)
    app.dependency_overrides.clear()


def _reject_all_keys():
    raise HTTPException(status_code=401, detail="Invalid API Key or Tenant ID")


class TestRateLimitHttp:
    def test_failed_auth_never_touches_tenant_quota(self, limited_client, monkeypatch):
        app, client = limited_client
        app.dependency_overrides[authenticate_api_key] = _reject_all_keys
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_MINUTE", 3)
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_IP_PER_MINUTE", 1000)
        headers = {"X-API-Key": "attacker-garbage", "X-Tenant-ID": "TEN-0017"}
        codes = [client.post("/api/v1/ingest/", json={}, headers=headers).status_code for _ in range(10)]
        assert codes == [401] * 10
        assert not ingest._tenant_rate_limiter._buckets

    def test_rotating_tenant_id_cannot_dodge_ip_limit(self, limited_client, monkeypatch):
        app, client = limited_client
        app.dependency_overrides[authenticate_api_key] = _reject_all_keys
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_IP_PER_MINUTE", 5)
        codes = [
            client.post("/api/v1/ingest/", json={},
                        headers={"X-API-Key": "k", "X-Tenant-ID": f"TEN-{i:04d}"}).status_code
            for i in range(8)
        ]
        assert codes == [401] * 5 + [429] * 3

    def test_tenant_quota_counts_only_after_auth(self, limited_client, monkeypatch):
        app, client = limited_client
        tenant = SimpleNamespace(id="11111111-1111-1111-1111-111111111111")

        def fake_auth():
            return tenant

        app.dependency_overrides[authenticate_api_key] = fake_auth
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_MINUTE", 2)
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_IP_PER_MINUTE", 1000)
        # Malformed JSON stops the handler before any DB work, so this needs no DB
        codes = [
            client.post("/api/v1/ingest/", content=b"{not json",
                        headers={"X-API-Key": "k", "X-Tenant-ID": "TEN-0001"}).status_code
            for _ in range(3)
        ]
        assert codes == [400, 400, 429]


class TestStartupSweep:
    def test_fails_old_alerts_now_and_pre_boot_ones_after_grace(self, monkeypatch):
        import threading
        from datetime import datetime, timezone
        from app import main

        calls, timers = [], []
        swept = threading.Event()

        def fake_fail(started_before):
            calls.append(started_before)
            swept.set()
            return 0

        class FakeTimer:
            def __init__(self, interval, fn, args=()):
                timers.append((interval, fn, args))
                self.daemon = False

            def start(self):
                pass

        monkeypatch.setattr(main.ingest, "fail_stuck_processing_alerts", fake_fail)
        monkeypatch.setattr(main.threading, "Timer", FakeTimer)
        monkeypatch.setattr(settings, "STUCK_PROCESSING_TIMEOUT_MINUTES", 15)
        before = datetime.now(timezone.utc)
        main._sweep_stuck_processing_alerts()
        assert swept.wait(5)
        [(interval, fn, (boot,))] = timers
        assert interval == 15 * 60 and boot >= before
        # Immediately: only alerts already older than the grace period
        assert calls == [boot - timedelta(minutes=15)]
        # Later: everything that started before this boot (a previous worker's orphans)
        fn(boot)
        assert calls[-1] == boot
