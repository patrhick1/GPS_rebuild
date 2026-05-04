"""Pure functions that build the JSON payloads sent to webhooks.

Kept separate from webhook_service.py so they can be unit-tested without
mocking httpx.

Assessment payload shape matches the legacy OpenAPI spec from Doug Niccum
(see PRD addendum §3.3) with one addition: an `instrument` field on the
assessment object so receivers can distinguish GPS from MyImpact.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.gifts_passion import GiftsPassion
from app.models.myimpact_result import MyImpactResult
from app.models.organization import Organization
from app.models.user import User


def _gift_to_dict(gp: GiftsPassion, points: Optional[int]) -> dict[str, Any]:
    return {
        "id": str(gp.id) if gp else None,
        "name": gp.name if gp else None,
        "abbreviation": gp.short_code if gp else None,
        "description": gp.description if gp else None,
        "points": points,
    }


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _user_block(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
    }


def build_assessment_payload(
    *,
    assessment: Assessment,
    user: User,
    organization: Optional[Organization],
    result: Optional[AssessmentResult] = None,
    myimpact_result: Optional[MyImpactResult] = None,
    gifts_by_id: Optional[dict] = None,
    story_questions: Optional[Iterable[dict]] = None,
) -> dict[str, Any]:
    """Build the assessment_completed webhook payload.

    Caller passes EITHER `result` (GPS) or `myimpact_result` (MyImpact).
    `gifts_by_id` is an optional pre-fetched {gift_id: GiftsPassion} map so
    we don't re-query for each of the up-to-7 gift/passion lookups.
    `story_questions` is an iterable of {question, questionEs, answer} dicts
    if available.
    """
    if assessment.instrument_type == "myimpact":
        return _build_myimpact_payload(
            assessment=assessment,
            user=user,
            organization=organization,
            myimpact_result=myimpact_result,
        )

    return _build_gps_payload(
        assessment=assessment,
        user=user,
        organization=organization,
        result=result,
        gifts_by_id=gifts_by_id or {},
        story_questions=list(story_questions) if story_questions else [],
    )


def _build_gps_payload(
    *,
    assessment: Assessment,
    user: User,
    organization: Optional[Organization],
    result: Optional[AssessmentResult],
    gifts_by_id: dict,
    story_questions: list,
) -> dict[str, Any]:
    gifts = []
    top_gifts = []
    if result:
        for idx, (gid_attr, score_attr) in enumerate(
            [
                ("gift_1_id", "spiritual_gift_1_score"),
                ("gift_2_id", "spiritual_gift_2_score"),
                ("gift_3_id", "spiritual_gift_3_score"),
                ("gift_4_id", "spiritual_gift_4_score"),
            ],
            start=1,
        ):
            gid = getattr(result, gid_attr)
            score = getattr(result, score_attr)
            if not gid:
                continue
            gp = gifts_by_id.get(gid)
            entry = _gift_to_dict(gp, score)
            gifts.append(entry)
            if idx <= 3:  # top 3 by score in legacy convention
                top_gifts.append(entry)

    passions = []
    top_passion = []
    if result:
        for idx, (pid_attr, score_attr) in enumerate(
            [
                ("passion_1_id", "passion_1_score"),
                ("passion_2_id", "passion_2_score"),
                ("passion_3_id", "passion_3_score"),
            ],
            start=1,
        ):
            pid = getattr(result, pid_attr)
            score = getattr(result, score_attr)
            if not pid:
                continue
            gp = gifts_by_id.get(pid)
            entry = _gift_to_dict(gp, score)
            passions.append(entry)
            if idx == 1:
                top_passion.append(entry)

    payload = {
        "user": _user_block(user),
        "organization": _organization_block(organization),
        "assessment": {
            "id": str(assessment.id),
            "instrument": "gps",
            "completedAt": _iso(assessment.completed_at),
            "gifts": gifts,
            "topGifts": top_gifts,
            "passions": passions,
            "topPassion": top_passion,
            "abilities": _split_csv(result.abilities) if result else [],
            "people": _split_csv(result.people) if result else [],
            "causes": _split_csv(result.cause) if result else [],
            "stories": story_questions,
        },
    }
    return payload


def _build_myimpact_payload(
    *,
    assessment: Assessment,
    user: User,
    organization: Optional[Organization],
    myimpact_result: Optional[MyImpactResult],
) -> dict[str, Any]:
    scores = None
    if myimpact_result:
        scores = {
            "character": myimpact_result.character_score,
            "calling": myimpact_result.calling_score,
            "myImpact": myimpact_result.myimpact_score,
            "characterBreakdown": myimpact_result.get_character_breakdown(),
            "callingBreakdown": myimpact_result.get_calling_breakdown(),
        }

    return {
        "user": _user_block(user),
        "organization": _organization_block(organization),
        "assessment": {
            "id": str(assessment.id),
            "instrument": "myimpact",
            "completedAt": _iso(assessment.completed_at),
            "myImpactScores": scores,
        },
    }


def _organization_block(organization: Optional[Organization]) -> Optional[dict[str, Any]]:
    if not organization:
        return None
    return {
        "id": str(organization.id),
        "name": organization.name,
        "key": organization.key,
    }


def _iso(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def build_user_registered_payload(
    *,
    user: User,
    organization: Organization,
    registered_at: datetime,
) -> dict[str, Any]:
    """user_registered payload (Zapier-shaped). Fires when a user becomes
    affiliated with a church (link registration, request approval, invite
    accept). Independent registrations (no org) do NOT fire."""
    return {
        "event": "user_registered",
        "user": {
            "id": str(user.id),
            "firstName": user.first_name,
            "lastName": user.last_name,
            "email": user.email,
            # User model uses `phone_number`; fall back to `phone` for stubs/tests.
            "phone": getattr(user, "phone_number", None) or getattr(user, "phone", None),
        },
        "church": {
            "id": str(organization.id),
            "name": organization.name,
            "key": organization.key,
        },
        "registeredAt": _iso(registered_at),
    }


def build_test_assessment_payload(*, event_type: str) -> dict[str, Any]:
    """Test payload for the 'Test Connection' button. Real shape, fake data,
    plus a root-level `test: true` flag so receivers can ignore."""
    if event_type == "user_registered":
        return {
            "test": True,
            "event": "user_registered",
            "user": {
                "id": "00000000-0000-0000-0000-000000000000",
                "firstName": "Test",
                "lastName": "User",
                "email": "test@example.com",
                "phone": "555-0100",
            },
            "church": {
                "id": "00000000-0000-0000-0000-000000000000",
                "name": "Test Church",
                "key": "test-church",
            },
            "registeredAt": _iso(datetime.now(timezone.utc)),
        }

    # default: assessment_completed test payload
    return {
        "test": True,
        "user": {
            "id": "00000000-0000-0000-0000-000000000000",
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
        },
        "organization": {
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "Test Church",
            "key": "test-church",
        },
        "assessment": {
            "id": "00000000-0000-0000-0000-000000000000",
            "instrument": "gps",
            "completedAt": _iso(datetime.now(timezone.utc)),
            "gifts": [
                {"id": "1", "name": "Wisdom", "abbreviation": "W", "description": "...", "points": 20},
            ],
            "topGifts": [
                {"id": "1", "name": "Wisdom", "abbreviation": "W", "description": "...", "points": 20},
            ],
            "passions": [
                {"id": "2", "name": "Shepherd", "abbreviation": "S", "description": "...", "points": 77},
            ],
            "topPassion": [
                {"id": "2", "name": "Shepherd", "abbreviation": "S", "description": "...", "points": 77},
            ],
            "abilities": ["Project management"],
            "people": ["Singles"],
            "causes": ["Education"],
            "stories": [],
        },
    }
