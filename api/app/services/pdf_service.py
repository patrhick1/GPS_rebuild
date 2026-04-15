"""
PDF generation service for GPS and MyImpact assessment results.
Uses ReportLab Platypus for layout.
"""
from io import BytesIO
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect

from app.services.scoring_service import GradedAssessment

# Brand colours
TEAL = HexColor("#4CABB0")
CHARCOAL = HexColor("#3A3A3A")
GRAY_LIGHT = HexColor("#E5E5E5")
GOLD = HexColor("#F7A824")
PINK = HexColor("#E3A2A2")
WHITE = HexColor("#FFFFFF")


def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "Title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=36,
            textColor=CHARCOAL,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            textColor=CHARCOAL,
            spaceAfter=2,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=TEAL,
            spaceBefore=20,
            spaceAfter=8,
        ),
        "subsection_heading": ParagraphStyle(
            "SubsectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=CHARCOAL,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=CHARCOAL,
            leading=15,
            spaceAfter=4,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=CHARCOAL,
            leading=15,
        ),
        "score": ParagraphStyle(
            "Score",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=TEAL,
            alignment=TA_RIGHT,
        ),
        "gift_name": ParagraphStyle(
            "GiftName",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=CHARCOAL,
        ),
        "story_question": ParagraphStyle(
            "StoryQuestion",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=CHARCOAL,
            spaceAfter=2,
        ),
        "story_answer": ParagraphStyle(
            "StoryAnswer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=CHARCOAL,
            leading=15,
            spaceAfter=10,
        ),
        "tag": ParagraphStyle(
            "Tag",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=CHARCOAL,
        ),
    }
    return styles


def _gift_rows(graded: GradedAssessment, styles: dict) -> list:
    """Build table rows for the gifts section."""
    rows = []
    for gift in graded.gifts:
        name_para = Paragraph(gift.name, styles["gift_name"])
        desc_para = Paragraph(gift.description or "", styles["body"])
        score_para = Paragraph(f"Score: {gift.points}", styles["score"])
        rows.append([name_para, desc_para, score_para])
    return rows


def _passion_rows(graded: GradedAssessment, styles: dict) -> list:
    """Build table rows for the passions/influencing styles section."""
    rows = []
    for passion in graded.passions:
        name_para = Paragraph(passion.name, styles["gift_name"])
        desc_para = Paragraph(passion.description or "", styles["body"])
        score_para = Paragraph(f"Score: {passion.points}", styles["score"])
        rows.append([name_para, desc_para, score_para])
    return rows


def _item_table(rows: list) -> Table:
    """Render gift/passion rows as a 3-column table: name | description | score."""
    col_widths = [1.4 * inch, 4.5 * inch, 1.1 * inch]
    tbl = Table(rows, colWidths=col_widths, repeatRows=0)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
    ]))
    return tbl


def generate_pdf(
    graded: GradedAssessment,
    user_name: str,
    completed_at: Optional[datetime] = None,
) -> BytesIO:
    """
    Generate a GPS assessment results PDF.

    Args:
        graded: Scored GradedAssessment from ScoringService.
        user_name: Full name of the user (e.g. "Jane Doe").
        completed_at: Assessment completion timestamp.

    Returns:
        BytesIO buffer positioned at 0, ready to stream.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    styles = _build_styles()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("GPS Assessment Results", styles["title"]))
    story.append(Paragraph(user_name, styles["subtitle"]))
    if completed_at:
        date_str = completed_at.strftime("%B %d, %Y")
        story.append(Paragraph(f"Completed {date_str}", styles["subtitle"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4))

    # ── Story Section ────────────────────────────────────────────────────────
    if graded.stories:
        story.append(Paragraph("Story", styles["section_heading"]))
        for s in graded.stories:
            if s.question and s.answer:
                block = [
                    Paragraph(s.question, styles["story_question"]),
                    Paragraph(s.answer.replace("\n", "<br/>"), styles["story_answer"]),
                ]
                story.append(KeepTogether(block))

    # ── Spiritual Gifts ──────────────────────────────────────────────────────
    if graded.gifts:
        story.append(Paragraph("Your Spiritual Gifts", styles["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))
        rows = _gift_rows(graded, styles)
        if rows:
            story.append(_item_table(rows))

    # ── Passions / Influencing Styles ────────────────────────────────────────
    if graded.passions:
        story.append(Paragraph("Passions", styles["section_heading"]))
        story.append(Paragraph(
            "Your Spiritual Influencing Styles "
            "(highest score is primary &amp; lower is secondary)",
            styles["body_bold"],
        ))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))
        rows = _passion_rows(graded, styles)
        if rows:
            story.append(_item_table(rows))

    # ── Selections ───────────────────────────────────────────────────────────
    has_selections = graded.abilities or graded.people or graded.causes
    if has_selections:
        story.append(Paragraph("Your Selections", styles["section_heading"]))

        if graded.abilities:
            story.append(Paragraph("Key Abilities", styles["subsection_heading"]))
            story.append(Paragraph(", ".join(graded.abilities), styles["body"]))

        if graded.people:
            story.append(Paragraph("People You're Passionate About", styles["subsection_heading"]))
            story.append(Paragraph(", ".join(graded.people), styles["body"]))

        if graded.causes:
            story.append(Paragraph("Causes You Care About", styles["subsection_heading"]))
            story.append(Paragraph(", ".join(graded.causes), styles["body"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ── MyImpact PDF ────────────────────────────────────────────────────────────────

# Dimension labels matching the frontend
_CHARACTER_LABELS = {
    "loving": "Loving",
    "joyful": "Joyful",
    "peaceful": "Peaceful",
    "patient": "Patient",
    "kind": "Kind",
    "good": "Good",
    "faithful": "Faithful",
    "gentle": "Gentle",
    "self_controlled": "Self-Controlled",
}

_CALLING_LABELS = {
    "know_gifts": "I can name my top 3 Spiritual Gifts",
    "know_people": "I know the people/causes God wants me to serve",
    "using_gifts": "I am using my gifts to serve others",
    "see_impact": "I see God making a difference through me",
    "experience_joy": "I experience joy in serving others",
    "pray_regularly": "I regularly pray for people around me",
    "see_movement": "I see people move toward faith",
    "receive_support": "I receive support in my calling",
}


def _score_bar(score: int, width: float = 200, height: float = 10) -> Drawing:
    """Create a score bar drawing for a 1-10 score."""
    d = Drawing(width, height)
    # Background
    d.add(Rect(0, 0, width, height, fillColor=GRAY_LIGHT, strokeColor=None))
    # Filled portion
    fill_width = (score / 10) * width
    if score >= 8:
        color = TEAL
    elif score >= 5:
        color = GOLD
    else:
        color = PINK
    d.add(Rect(0, 0, fill_width, height, fillColor=color, strokeColor=None))
    return d


def _dimension_table(dimensions: dict, labels: dict, styles: dict) -> Table:
    """Build a table of dimension rows: label | bar | score."""
    rows = []
    for key, score in dimensions.items():
        if score is None:
            continue
        label = labels.get(key, key.replace("_", " ").title())
        rows.append([
            Paragraph(label, styles["gift_name"]),
            _score_bar(score),
            Paragraph(f"{score}/10", styles["score"]),
        ])
    col_widths = [2.4 * inch, 3.2 * inch, 1.0 * inch]
    tbl = Table(rows, colWidths=col_widths, repeatRows=0)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
    ]))
    return tbl


def generate_myimpact_pdf(
    result,
    user_name: str,
    completed_at: Optional[datetime] = None,
) -> BytesIO:
    """
    Generate a MyImpact assessment results PDF.

    Args:
        result: MyImpactResult model instance.
        user_name: Full name of the user.
        completed_at: Assessment completion timestamp.

    Returns:
        BytesIO buffer positioned at 0, ready to stream.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    styles = _build_styles()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("MyImpact Assessment Results", styles["title"]))
    story.append(Paragraph(user_name, styles["subtitle"]))
    if completed_at:
        date_str = completed_at.strftime("%B %d, %Y")
        story.append(Paragraph(f"Completed {date_str}", styles["subtitle"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4))

    # ── Score Summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Your MyImpact Score", styles["section_heading"]))

    char_avg = f"{result.character_score:.1f}" if result.character_score else "—"
    call_avg = f"{result.calling_score:.1f}" if result.calling_score else "—"
    impact = f"{result.myimpact_score:.1f}" if result.myimpact_score else "—"

    score_style_center = ParagraphStyle(
        "ScoreCenter", parent=styles["body"],
        fontName="Helvetica-Bold", fontSize=14,
        textColor=TEAL, alignment=TA_CENTER,
    )
    score_style_gold = ParagraphStyle(
        "ScoreGold", parent=score_style_center,
        fontSize=18, textColor=GOLD,
    )
    label_style = ParagraphStyle(
        "ScoreLabel", parent=styles["body"],
        fontName="Helvetica-Bold", fontSize=9,
        textColor=CHARCOAL, alignment=TA_CENTER,
    )
    op_style = ParagraphStyle(
        "Operator", parent=styles["body"],
        fontName="Helvetica-Bold", fontSize=16,
        textColor=CHARCOAL, alignment=TA_CENTER,
    )

    formula_row = [
        [Paragraph(char_avg, score_style_center), Paragraph("×", op_style),
         Paragraph(call_avg, score_style_center), Paragraph("=", op_style),
         Paragraph(impact, score_style_gold)],
        [Paragraph("Character", label_style), Paragraph("", label_style),
         Paragraph("Calling", label_style), Paragraph("", label_style),
         Paragraph("MyImpact", label_style)],
    ]
    formula_tbl = Table(formula_row, colWidths=[1.4 * inch, 0.5 * inch, 1.4 * inch, 0.5 * inch, 1.6 * inch])
    formula_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
    ]))
    story.append(formula_tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Most first-time takers score between 4-25. The goal is steady growth, not perfection.",
        styles["body"],
    ))

    # ── Character Section ───────────────────────────────────────────────────
    story.append(Paragraph("Character", styles["section_heading"]))
    story.append(Paragraph(
        "Fruit of the Spirit — Rate yourself as those who know you best would rate you.",
        styles["body_bold"],
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))

    char_breakdown = result.get_character_breakdown()
    story.append(_dimension_table(char_breakdown, _CHARACTER_LABELS, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Average: {char_avg}/10", styles["score"]))

    # ── Calling Section ─────────────────────────────────────────────────────
    story.append(Paragraph("Calling", styles["section_heading"]))
    story.append(Paragraph(
        "Your Unique Design — Your Calling is the unique way God has designed you to partner with Him.",
        styles["body_bold"],
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))

    call_breakdown = result.get_calling_breakdown()
    story.append(_dimension_table(call_breakdown, _CALLING_LABELS, styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Average: {call_avg}/10", styles["score"]))

    # ── Growth Opportunities ────────────────────────────────────────────────
    story.append(Paragraph("Growth Opportunities", styles["section_heading"]))
    story.append(Paragraph(
        "The goal is steady growth, not perfection. Consider focusing on your "
        "lowest-scoring areas to increase your overall impact.",
        styles["body_bold"],
    ))
    story.append(Spacer(1, 8))

    tips = [
        ("Retake Regularly", "Take this assessment every 6-12 months to track your growth over time."),
        ("Get Feedback", "Ask those closest to you how they would rate your character and calling."),
        ("Set Goals", "Focus on 1-2 dimensions at a time for sustainable growth."),
    ]
    for tip_title, tip_body in tips:
        block = [
            Paragraph(tip_title, styles["subsection_heading"]),
            Paragraph(tip_body, styles["body"]),
        ]
        story.append(KeepTogether(block))

    doc.build(story)
    buffer.seek(0)
    return buffer
