"""Auth/tenant fixes that need no database: email normalization, request/response
schemas, the production config guard, comped-tenant config and the docs auth scheme."""
import uuid
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import Settings, settings
from app.schemas.auth import UserLogin, UserSignup
from app.schemas.tenant import TenantApproveResponse, TenantRejectRequest, TenantResponse


class TestEmailNormalization:
    def test_login_email_is_lowercased_and_trimmed(self):
        assert UserLogin(email="  Admin@TestFintech.IN ", password="x").email == "admin@testfintech.in"

    def test_signup_email_is_lowercased(self):
        s = UserSignup(
            company_name="Acme Bank", company_type="BANK", admin_email="Jane.Doe@ACME.example.com",
            admin_password="correct-horse-battery", admin_name="Jane",
        )
        assert s.email == "jane.doe@acme.example.com"

    def test_invalid_email_still_rejected(self):
        with pytest.raises(ValidationError):
            UserLogin(email="not-an-email", password="x")


class TestTenantSchemas:
    def test_tenant_response_accepts_uuid_id(self):
        tid = uuid.uuid4()
        row = SimpleNamespace(id=tid, name="Acme", slug="acme", company_type="BANK",
                              status="ACTIVE", tenant_id_public="TEN-0001")
        body = TenantResponse.model_validate(row).model_dump(mode="json")
        assert body["id"] == str(tid)
        assert body["tenant_id_public"] == "TEN-0001"

    def test_approve_response_carries_public_id_and_uuid(self):
        tid = uuid.uuid4()
        body = TenantApproveResponse(tenant_id="TEN-0042", id=tid, status="ACTIVE",
                                     api_key="sk-ae-x").model_dump(mode="json")
        assert body["tenant_id"] == "TEN-0042"
        assert body["id"] == str(tid)

    @pytest.mark.parametrize("reason", ["", "   ", "\n\t", "ok"])
    def test_reject_reason_blank_or_too_short_is_invalid(self, reason):
        with pytest.raises(ValidationError):
            TenantRejectRequest(reason=reason)

    def test_reject_reason_is_trimmed(self):
        assert TenantRejectRequest(reason="  Unable to verify CIN.  ").reason == "Unable to verify CIN."

    def test_reject_reason_has_upper_bound(self):
        with pytest.raises(ValidationError):
            TenantRejectRequest(reason="x" * 2001)


def _prod(**kw) -> Settings:
    base = dict(ENVIRONMENT="production", SECRET_KEY="s" * 64, PII_ENCRYPTION_KEY=Fernet.generate_key().decode())
    base.update(kw)
    return Settings(_env_file=None, **base)


class TestProductionConfigGuard:
    def test_valid_production_config_passes(self):
        assert _prod().production_config_errors() == []

    def test_malformed_pii_key_is_rejected(self):
        errors = _prod(PII_ENCRYPTION_KEY="not-a-fernet-key").production_config_errors()
        assert any("not a valid Fernet key" in e for e in errors)

    def test_missing_pii_key_still_rejected(self):
        errors = _prod(PII_ENCRYPTION_KEY="").production_config_errors()
        assert any("must be set" in e for e in errors)

    def test_development_is_not_checked(self):
        s = Settings(_env_file=None, ENVIRONMENT="development", PII_ENCRYPTION_KEY="not-a-fernet-key")
        assert s.production_config_errors() == []


class TestCompedTenants:
    def test_parses_comma_separated_public_ids(self):
        s = Settings(_env_file=None, COMPED_TENANT_IDS=" ten-0005, TEN-0007 ,,")
        assert s.comped_tenant_ids == {"TEN-0005", "TEN-0007"}

    def test_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("COMPED_TENANT_IDS", raising=False)
        assert Settings(_env_file=None).comped_tenant_ids == frozenset()

    def test_billing_and_plan_pins_follow_the_setting(self):
        # No hard-coded public id: both the billing exemption and the free-plan pin come
        # from COMPED_TENANT_IDS, whatever it is set to in this environment.
        from app.routers.tenant import FREE_ACCESS_TENANTS
        from app.services.model_router import TENANT_PLAN_OVERRIDES, resolve_plan

        assert FREE_ACCESS_TENANTS == settings.comped_tenant_ids
        for tid in settings.comped_tenant_ids:
            assert TENANT_PLAN_OVERRIDES[tid] == "free"
            assert resolve_plan(SimpleNamespace(tenant_id_public=tid)) == "free"
        assert set(TENANT_PLAN_OVERRIDES) == set(settings.comped_tenant_ids)


class TestDocsAuthScheme:
    def test_openapi_advertises_http_bearer_not_password_flow(self):
        from app.main import app

        schemes = app.openapi()["components"]["securitySchemes"]
        assert schemes == {"HTTPBearer": {"type": "http", "scheme": "bearer"}}

    def test_missing_token_is_401_not_403(self):
        # HTTPBearer's own auto_error answers 403; the SPA's refresh interceptor keys on 401
        from app.utils.deps import get_current_user

        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=None, db=None)
        assert exc.value.status_code == 401
        assert exc.value.headers == {"WWW-Authenticate": "Bearer"}
