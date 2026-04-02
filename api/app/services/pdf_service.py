"""
PDF generation service for GPS assessment results.
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

from app.services.scoring_service import GradedAssessment

# Brand colours
TEAL = HexColor("#4CABB0")
CHARCOAL = HexColor("#3A3A3A")
GRAY_LIGHT = HexColor("#E5E5E5")
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
