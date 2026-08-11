"""Ticari doküman render yardımcıları."""

from __future__ import annotations

from commercial_profile import COMPANY, DEFAULT_QUOTE, merge_quote
from subscription_plans import PLANS, format_try


def build_quote_context(overrides: dict | None = None) -> dict:
    quote = merge_quote(overrides)
    plan = PLANS.get(quote.get("plan_id") or "professional", PLANS["professional"])
    setup = plan["setup_price"]
    monthly = plan["monthly_price"]
    yearly_discounted = int(monthly * 12 * 0.85)
    total_yearly = setup + yearly_discounted

    payment_rows = quote.get("payment_terms")
    if not payment_rows:
        payment_rows = [
            ("Sözleşme imzası", 40, int(setup * 0.4)),
            ("Canlıya alma", 40, int(setup * 0.4)),
            ("30 gün stabilizasyon", 20, int(setup * 0.2)),
        ]

    return {
        "company": COMPANY,
        "quote": quote,
        "plan": plan,
        "setup_display": format_try(setup),
        "monthly_display": format_try(monthly),
        "yearly_service_display": format_try(yearly_discounted),
        "total_yearly_display": format_try(total_yearly),
        "payment_rows": [
            {"label": label, "pct": pct, "amount": format_try(amt)}
            for label, pct, amt in payment_rows
        ],
    }


def build_contract_context(overrides: dict | None = None) -> dict:
    ctx = build_quote_context(overrides)
    ctx["contract_no"] = quote_no_to_contract(ctx["quote"].get("quote_no", ""))
    return ctx


def quote_no_to_contract(quote_no: str) -> str:
    return quote_no.replace("TEKLIF", "SOZ").replace("Teklif", "SOZ")