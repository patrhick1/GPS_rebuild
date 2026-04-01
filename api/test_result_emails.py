"""
Test script: sends sample GPS and MyImpact result emails to a given address.

Run from the api/ directory:
    python test_result_emails.py okonkworpaschal@gmail.com

Requirements: .env file present with RESEND_API_KEY set.
"""
import sys
import os
import types

# ── Load .env before importing app modules ─────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass  # pydantic-settings will read .env directly

# ── Resolve email address ──────────────────────────────────────────────────────
TO_EMAIL = sys.argv[1] if len(sys.argv) > 1 else "okonkworpaschal@gmail.com"
FIRST_NAME = "Paschal"
FAKE_ASSESSMENT_ID = "test-00000000-0000-0000-0000-000000000001"

# ── Import email functions (after env is loaded) ───────────────────────────────
from app.services.email_service import send_gps_result_email, send_myimpact_result_email
from app.core.config import settings

# ── Build mock GPS result ──────────────────────────────────────────────────────
gps_result = types.SimpleNamespace(
    id=FAKE_ASSESSMENT_ID,
    # Top 4 spiritual gifts
    gift_1_name="Administration",
    gift_1_description="The special ability to understand what makes an organization function and the discipline to make plans and carry out those plans to accomplish the goals of the body.",
    spiritual_gift_1_score=87,
    gift_2_name="Teaching",
    gift_2_description="The special ability to clearly explain and apply the truth of God's Word to the lives of people in a way that produces growth and maturity.",
    spiritual_gift_2_score=76,
    gift_3_name="Encouragement",
    gift_3_description="The special ability to offer words of comfort, encouragement, and counsel so that others feel helped and strengthened.",
    spiritual_gift_3_score=68,
    gift_4_name="Leadership",
    gift_4_description="The special ability to cast vision, motivate, and direct people in a way that moves the body toward a common goal.",
    spiritual_gift_4_score=61,
    # Top 3 influencing styles
    passion_1_name="Teacher",
    passion_1_description="Teachers communicate God's truth clearly and systematically, helping others understand and apply Scripture in their daily lives.",
    passion_2_name="Shepherd",
    passion_2_description="Shepherds care for and nurture others through long-term relationships, guiding people toward spiritual health and maturity.",
    passion_3_name="Prophet",
    passion_3_description="Prophets boldly speak truth, call people toward God, and are willing to confront sin and challenge the status quo.",
    # Selections
    abilities_list=["Teaching", "Writing", "Strategic Planning", "Public Speaking"],
    people_list=["College Students", "Young Adults", "Families"],
    cause_list=["Discipleship", "Church Planting", "Education"],
)

# ── Build mock MyImpact result ─────────────────────────────────────────────────
myimpact_result = types.SimpleNamespace(
    id=FAKE_ASSESSMENT_ID,
    # Character (Fruit of the Spirit) scores 1-10
    c1_loving=8,
    c2_joyful=7,
    c3_peaceful=6,
    c4_patient=7,
    c5_kind=9,
    c6_good=7,
    c7_faithful=8,
    c8_gentle=6,
    c9_self_controlled=7,
    character_score=7.2,
    # Calling scores 1-10
    cl1_know_gifts=8,
    cl2_know_people=7,
    cl3_using_gifts=6,
    cl4_see_impact=7,
    cl5_experience_joy=8,
    cl6_pray_regularly=6,
    cl7_see_movement=5,
    cl8_receive_support=7,
    calling_score=6.75,
    # Final score (character × calling)
    myimpact_score=48.6,
)

gps_url = f"{settings.FRONTEND_URL}/assessment-results?id={FAKE_ASSESSMENT_ID}"
myimpact_url = f"{settings.FRONTEND_URL}/myimpact-results?id={FAKE_ASSESSMENT_ID}"

# ── Send both emails ───────────────────────────────────────────────────────────
print(f"Sending GPS result email to {TO_EMAIL} ...")
send_gps_result_email(TO_EMAIL, FIRST_NAME, gps_result, results_url=gps_url)

print(f"Sending MyImpact result email to {TO_EMAIL} ...")
send_myimpact_result_email(TO_EMAIL, FIRST_NAME, myimpact_result, results_url=myimpact_url)

print("Done. Check your inbox!")
