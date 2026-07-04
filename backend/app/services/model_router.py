"""Single source of truth for WHICH drafting model / provider / API key a tenant's SARs are
generated with — keyed by the tenant's PLAN.

Reality today (2026-07): the platform is FREE-only. Every tenant — including **TEN-0005
(Meridian Bank), our live demo tenant, which has free access ONLY** — drafts on the free tier:
Groq (llama-3.3-70b) with a Gemini failover, using the keys already in `.env`.

The PRO tier below is deliberate SCAFFOLDING, not a live path:
  * its provider/model are wired, but `ANTHROPIC_API_KEY` is an empty PLACEHOLDER in config,
  * and `resolve_plan()` returns "free" for everyone right now.

When we turn on paid inference, a future client's plan selects the tier here and nothing else
changes: set `ANTHROPIC_API_KEY`, give the tenant a paid plan (via `TENANT_PLAN_OVERRIDES` or,
later, a real `tenants.plan` column), and PRO-tier SARs route to Anthropic automatically.

Keep this the ONLY place that maps plan -> model/provider/key.
"""
from app.config import settings

# ── Provider tiers ────────────────────────────────────────────────────
FREE_TIER = "free"   # Groq -> Gemini failover (real, working, free-tier keys)
PRO_TIER = "pro"     # Anthropic Opus/Sonnet (PLACEHOLDER — no key until paid launches)

# ── Plan -> tier ──────────────────────────────────────────────────────
# Billing plan ids (see tenant.py billing_plans) collapse onto the two provider tiers.
# Everything is FREE today; the paid rows are placeholders.
PLAN_TIER = {
    "free": FREE_TIER,
    "standard": FREE_TIER,     # current default plan — runs on the free provider chain
    "growth": FREE_TIER,
    "scale": FREE_TIER,
    "premium": PRO_TIER,       # paid drafting (Opus) — placeholder, not yet live
    "pro": PRO_TIER,
    "enterprise": PRO_TIER,
}

# ── Explicit per-tenant plan pins (placeholder map) ───────────────────
# Tenants pinned to a specific plan by public id. TEN-0005 (Meridian) is FREE ACCESS ONLY —
# pinned here so it can never be routed to a paid model or billed, whatever we do with plans.
# Future paying clients would either get a pin here or (later) a real `tenants.plan` column.
TENANT_PLAN_OVERRIDES = {
    "TEN-0005": "free",
    # "TEN-0006": "premium",   # <- example: a future paying client on the PRO tier
}


def resolve_plan(tenant) -> str:
    """The plan id for a tenant. Resolution order:
      1. explicit pin in TENANT_PLAN_OVERRIDES (TEN-0005 -> free),
      2. (future) a real `tenants.plan` column — TODO below,
      3. default: "free" (the whole platform today).
    """
    if tenant is not None:
        pub = getattr(tenant, "tenant_id_public", None)
        if pub in TENANT_PLAN_OVERRIDES:
            return TENANT_PLAN_OVERRIDES[pub]
        # TODO(paid): when a `tenants.plan` column exists, prefer it here:
        #   plan = getattr(tenant, "plan", None)
        #   if plan: return plan
    return "free"


def tier_config(tier: str) -> dict:
    """Drafting config for a provider tier: provider failover chain, model, key, and whether
    it's a not-yet-live placeholder. `api_key` empty => placeholder (paid tier not enabled)."""
    if tier == PRO_TIER:
        return {
            "tier": PRO_TIER,
            "provider_chain": ["anthropic"],
            "model_name": settings.PRO_MODEL,          # e.g. claude-opus-4-8 (placeholder)
            "api_key": settings.ANTHROPIC_API_KEY,     # empty today => placeholder
            "is_placeholder": not bool(settings.ANTHROPIC_API_KEY),
        }
    # FREE tier — the real, working path today: primary provider then optional failover.
    primary = (settings.LLM_PROVIDER or "groq").lower()
    fallback = (settings.LLM_FALLBACK_PROVIDER or "").lower()
    chain = [primary] + ([fallback] if fallback and fallback != primary else [])
    return {
        "tier": FREE_TIER,
        "provider_chain": chain,
        "model_name": settings.GROQ_MODEL,
        "api_key": settings.GROQ_API_KEY,
        "is_placeholder": False,
    }


def resolve_drafting(tenant) -> dict:
    """Full drafting config for a tenant, selected by its plan. This is what generation calls.
    Returns keys: plan, tier, provider_chain, model_name, api_key, is_placeholder."""
    plan = resolve_plan(tenant)
    cfg = tier_config(PLAN_TIER.get(plan, FREE_TIER))
    cfg["plan"] = plan
    return cfg
