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


# ── i18n ───────────────────────────────────────────────────────────────────────
#
# Chrome strings live in this single table so the GPS + MyImpact generators
# share one source. Both locales return identical keys; lookups fall back to
# the English string when a Spanish value is missing (defensive — every key
# below has a Spanish translation, so the fallback would only fire on a typo).
#
# Sources for the Spanish entries mirror the web translations in
# web/src/i18n/translations.ts so the PDF and web results stay consistent.

_STRINGS = {
    "en": {
        # Headers
        "gps_title": "GPS Assessment Results",
        "myimpact_title": "MyImpact Assessment Results",
        "completed_prefix": "Completed",
        # Sections
        "gifts_heading": "Your Spiritual Gifts",
        "abilities_heading": "Key Abilities",
        "passions_heading": "Passions",
        "passions_subtitle": (
            "Your Spiritual Influencing Styles "
            "(highest score is primary &amp; lower is secondary)"
        ),
        "people_heading": "People You're Passionate About",
        "causes_heading": "Causes You Care About",
        "story_heading": "Story",
        # MyImpact
        "myimpact_score_heading": "Your MyImpact Score",
        "character_heading": "Character",
        "character_subtitle": (
            "Fruit of the Spirit — Rate yourself as those who know "
            "you best would rate you."
        ),
        "calling_heading": "Calling",
        "calling_subtitle": (
            "Your Unique Design — Your Calling is the unique way "
            "God has designed you to partner with Him."
        ),
        "myimpact_label": "MyImpact",
        "score_explainer": (
            "Most first-time takers score between 4-25. The goal is "
            "steady growth, not perfection."
        ),
        "average_prefix": "Average:",
        "growth_heading": "Growth Opportunities",
        "growth_intro": (
            "The goal is steady growth, not perfection. Consider focusing "
            "on your lowest-scoring areas to increase your overall impact."
        ),
        "tip_retake_title": "Retake Regularly",
        "tip_retake_body": (
            "Take this assessment every 6-12 months to track your growth over time."
        ),
        "tip_feedback_title": "Get Feedback",
        "tip_feedback_body": (
            "Ask those closest to you how they would rate your character and calling."
        ),
        "tip_goals_title": "Set Goals",
        "tip_goals_body": (
            "Focus on 1-2 dimensions at a time for sustainable growth."
        ),
        # Misc
        "score_prefix": "Score:",
        "other_prefix": "Other:",
    },
    "es": {
        "gps_title": "Resultados de la Evaluación GPS",
        "myimpact_title": "Resultados de la Evaluación MiImpacto",
        "completed_prefix": "Completada",
        "gifts_heading": "Tus Dones Espirituales",
        "abilities_heading": "Habilidades Clave",
        "passions_heading": "Pasiones",
        "passions_subtitle": (
            "Tus estilos de influencia espiritual "
            "(el puntaje más alto es el principal y el más bajo es el secundario)"
        ),
        "people_heading": "Personas que te apasionan",
        "causes_heading": "Causas que te importan",
        "story_heading": "Historia",
        "myimpact_score_heading": "Tu puntaje MiImpacto",
        "character_heading": "Carácter",
        "character_subtitle": (
            "Fruto del Espíritu — Evalúate como te evaluarían "
            "quienes mejor te conocen."
        ),
        "calling_heading": "Llamado",
        "calling_subtitle": (
            "Tu diseño único — Tu llamado es la forma única en la que "
            "Dios te ha diseñado para colaborar con Él."
        ),
        "myimpact_label": "MiImpacto",
        "score_explainer": (
            "La mayoría de quienes la toman por primera vez obtienen entre 4 "
            "y 25 puntos. El objetivo es el crecimiento constante, no la perfección."
        ),
        "average_prefix": "Promedio:",
        "growth_heading": "Oportunidades de crecimiento",
        "growth_intro": (
            "El objetivo es el crecimiento constante, no la perfección. "
            "Considera enfocarte en tus áreas con menor puntaje para "
            "aumentar tu impacto general."
        ),
        "tip_retake_title": "Vuelve a tomarla con regularidad",
        "tip_retake_body": (
            "Toma esta evaluación cada 6 a 12 meses para seguir tu "
            "crecimiento a lo largo del tiempo."
        ),
        "tip_feedback_title": "Pide retroalimentación",
        "tip_feedback_body": (
            "Pregunta a tus personas más cercanas cómo evaluarían tu "
            "carácter y tu llamado."
        ),
        "tip_goals_title": "Fija metas",
        "tip_goals_body": (
            "Enfócate en 1 o 2 dimensiones a la vez para un crecimiento sostenible."
        ),
        "score_prefix": "Puntaje:",
        "other_prefix": "Otro:",
    },
}


def _s(locale: str, key: str) -> str:
    """Look up a localized chrome string, falling back to English."""
    if locale != "en" and key in _STRINGS.get(locale, {}):
        return _STRINGS[locale][key]
    return _STRINGS["en"][key]


def _locale_of(locale: Optional[str]) -> str:
    """Normalize / safe-default a locale code to the supported set."""
    return "es" if locale == "es" else "en"


def _format_date(dt: datetime, locale: str) -> str:
    """Format a date for the PDF header. ReportLab is locale-agnostic, so
    we hand-format the Spanish month name to avoid pulling in the `babel`
    dep and to keep the output stable across Render's container locale."""
    if locale == "es":
        months_es = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"{dt.day} de {months_es[dt.month - 1]} de {dt.year}"
    return dt.strftime("%B %d, %Y")


# ── Domain-data localization (gift names, dimension labels, option pills) ─────

_CHARACTER_LABELS = {
    "en": {
        "loving": "Loving", "joyful": "Joyful", "peaceful": "Peaceful",
        "patient": "Patient", "kind": "Kind", "good": "Good",
        "faithful": "Faithful", "gentle": "Gentle",
        "self_controlled": "Self-Controlled",
    },
    "es": {
        "loving": "Amoroso", "joyful": "Alegre", "peaceful": "Pacífico",
        "patient": "Paciente", "kind": "Amable", "good": "Bondadoso",
        "faithful": "Fiel", "gentle": "Manso",
        "self_controlled": "Con dominio propio",
    },
}

_CALLING_LABELS = {
    "en": {
        "know_gifts": "I can name my top 3 Spiritual Gifts",
        "know_people": "I know the people/causes God wants me to serve",
        "using_gifts": "I am using my gifts to serve others",
        "see_impact": "I see God making a difference through me",
        "experience_joy": "I experience joy in serving others",
        "pray_regularly": "I regularly pray for people around me",
        "see_movement": "I see people move toward faith",
        "receive_support": "I receive support in my calling",
    },
    "es": {
        "know_gifts": "Puedo nombrar mis 3 dones espirituales principales",
        "know_people": "Sé a qué personas y causas Dios quiere que sirva",
        "using_gifts": "Estoy usando mis dones para servir a otros",
        "see_impact": "Veo a Dios marcando la diferencia a través de mí",
        "experience_joy": "Experimento alegría al servir a los demás",
        "pray_regularly": "Oro regularmente por las personas que me rodean",
        "see_movement": "Veo a personas avanzar hacia la fe",
        "receive_support": "Recibo apoyo en mi llamado",
    },
}

# English -> Spanish for the user-selected People/Causes/Abilities pills.
# Mirrors web/src/data/assessmentOptions.ts OPTION_LABEL_ES. Single map works
# across all three categories because the few cross-category collisions
# ("Financial Management") share the same Spanish.
_OPTION_LABEL_ES = {
    # People
    "Infants/Babies": "Bebés/Infantes",
    "Toddlers": "Niños pequeños",
    "Preschool Children": "Niños en edad preescolar",
    "Elementary Children": "Niños de primaria",
    "Jr. High Students": "Estudiantes de secundaria",
    "High School": "Estudiantes de preparatoria",
    "College/Career": "Universitarios/Profesionales",
    "Women": "Mujeres",
    "Men": "Hombres",
    "Singles": "Solteros",
    "Single Parents": "Padres/madres solteros",
    "Young Marrieds": "Recién casados",
    "Couples": "Parejas",
    "Families": "Familias",
    "Older Adults 60+": "Adultos mayores (60+)",
    # Causes
    "Families/Marriage": "Familias/Matrimonio",
    "At-Risk Children": "Niños en riesgo",
    "Abuse/Violence": "Abuso/Violencia",
    "Financial Management": "Manejo financiero",
    "Divorce Recovery": "Recuperación del divorcio",
    "Disabilities and/or Support": "Discapacidad y/o apoyo",
    "Law and/or Justice System": "Sistema legal y/o judicial",
    "Sanctity of Life": "Santidad de la vida",
    "Homelessness": "Personas sin hogar",
    "Recovery": "Recuperación",
    "Working with prison inmates/families": "Trabajo con personas en prisión y sus familias",
    "Illness and/or Injury": "Enfermedad y/o lesiones",
    "Sexuality and/or Gender Issues": "Asuntos de sexualidad y/o género",
    "Education": "Educación",
    "Policy and/or Politics": "Política y/o políticas públicas",
    "Race": "Raza",
    "Business and the Economy": "Negocios y economía",
    "Relief Efforts": "Esfuerzos de ayuda humanitaria",
    "Ethics": "Ética",
    "Health and/or Fitness": "Salud y/o estado físico",
    "Science and/or Technology": "Ciencia y/o tecnología",
    "Environment": "Medio ambiente",
    "International and Global Affairs": "Asuntos internacionales y globales",
    "Regional/State/Federal Issues": "Asuntos regionales/estatales/federales",
    "Community/Neighborhood Issues": "Asuntos comunitarios/vecinales",
    # Abilities
    "Project Management": "Gestión de proyectos",
    "Marketing": "Mercadotecnia",
    "Web Development": "Desarrollo web",
    "Music: Vocal": "Música: Vocal",
    "Writing": "Escritura",
    "Coaching": "Coaching",
    "Plumbing": "Plomería",
    "Electrical": "Electricidad",
    "Information Technology": "Tecnología de la información",
    "Community Relations": "Relaciones comunitarias",
    "Graphic Arts": "Artes gráficas",
    "Music: Instrumental": "Música: Instrumental",
    "Training": "Capacitación",
    "Cooking": "Cocina",
    "Landscaping/Gardening": "Paisajismo/Jardinería",
    "Communications": "Comunicaciones",
    "Social Media": "Redes sociales",
    "Creative Arts": "Artes creativas",
    "Audio Visual": "Audiovisual",
    "Counseling": "Consejería",
    "Sports Mechanical": "Deportes/Mecánica",
    "Carpentry/Construction": "Carpintería/Construcción",
}


def _option_label(value: str, locale: str) -> str:
    """Mirror of web/src/data/assessmentOptions.ts optionLabel(). Custom
    "Other: <user text>" entries get the prefix localized but keep the
    user's free text untouched."""
    if locale != "es":
        return value
    if value.startswith("Other: "):
        return _s(locale, "other_prefix") + " " + value[len("Other: "):]
    return _OPTION_LABEL_ES.get(value, value)


def _gift_name(gift, locale: str) -> str:
    return (gift.name_es or gift.name) if locale == "es" else gift.name


def _gift_desc(gift, locale: str) -> str:
    return (gift.description_es or gift.description or "") if locale == "es" else (gift.description or "")


def _story_question(story, locale: str) -> str:
    return (story.question_es or story.question) if locale == "es" else story.question


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


def _gift_rows(graded: GradedAssessment, styles: dict, locale: str) -> list:
    """Build table rows for the gifts section. Top 3-4 only (with ties)."""
    rows = []
    score_label = _s(locale, "score_prefix")
    for gift in graded.top_gifts:
        name_para = Paragraph(_gift_name(gift, locale), styles["gift_name"])
        desc_para = Paragraph(_gift_desc(gift, locale), styles["body"])
        score_para = Paragraph(f"{score_label} {gift.points}", styles["score"])
        rows.append([name_para, desc_para, score_para])
    return rows


def _passion_rows(graded: GradedAssessment, styles: dict, locale: str) -> list:
    """Build table rows for the passions section. Top 2 only — matches the
    legacy GPS layout (Sherri 2026-05-05)."""
    rows = []
    score_label = _s(locale, "score_prefix")
    for passion in graded.top_passions[:2]:
        name_para = Paragraph(_gift_name(passion, locale), styles["gift_name"])
        desc_para = Paragraph(_gift_desc(passion, locale), styles["body"])
        score_para = Paragraph(f"{score_label} {passion.points}", styles["score"])
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
    locale: str = "en",
) -> BytesIO:
    """
    Generate a GPS assessment results PDF.

    Args:
        graded: Scored GradedAssessment from ScoringService.
        user_name: Full name of the user (e.g. "Jane Doe").
        completed_at: Assessment completion timestamp.
        locale: "en" or "es". Unknown values fall back to English.

    Returns:
        BytesIO buffer positioned at 0, ready to stream.
    """
    locale = _locale_of(locale)
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
    story.append(Paragraph(_s(locale, "gps_title"), styles["title"]))
    story.append(Paragraph(user_name, styles["subtitle"]))
    if completed_at:
        date_str = _format_date(completed_at, locale)
        story.append(Paragraph(f"{_s(locale, 'completed_prefix')} {date_str}", styles["subtitle"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4))

    # Section order matches the web results page (Sherri 2026-05-05):
    # Gifts → Passions → Story. Key Abilities folded under Gifts; People +
    # Causes folded under Passions. Story is the closing section.

    # ── Spiritual Gifts ──────────────────────────────────────────────────────
    if graded.top_gifts:
        story.append(Paragraph(_s(locale, "gifts_heading"), styles["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))
        rows = _gift_rows(graded, styles, locale)
        if rows:
            story.append(_item_table(rows))

        if graded.abilities:
            story.append(Paragraph(_s(locale, "abilities_heading"), styles["subsection_heading"]))
            story.append(Paragraph(
                ", ".join(_option_label(a, locale) for a in graded.abilities),
                styles["body"],
            ))

    # ── Passions / Influencing Styles ────────────────────────────────────────
    if graded.top_passions:
        story.append(Paragraph(_s(locale, "passions_heading"), styles["section_heading"]))
        story.append(Paragraph(_s(locale, "passions_subtitle"), styles["body_bold"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))
        rows = _passion_rows(graded, styles, locale)
        if rows:
            story.append(_item_table(rows))

        if graded.people:
            story.append(Paragraph(_s(locale, "people_heading"), styles["subsection_heading"]))
            story.append(Paragraph(
                ", ".join(_option_label(p, locale) for p in graded.people),
                styles["body"],
            ))

        if graded.causes:
            story.append(Paragraph(_s(locale, "causes_heading"), styles["subsection_heading"]))
            story.append(Paragraph(
                ", ".join(_option_label(c, locale) for c in graded.causes),
                styles["body"],
            ))

    # ── Story Section (closes the document) ─────────────────────────────────
    if graded.stories:
        story.append(Paragraph(_s(locale, "story_heading"), styles["section_heading"]))
        for s in graded.stories:
            if s.question and s.answer:
                block = [
                    Paragraph(_story_question(s, locale), styles["story_question"]),
                    Paragraph(s.answer.replace("\n", "<br/>"), styles["story_answer"]),
                ]
                story.append(KeepTogether(block))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ── MyImpact PDF ────────────────────────────────────────────────────────────────


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


def _dimension_table(dimensions: dict, labels: dict, styles: dict, locale: str) -> Table:
    """Build a table of dimension rows: label | bar | score."""
    rows = []
    locale_labels = labels.get(locale, labels["en"])
    for key, score in dimensions.items():
        if score is None:
            continue
        label = locale_labels.get(key, key.replace("_", " ").title())
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
    locale: str = "en",
) -> BytesIO:
    """
    Generate a MyImpact assessment results PDF.

    Args:
        result: MyImpactResult model instance.
        user_name: Full name of the user.
        completed_at: Assessment completion timestamp.
        locale: "en" or "es". Unknown values fall back to English.

    Returns:
        BytesIO buffer positioned at 0, ready to stream.
    """
    locale = _locale_of(locale)
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
    story.append(Paragraph(_s(locale, "myimpact_title"), styles["title"]))
    story.append(Paragraph(user_name, styles["subtitle"]))
    if completed_at:
        date_str = _format_date(completed_at, locale)
        story.append(Paragraph(f"{_s(locale, 'completed_prefix')} {date_str}", styles["subtitle"]))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=4))

    # ── Score Summary ───────────────────────────────────────────────────────
    story.append(Paragraph(_s(locale, "myimpact_score_heading"), styles["section_heading"]))

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
        [Paragraph(_s(locale, "character_heading"), label_style), Paragraph("", label_style),
         Paragraph(_s(locale, "calling_heading"), label_style), Paragraph("", label_style),
         Paragraph(_s(locale, "myimpact_label"), label_style)],
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
    story.append(Paragraph(_s(locale, "score_explainer"), styles["body"]))

    # ── Character Section ───────────────────────────────────────────────────
    story.append(Paragraph(_s(locale, "character_heading"), styles["section_heading"]))
    story.append(Paragraph(_s(locale, "character_subtitle"), styles["body_bold"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))

    char_breakdown = result.get_character_breakdown()
    story.append(_dimension_table(char_breakdown, _CHARACTER_LABELS, styles, locale))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{_s(locale, 'average_prefix')} {char_avg}/10", styles["score"]))

    # ── Calling Section ─────────────────────────────────────────────────────
    story.append(Paragraph(_s(locale, "calling_heading"), styles["section_heading"]))
    story.append(Paragraph(_s(locale, "calling_subtitle"), styles["body_bold"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT, spaceAfter=0))

    call_breakdown = result.get_calling_breakdown()
    story.append(_dimension_table(call_breakdown, _CALLING_LABELS, styles, locale))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{_s(locale, 'average_prefix')} {call_avg}/10", styles["score"]))

    # ── Growth Opportunities ────────────────────────────────────────────────
    story.append(Paragraph(_s(locale, "growth_heading"), styles["section_heading"]))
    story.append(Paragraph(_s(locale, "growth_intro"), styles["body_bold"]))
    story.append(Spacer(1, 8))

    tips = [
        (_s(locale, "tip_retake_title"), _s(locale, "tip_retake_body")),
        (_s(locale, "tip_feedback_title"), _s(locale, "tip_feedback_body")),
        (_s(locale, "tip_goals_title"), _s(locale, "tip_goals_body")),
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
