#!/usr/bin/env python3
"""Build the English M1 group-meeting report from saved local evidence.

No network requests are made. M1.1 files are read but never modified.
"""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
OUTPUT = ROOT / "meeting_report.pdf"
CHECKS_PATH = PROJECT / "work_packages/M1_source_access/01_feasibility/checks.json"

INK = colors.HexColor("#18241F")
MUTED = colors.HexColor("#63706A")
PAPER = colors.HexColor("#FFFDF8")
LINE = colors.HexColor("#D9D5CA")
GOV = colors.HexColor("#6D3A8E")
GOV_SOFT = colors.HexColor("#EDE3F2")
MEDIA = colors.HexColor("#2F6FBD")
MEDIA_SOFT = colors.HexColor("#E1ECF8")
PUBLIC = colors.HexColor("#2E8B57")
PUBLIC_SOFT = colors.HexColor("#DFF1E7")
AMBER = colors.HexColor("#A56113")
AMBER_SOFT = colors.HexColor("#FFF0D8")
RED = colors.HexColor("#934B4B")
RED_SOFT = colors.HexColor("#F7E5E5")
WHITE = colors.white

styles = getSampleStyleSheet()
TITLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=25, leading=31, textColor=INK, spaceAfter=10)
COVER_SUB = ParagraphStyle("CoverSub", fontName="Helvetica-Bold", fontSize=18, leading=23, textColor=GOV, spaceAfter=8)
SUBTITLE = ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=11.5, leading=16, textColor=MUTED, spaceAfter=9)
KICKER = ParagraphStyle("Kicker", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=GOV, tracking=1.1, spaceAfter=6)
H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceAfter=10)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=4, spaceAfter=4)
BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=8.7, leading=12.5, textColor=INK, spaceAfter=5)
BODY_TIGHT = ParagraphStyle("BodyTight", parent=BODY, fontSize=8.0, leading=10.9, spaceAfter=2)
SMALL = ParagraphStyle("Small", fontName="Helvetica", fontSize=6.9, leading=9.2, textColor=MUTED, spaceAfter=2)
SMALL_BOLD = ParagraphStyle("SmallBold", parent=SMALL, fontName="Helvetica-Bold", textColor=INK)
CALLOUT = ParagraphStyle("Callout", parent=BODY, fontSize=9.0, leading=13.1)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", BODY_TIGHT)


def card(content, *, background=PAPER, border=LINE, padding=8) -> Table:
    if not isinstance(content, list):
        content = [[content]]
    table = Table(content, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return table


def vertical_card(items, width, *, background=PAPER, border=LINE, padding=8) -> Table:
    table = Table([[item] for item in items], colWidths=[width], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (0, 0), padding),
        ("BOTTOMPADDING", (0, -1), (0, -1), padding),
    ]))
    return table


def formatted_table(data, widths, *, font_size=7.2, leading=9.7) -> Table:
    cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=font_size, leading=leading, textColor=INK)
    head = ParagraphStyle("Head", parent=cell, fontName="Helvetica-Bold", textColor=colors.HexColor("#47554F"))
    rows = [[p(str(v), head if r == 0 else cell) for v in row] for r, row in enumerate(data)]
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.55, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1EE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    for row_index in range(2, len(rows), 2):
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#FBFAF5")))
    table.setStyle(TableStyle(commands))
    return table


class PipelineDiagram(Flowable):
    def __init__(self, width=500, height=214):
        super().__init__(); self.width = width; self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def arrow(self, c, x1, y1, x2, y2):
        c.setStrokeColor(colors.HexColor("#53635C")); c.setLineWidth(1.3); c.line(x1, y1, x2, y2)
        c.line(x2-4, y2+2.5, x2, y2); c.line(x2-4, y2-2.5, x2, y2)

    def box(self, c, x, y, w, h, title, lines, *, border=LINE, dashed=False, fill=WHITE):
        c.setFillColor(fill); c.setStrokeColor(border); c.setLineWidth(1.1)
        if dashed: c.setDash(4, 3)
        c.roundRect(x, y, w, h, 6, stroke=1, fill=1); c.setDash()
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 7.4); c.drawCentredString(x+w/2, y+h-13, title)
        c.setFillColor(MUTED); c.setFont("Helvetica", 5.8)
        for idx, line in enumerate(lines): c.drawCentredString(x+w/2, y+h-25-idx*9, line)

    def draw(self):
        c = self.canv
        c.setFillColor(PAPER); c.roundRect(0, 0, self.width, self.height, 9, fill=1, stroke=0)
        c.setFillColor(MUTED); c.setFont("Helvetica", 6.4); c.drawString(10, self.height-13, "Design diagram: dashed stages are planned; only M1.1 source feasibility is completed")
        for label, colour, y in [("POLICY", GOV, 142), ("MEDIA", MEDIA, 116), ("PUBLIC", PUBLIC, 90)]:
            c.setFillColor(colour); c.roundRect(10, y, 48, 18, 4, fill=1, stroke=0); c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 6.4); c.drawCentredString(34, y+6, label)
        self.arrow(c, 60, 126, 80, 126)
        self.box(c, 82, 89, 82, 73, "SOURCE + DENOMINATOR", ["type · dates · rights", "eligible N"], border=GOV)
        c.setFillColor(GOV_SOFT); c.roundRect(98, 96, 50, 11, 4, fill=1, stroke=0); c.setFillColor(GOV); c.setFont("Helvetica-Bold", 5.2); c.drawCentredString(123, 100, "M1.1 COMPLETE")
        self.arrow(c, 166, 126, 184, 126)
        self.box(c, 186, 89, 78, 73, "DATABASE + CLEAN", ["metadata · dedupe", "passages · versions"], dashed=True)
        self.arrow(c, 266, 126, 284, 126)
        self.box(c, 286, 89, 82, 73, "ENCODE + RETRIEVE", ["Transformer candidate", "lexical baseline"], dashed=True)
        self.arrow(c, 370, 126, 388, 126)
        self.box(c, 390, 89, 100, 73, "THREE NLP TASKS", ["emotion · relations", "topics · frames"], dashed=True)
        self.box(c, 286, 31, 82, 42, "VALIDATE + AGGREGATE", ["holdout · S/E/B"], dashed=True)
        c.setStrokeColor(colors.HexColor("#53635C")); c.line(440,89,440,79); c.line(440,79,327,79); self.arrow(c,327,79,327,73)
        self.box(c, 111, 27, 153, 51, "RQ1 · RQ2 · RQ3", ["timing · events · meaning", "return to original text"], border=colors.HexColor("#53635C"), fill=colors.HexColor("#EEF3F0"))
        self.arrow(c, 284, 52, 266, 52)
        c.setFillColor(INK); c.roundRect(10, 4, 480, 17, 4, fill=1, stroke=0); c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 5.5)
        c.drawString(16, 10, "Evidence spine: document → passage → date/source → speaker/holder → span → model version → aggregate → interpretation")


class VerificationChart(Flowable):
    def __init__(self, width=500, height=196):
        super().__init__(); self.width = width; self.height = height

    def wrap(self, avail_width, avail_height): return min(self.width, avail_width), self.height

    def draw(self):
        c = self.canv; c.setFillColor(PAPER); c.roundRect(0, 0, self.width, self.height, 9, fill=1, stroke=0)
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 8); c.drawString(12, 180, "Actual access chain: each full bar is 9/9")
        labels = ["Search API total", "Search API returned", "Content API", "Canonical HTML"]
        for i, label in enumerate(labels):
            y = 148 - i*27; c.setFillColor(INK); c.setFont("Helvetica", 6.8); c.drawString(12, y+4, label)
            c.setFillColor(colors.HexColor("#E7E2EA")); c.roundRect(112, y, 250, 13, 6, fill=1, stroke=0)
            c.setFillColor(GOV); c.roundRect(112, y, 250, 13, 6, fill=1, stroke=0); c.setFont("Helvetica-Bold", 7); c.drawString(370, y+3, "9")
        c.setFillColor(INK); c.setFont("Helvetica", 6.8); c.drawString(12, 35, "Pagination")
        c.setFillColor(colors.HexColor("#8D5CA6")); c.roundRect(112, 31, 139, 15, 7, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#C3A8D1")); c.roundRect(251, 31, 111, 15, 7, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 6); c.drawCentredString(181, 36, "page 1: 5"); c.drawCentredString(306, 36, "page 2: 4")
        c.setFillColor(GOV); c.setFont("Helvetica-Bold", 7); c.drawString(370, 35, "5 + 4 = 9")
        stats = [("0", "missing", colors.HexColor("#EEF3F0")), ("0", "duplicates", colors.HexColor("#EEF3F0")), ("3", "multi-org", AMBER_SOFT), ("0", "bodies", RED_SOFT)]
        for idx, (value, label, fill) in enumerate(stats):
            x = 405 + (idx%2)*45; y = 103 - (idx//2)*61; c.setFillColor(fill); c.setStrokeColor(LINE); c.roundRect(x, y, 40, 47, 5, fill=1, stroke=1)
            c.setFillColor(INK); c.setFont("Helvetica-Bold", 13); c.drawCentredString(x+20, y+27, value); c.setFont("Helvetica", 5.2); c.drawCentredString(x+20, y+9, label)
        c.setFillColor(INK); c.roundRect(10, 4, 480, 17, 4, fill=1, stroke=0); c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 5.5)
        c.drawString(16, 10, "Status 1 / conditional go: bounded document denominator only; N_total = 9")


def on_page(canvas: Canvas, doc) -> None:
    canvas.saveState(); canvas.setFillColor(PAPER); canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    if doc.page == 1:
        canvas.setFillColor(GOV_SOFT); canvas.rect(A4[0]-58*mm, 0, 58*mm, A4[1], fill=1, stroke=0)
        canvas.setFillColor(colors.Color(GOV.red, GOV.green, GOV.blue, alpha=0.08)); canvas.setFont("Helvetica-Bold", 82); canvas.drawRightString(A4[0]-12*mm, A4[1]-35*mm, "M1")
    else:
        canvas.setStrokeColor(LINE); canvas.line(16*mm, A4[1]-15*mm, A4[0]-16*mm, A4[1]-15*mm)
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 6.8); canvas.drawString(16*mm, A4[1]-11*mm, "FEAR OF TEMPERATURE · M1 GROUP-MEETING REPORT")
    canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 6.6); canvas.drawString(16*mm, 9*mm, "Dai Pan · 16 Sep 2026 · based on saved proposal and M1.1 evidence")
    canvas.drawRightString(A4[0]-16*mm, 9*mm, f"{doc.page:02d} / 07"); canvas.restoreState()


def build_story(checks: dict) -> list:
    total = checks["selected_query"]["reported_total"]
    returned = checks["selected_query"]["returned_count"]
    multi = checks["record_checks"]["co_published_or_multi_org_count"]
    body_count = checks["content_collection"]["body_persisted_count"]
    assert (total, returned, multi, body_count) == (9, 9, 3, 0)
    story = []

    # Page 1: cover + one-minute summary
    story += [Spacer(1, 12*mm), p("GROUP MEETING · 16 SEPTEMBER 2026", KICKER), p("Fear of Temperature", TITLE), p("Research direction and initial source-feasibility progress", COVER_SUB), p("Computational analysis of policy, media and public climate emotions", SUBTITLE)]
    role = ParagraphStyle("Role", parent=BODY, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_CENTER)
    role_table = Table([[p("Government / policy", role), p("News media", role), p("Public expression", role)]], colWidths=[52*mm]*3)
    role_table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),GOV),("BACKGROUND",(1,0),(1,0),MEDIA),("BACKGROUND",(2,0),(2,0),PUBLIC),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story += [role_table, Spacer(1, 5*mm)]
    chips = Table([[p("COMPLETED · bounded M1.1 audit", SMALL_BOLD), p("PLANNED · NLP + temporal analysis", SMALL_BOLD), p("DECISION · counting / text / rights", SMALL_BOLD)]], colWidths=[52*mm]*3)
    chips.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),PUBLIC_SOFT),("BACKGROUND",(1,0),(1,0),MEDIA_SOFT),("BACKGROUND",(2,0),(2,0),AMBER_SOFT),("BOX",(0,0),(-1,-1),0.5,LINE),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [chips, Spacer(1, 6*mm), card([[p("One-minute overview", H2), p("The topic has not changed: how policy, media and public communication express fear of rising temperatures, who changes first, what changes around events and how responsibility is explained. The method moves from keyword/Ngram exploration towards a traceable corpus, validated semantic retrieval and bounded temporal analysis. Lexical and TF-IDF methods remain baselines; 1988 is an IPCC-related collection anchor, not an emotional origin.", CALLOUT), p(f"<b>Completed this week:</b> nine July 2026 GOV.UK policy_paper records tagged to DEFRA. Reported/returned: {total}/{returned}; pagination: 5 + 4; accessible API records and pages: 9/9; missing and duplicate key fields: 0. This supports one bounded document denominator only. Retained bodies: 0; no emotion or temporal result exists.", CALLOUT)]], background=colors.HexColor("#F7F2F9"), border=GOV, padding=11), Spacer(1, 5*mm), p("Dai Pan · Supervisor: Mashhuda Glencross · progress report, not a completed model study", SMALL), PageBreak()]

    # Page 2: transition
    story += [p("RESEARCH TRANSITION", KICKER), p("The research question is unchanged; the evidence strategy is changing", H1)]
    transition = [["Earlier exploration","Current design","Reason"],["Dictionaries, keywords, Ngrams","Traceable corpus + semantic retrieval","Similar concerns use different language; the same word can be quotation, denial or unrelated text"],["Raw hit counts","S, E and derived B with aligned denominators","A hit count is not attention unless numerator and denominator share the eligible collection"],["Selected examples","Versioned queries, held-out validation, evidence spans","Reduces discretionary selection and preserves counterexamples"],["General negative sentiment","Emotion, target, horizon, holder, cause, blame and duty","Similarity is not intensity; a risk statement need not express fear"]]
    story += [formatted_table(transition,[37*mm,51*mm,74*mm],font_size=7.0,leading=9.4),Spacer(1,5*mm)]
    two = Table([[card([[p("Baseline retained",H2),p("Dictionary and TF-IDF methods remain. A Transformer only counts as an improvement if held-out precision, recall, F1 and error analysis support it.",BODY_TIGHT)]],background=PUBLIC_SOFT,border=PUBLIC),card([[p("1988 boundary",H2),p("The IPCC provides an institutional collection anchor, not the origin of fear or a demonstrated breakpoint. The final comparison window depends on reliable overlap.",BODY_TIGHT)]],background=GOV_SOFT,border=GOV)]],colWidths=[80*mm,80*mm]); two.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4)]))
    story += [two,Spacer(1,5*mm),card([[p("Historical span is not comparable coverage",H2),p("Letters, early forums and modern platforms will not be merged into a seamless public-emotion series. Channel changes can flag composition risk but cannot prove bias by themselves.",BODY_TIGHT)]],background=AMBER_SOFT,border=AMBER),Spacer(1,4*mm),p("The scholarly question remains social: the corpus and code make the evidence reproducible; they are not the substantive contribution by themselves.",BODY),PageBreak()]

    # Page 3: workflow
    story += [p("END-TO-END EVIDENCE CHAIN",KICKER),p("Original evidence remains linked throughout the planned workflow",H1),PipelineDiagram(width=164*mm,height=70*mm),Spacer(1,4*mm)]
    measurement = [[p("Measures",H2),p("<b>S</b>: relevant share of eligible units<br/><b>E</b>: future fear/worry within relevant text<br/><b>B = S x E</b>: derived joint share",BODY_TIGHT)],[p("Model boundary",H2),p("Sentence-BERT is a retrieval candidate; GoEmotions is a dataset; spaCy/Stanza is not a complete responsibility system.",BODY_TIGHT)],[p("Evidence boundary",H2),p("Publishing institution, quoted speaker and emotion holder remain separate. Evidence spans, negation, versions and counterexamples are retained.",BODY_TIGHT)]]
    mt = Table(measurement,colWidths=[32*mm,132*mm]); mt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.55,LINE),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#EEF1EE")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [mt,Spacer(1,4*mm),p("Planned, not completed: exact checkpoints are not frozen; shared representation does not imply joint training or algorithmic novelty. Aggregation follows source/period validation.",SMALL),PageBreak()]

    # Page 4: RQs
    story += [p("RESEARCH QUESTIONS",KICKER),p("Three RQs connect timing, events and meaning",H1)]
    rq = [["RQ","Question","Planned evidence and method","Boundary"],["RQ1\nWho changes first?","Leading, lagging, synchronous and feedback patterns across roles","Common-window S/E; CCF; conditional VAR against own-history baseline","Precedence and added prediction are not automatic causation"],["RQ2\nWhat changes around events?","Level and slope near independent heat, science or policy dates","Segmented regression / ITS; windows; placebo dates; serial-dependence checks","Change may reflect anticipation, common shocks, composition or channel shifts"],["RQ3\nHow is fear explained?","Affected groups, causes, blame, duties and threatened futures","Evidence-linked relations; topics/frames; quotation and stance; contrary text","Grammar is not culpability; similarity is not agreement or intensity"]]
    story += [formatted_table(rq,[25*mm,45*mm,55*mm,39*mm],font_size=7.0,leading=9.7),Spacer(1,6*mm),card([[p("Why all three?",H2),p("RQ1 without RQ3 gives curves without meaning; RQ3 alone cannot compare sequence; RQ2 links independently dated events to changes. NLP components serve multiple RQs rather than mapping one model to one question.",BODY)]],background=GOV_SOFT,border=GOV,padding=10),Spacer(1,5*mm),card([[p("Shared causal boundary",H2),p("CCF/Granger/VAR added prediction is not causal identification. A non-significant result would not prove policy dominance or the absence of physical influence. Channel-transition diagnostics only flag composition risk.",BODY)]],background=RED_SOFT,border=RED,padding=10),PageBreak()]

    # Page 5: completed pilot
    story += [p("COMPLETED THIS WEEK",KICKER),p("M1.1 verified one bounded policy-document denominator",H1),VerificationChart(width=164*mm,height=64*mm),Spacer(1,4*mm)]
    samples = [["First published","Real title","Why it matters"],["3 Jul 2026",'<link href="https://www.gov.uk/government/publications/air-pollution-awareness-coalition-apac">Air Pollution Awareness Coalition (APAC)</link>',"Updated 21 Aug; DEFRA, DHSC and DfT. Publication and update dates differ."],["13 Jul 2026",'<link href="https://www.gov.uk/government/publications/30by30-on-land-in-england-delivery-plan">30by30 on land in England: Delivery plan</link>',"policy_paper; linked to DEFRA."],["15 Jul 2026",'<link href="https://www.gov.uk/government/publications/british-sign-language-5-year-plan-department-for-environment-food-and-rural-affairs-1-year-update-july-2026">British Sign Language 5-year plan: Department for Environment, Food and Rural Affairs - 1-year update, July 2026</link>',"Non-climate record: denominator was not built from climate keyword hits."]]
    story += [formatted_table(samples,[27*mm,80*mm,57*mm],font_size=6.9,leading=9.4),Spacer(1,4*mm),card([[p("Decision: status 1, conditional go",H2),p("N_total = 9 is complete only for this saved index time, organisation tag, document type and month. It is not all DEFRA output, all UK policy, a passage denominator or proof of complete 1988-2026 coverage.",BODY_TIGHT)]],background=PUBLIC_SOFT,border=PUBLIC,padding=8),PageBreak()]

    # Page 6: findings and limits
    story += [p("TECHNICAL FINDINGS AND LIMITS",KICKER),p("What the pilot established - and what remains unclaimed",H1)]
    findings = Table([[vertical_card([p("Completed and confirmed",H2),bullet("first_published_at worked as a filter, but was not populated in the search response; sorting returned HTTP 422."),bullet("The Content API supplied dates for verification and local sorting."),bullet("3/9 records had multiple organisations; the pilot counted each landing page once if DEFRA-tagged."),bullet("Access time and evidence hashes were saved.")],76*mm,background=PUBLIC_SOFT,border=PUBLIC),vertical_card([p("Technical implications",H2),bullet("public_timestamp can reflect an update and cannot substitute for first publication."),bullet("An organisation tag is not exclusive authorship; cross-institution totals may double count."),bullet("The index is a dynamic snapshot."),bullet("One complete month does not prove 1988-2026 completeness.")],76*mm,background=GOV_SOFT,border=GOV)]],colWidths=[80*mm,80*mm]); findings.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4)]))
    story += [findings,Spacer(1,5*mm),card([[p("Not completed",H2),p("Body/attachment retention, passage denominator, relevance/emotion labels, embeddings, topics, relations, S/E/B, CCF, VAR and ITS. Retained bodies and paragraph examples: 0.",BODY)]],background=RED_SOFT,border=RED),Spacer(1,4*mm),card([[p("Rights and ethics",H2),p("Most GOV.UK material is under OGL v3, but attachment, third-party and personal-data exceptions remain. Public visibility is not blanket permission to store or redistribute content.",BODY)]],background=AMBER_SOFT,border=AMBER),Spacer(1,4*mm),p("<b>The pilot cannot establish:</b> climate prevalence, fear level or trend, policy leadership, whole-government representativeness or complete historical coverage.",BODY),PageBreak()]

    # Page 7: next week
    story += [p("NEXT WEEK AND DECISIONS",KICKER),p("21-27 September: 10-20 hours, strengthen measurement before expansion",H1)]
    plan = [["Time","Work","Output / stop condition"],["3-5 h","Preserve snapshot; audit recent, intermediate and earlier windows","Versioned coverage table; do not overwrite M1.1; downgrade status if fields are unstable"],["2-3 h","Review three multi-organisation records and date/unit rules","Data dictionary and counting recommendation; no cross-institution total before decision"],["2-4 h","If authorised, test provenance on three public documents","Traceable passage sample; otherwise metadata or labelled synthetic checks only"],["3-5 h","Two close readings + two targeted readings","Query and annotation drafts; readings are planned, not completed"],["0-3 h","Synthesis and demonstration","Next meeting material; total stays within 20 h"]]
    story += [formatted_table(plan,[24*mm,64*mm,76*mm],font_size=6.9,leading=9.4),Spacer(1,4*mm)]
    rd = Table([[vertical_card([p("Planned reading",H2),p("<b>Close:</b> Sentence-BERT; Pihkala climate-emotion taxonomy.<br/><b>Targeted:</b> GoEmotions transfer limits; Brulle et al. temporal design.",BODY_TIGHT)],65*mm,background=colors.HexColor("#FBFAF5")),vertical_card([p("Supervisor decisions requested",H2),bullet("1988 anchor with final analysis restricted to common coverage?"),bullet("Joint records: all linked, lead-only or fractional weights?"),bullet("What supervision, ethics and rights record is needed before a three-document passage pilot?"),bullet("Prioritise coverage audit or freeze units/counting first?")],87*mm,background=GOV_SOFT,border=GOV)]],colWidths=[69*mm,91*mm]); rd.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),4)]))
    story += [rd,Spacer(1,4*mm),card([[p("Closing principle",H2),p("Make the denominator, evidence location and validation chain defensible before running complex models. Next week does not commit to completing emotion models or VAR.",BODY)]],background=colors.HexColor("#F7F2F9"),border=GOV),Spacer(1,3*mm),p("Evidence base: meeting_report_en.md; latest proposal; research narrative; saved M1.1 README, CSV, denominator assessment and checks.json. This report did not rerun collection.",SMALL)]
    return story


def main() -> None:
    checks = json.loads(CHECKS_PATH.read_text(encoding="utf-8"))
    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=20*mm, bottomMargin=15*mm, title="Fear of Temperature: research direction and initial source-feasibility progress", author="Dai Pan", subject="M1 group-meeting report")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="report", frames=frame, onPage=on_page))
    doc.build(build_story(checks))
    reader = PdfReader(str(OUTPUT))
    if len(reader.pages) != 7: raise RuntimeError(f"Expected 7 pages, generated {len(reader.pages)}")
    for idx, page in enumerate(reader.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if abs(width-A4[0]) > 1 or abs(height-A4[1]) > 1: raise RuntimeError(f"Page {idx} is not A4: {width} x {height}")
    print(f"created {OUTPUT} ({len(reader.pages)} A4 pages)")


if __name__ == "__main__":
    main()
