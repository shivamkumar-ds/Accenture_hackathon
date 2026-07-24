"""
Freshness evaluation for capability entities.

Computed fresh on every read, never persisted — verification_status
(the stored column) is never mutated here. Certificate-expiry-triggered
revalidation is explicitly M9's job (event-driven, with cascading
re-evaluation of active missions); doing any of that here, out of
order and without the cascade logic, would be scope creep disguised as
a bug fix. See 99_DECISIONS_LOG.md (D-112).
"""

from datetime import date

from app.core.config import get_settings

settings = get_settings()


def evaluate_freshness(entity) -> dict:
    """
    Works across all five capability entities. Only Certification has
    expiry_date (getattr with a default handles the other four).
    Staleness is judged from last_verified_at if it's ever been set,
    falling back to created_at — every entity has one or the other.
    """
    today = date.today()

    expiry_date = getattr(entity, "expiry_date", None)
    is_expired = expiry_date is not None and expiry_date < today

    reference_time = entity.last_verified_at or entity.created_at
    reference_date = reference_time.date()
    age_days = (today - reference_date).days
    is_stale = age_days > settings.capability_staleness_days

    if is_expired:
        freshness_status = "expired"
    elif is_stale:
        freshness_status = "stale"
    else:
        freshness_status = "current"

    return {"is_expired": is_expired, "is_stale": is_stale, "freshness_status": freshness_status}
