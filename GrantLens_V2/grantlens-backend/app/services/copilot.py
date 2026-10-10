"""Investigation Copilot service: deterministic evidence-linked question templates and ReportLab PDF generator."""
import io
from datetime import datetime, timezone
from uuid import uuid4
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        # Top banner on pages > 1
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, 755, 572, 755)
            self.drawString(40, 760, "SATARKK Investigation Copilot — Forensic Investigation Report")
        # Footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 45, 572, 45)
        self.drawString(40, 32, "CONFIDENTIAL — FOR OFFICIAL AUDITOR USE ONLY · PROTOTYPE SYNTHETIC AUDIT DATA")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 32, page_str)
        self.restoreState()


def generate_questions_for_case(case: dict) -> list[dict]:
    """Generates relevant questions using a deterministic rule-based template library based on real case evidence."""
    evidence_list = case.get("evidence", []) or []
    cluster_id = case.get("case_id") or case.get("cluster_id") or "CASE"
    beneficiaries = case.get("beneficiary_ids", []) or []
    schemes = case.get("schemes", []) or [case.get("scheme", "")]
    schemes = [s for s in schemes if s]

    indicators = {e.get("indicator") for e in evidence_list if e.get("indicator")}
    questions = []
    seen_templates = set()

    def add_q(template_id, category, text, evidence_refs, rationale, action, priority):
        if template_id in seen_templates:
            return
        seen_templates.add(template_id)
        q_num = len(questions) + 1
        questions.append({
            "question_id": f"Q-{q_num:02d}",
            "template_id": template_id,
            "category": category,
            "question_text": text,
            "evidence_refs": evidence_refs,
            "rationale": rationale,
            "verification_action": action,
            "priority": priority,
            "status": "Pending",
            "officer_notes": "",
        })

    # 1. Identity and duplicate applications
    if "identity" in indicators:
        id_ev = [e for e in evidence_list if e.get("indicator") == "identity"]
        all_refs = [r for e in id_ev for r in e.get("source_record_ids", [])]
        add_q(
            "TPL-ID-01",
            "Identity and Duplicate Applications",
            "Can the applicants' identities be independently verified through official citizen registries?",
            all_refs or beneficiaries[:3],
            "High phonetic or attribute similarity was detected across scholarship applications, suggesting possible identity duplication.",
            "Verify identity credentials (Aadhaar / Voter ID / National Register) through an authorized government verification service.",
            "High",
        )
        add_q(
            "TPL-ID-02",
            "Identity and Duplicate Applications",
            "Are the similar records separate legitimate applicants (such as relatives or twins) or possible duplicate submissions?",
            all_refs[:4],
            "Names, birth dates, or parentage exhibit strong similarity but may have legitimate explanations such as siblings or family members.",
            "Review student birth certificates and enrollment registers directly with the educational institution.",
            "Medium",
        )

    # 2. Bank account and beneficiary verification
    if any(ind in indicators for ind in ["payout_concentration", "shared_account"]):
        acct_ev = [e for e in evidence_list if e.get("indicator") in ["payout_concentration", "shared_account"]]
        all_accts = [r for e in acct_ev for r in e.get("related_account_ids", [])]
        all_ben = [r for e in acct_ev for r in e.get("related_beneficiary_ids", [])]
        add_q(
            "TPL-BANK-01",
            "Bank Account and Beneficiary Verification",
            "Does the payout account legitimately belong to the beneficiary or an authorized parent/guardian under applicable scheme rules?",
            all_accts[:4] or all_ben[:4],
            "Multiple scholarship beneficiaries are mapped to the same disbursement bank account identifier.",
            "Verify account ownership directly via CBS (Core Banking Solution) / PFMS linkage and review guardian authorization documents.",
            "High",
        )
        add_q(
            "TPL-BANK-02",
            "Bank Account and Beneficiary Verification",
            "Is there a legitimate household or institutional reason explaining the shared account?",
            all_accts[:2] or beneficiaries[:2],
            "Shared accounts can occasionally represent minors under the same household head or authorized institutional accounts.",
            "Examine ration card or domicile certificates to verify whether linked beneficiaries belong to the same family unit.",
            "Medium",
        )

    # 3. Transaction and payment patterns
    if any(ind in indicators for ind in ["circular_transfer", "collector", "velocity"]):
        tx_ev = [e for e in evidence_list if e.get("indicator") in ["circular_transfer", "collector", "velocity"]]
        all_tx = [r for e in tx_ev for r in e.get("source_record_ids", [])]
        add_q(
            "TPL-TX-01",
            "Transaction and Payment Patterns",
            "Are the post-disbursement transfers consistent with legitimate student expenditures or educational fee remittances?",
            all_tx[:6],
            "Coordinated transaction sequences or circular transfer patterns were detected following state scholarship disbursements.",
            "Inspect transaction statements for destination accounts to determine whether funds reached educational institutions or intermediaries.",
            "High",
        )
        add_q(
            "TPL-TX-02",
            "Transaction and Payment Patterns",
            "Is there independently verifiable evidence of an unusual collector pattern or kickback arrangement?",
            all_tx[:4],
            "A single recipient account concentrated incoming transfers from multiple scholarship recipient accounts within a short window.",
            "Interview account holders and request proof of tuition or hostel payment receipts corresponding to transfer amounts.",
            "High",
        )

    # 4. Cross-scheme cases
    if "alias_award_conflict" in indicators or len(schemes) > 1:
        scheme_ev = [e for e in evidence_list if e.get("indicator") == "alias_award_conflict"]
        all_apps = [r for e in scheme_ev for r in e.get("source_record_ids", [])]
        add_q(
            "TPL-SCHEME-01",
            "Cross-Scheme Verification",
            "Do the respective schemes permit the identified combination of scholarship benefits, or is there an award conflict?",
            all_apps or schemes,
            "Linked beneficiary records appear under multiple scholarship schemes with overlapping benefit entitlement periods.",
            "Cross-reference state and central scholarship guidelines to verify concurrent scholarship eligibility allowances.",
            "High",
        )

    # 5. Phone and address links
    if any(ind in indicators for ind in ["shared_phone", "shared_address"]):
        add_q(
            "TPL-CONTACT-01",
            "Phone and Address Links",
            "Could the shared contact information be explained by a legitimate institutional hostel, cyber café, or campus facilitator?",
            beneficiaries[:4],
            "Identical phone numbers or addresses appear across numerous unrelated applications.",
            "Confirm physical student residency with the college registrar and verify if phone belongs to an authorized representative.",
            "Medium",
        )

    # 6. Documents and eligibility (Always generate base verification question for suspicious cases)
    add_q(
        "TPL-DOC-01",
        "Documents and Eligibility",
        "Have the submitted income, caste, and institutional admission documents been verified directly with the issuing authorities?",
        beneficiaries[:3],
        "Verification of underlying eligibility criteria is essential before determining intentional misrepresentation.",
        "Obtain verification receipts from the state portal or college admission office for each flagged beneficiary.",
        "High" if case.get("risk_score", 0) >= 60 else "Medium",
    )

    # 7. Graph and network relationships
    if len(beneficiaries) > 1 or case.get("size", 1) > 1:
        add_q(
            "TPL-GRAPH-01",
            "Graph and Network Relationships",
            "Are there independent supporting signals linking all records in this cluster, or does the cluster rely on a single shared attribute?",
            [cluster_id],
            "The cluster was formed via network community analysis. A single shared attribute (e.g. college or facilitator) may falsely group innocent applicants.",
            "Review graph evidence to determine whether multiple distinct connection types exist (e.g., both account and phone links).",
            "Medium",
        )

    return questions


def generate_investigation_pdf(case: dict, investigation: dict, questions: list[dict]) -> bytes:
    """Renders a comprehensive, multi-page ReportLab PDF for the Investigation Copilot."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#0f2744")
    accent_color = colors.HexColor("#1e5692")
    border_color = colors.HexColor("#cbd5e1")
    light_bg = colors.HexColor("#f8fafc")
    text_dark = colors.HexColor("#0f172a")
    text_muted = colors.HexColor("#475569")

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=accent_color,
        spaceAfter=12,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=text_dark,
    )
    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=text_muted,
    )
    q_text_style = ParagraphStyle(
        "QuestionText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=primary_color,
    )
    tag_style = ParagraphStyle(
        "TagStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    elements = []

    # Title & Metadata Header
    elements.append(Paragraph("SATARKK — FORENSIC INVESTIGATION COPILOT", title_style))
    elements.append(Paragraph("Actionable Investigation Workspace & Evidence-Linked Verification Checklist", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=0, spaceAfter=12))

    # Case Summary Box
    case_id = case.get("case_id") or case.get("cluster_id") or investigation.get("case_id") or "UNKNOWN"
    risk_score = case.get("risk_score", 0)
    risk_level = case.get("risk_level", "Medium")
    status = investigation.get("status", "Under Review")
    schemes = ", ".join(case.get("schemes", [])) or case.get("scheme", "Scholarship Scheme")
    gen_time = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    meta_data = [
        [
            Paragraph("<b>Case Reference:</b> " + str(case_id), body_style),
            Paragraph("<b>Investigation Status:</b> " + str(status), body_style),
        ],
        [
            Paragraph("<b>Target Scheme(s):</b> " + str(schemes), body_style),
            Paragraph(f"<b>Priority Score:</b> {risk_score}/100 ({risk_level})", body_style),
        ],
        [
            Paragraph("<b>Beneficiaries Flagged:</b> " + str(len(case.get("beneficiary_ids", []))), body_style),
            Paragraph("<b>Report Generated:</b> " + str(gen_time), body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    # Core Investigative Notice
    notice_text = (
        "<b>Investigative Standard:</b> Review priority scores and detected patterns are indicators for "
        "human verification and do NOT constitute proof of fraud. Officers must independently verify evidence, "
        "protect applicant rights, and examine legitimate household or institutional explanations."
    )
    notice_p = Paragraph(notice_text, body_muted)
    notice_table = Table([[notice_p]], colWidths=[520])
    notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d97706")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(notice_table)
    elements.append(Spacer(1, 14))

    # Section 1: Evidence Summary
    elements.append(Paragraph("1. Flagged Evidence & Signals", section_heading))
    evidence_items = case.get("evidence", []) or []
    if evidence_items:
        ev_rows = [[
            Paragraph("<b>Signal / Type</b>", body_bold),
            Paragraph("<b>Explanation & Forensic Finding</b>", body_bold),
            Paragraph("<b>Related Records</b>", body_bold),
            Paragraph("<b>Score</b>", body_bold),
        ]]
        for ev in evidence_items[:8]:
            ind_name = ev.get("indicator", "signal").replace("_", " ").title()
            expl = ev.get("explanation", "Evidence flagged by system analysis.")
            records_ref = ", ".join(ev.get("source_record_ids", [])[:3] or ev.get("related_account_ids", [])[:2] or ["Records"])
            pts = f"+{ev.get('contribution', 0)}"
            ev_rows.append([
                Paragraph(ind_name, body_bold),
                Paragraph(expl, body_style),
                Paragraph(records_ref, body_muted),
                Paragraph(pts, body_bold),
            ])
        ev_table = Table(ev_rows, colWidths=[105, 255, 115, 45])
        ev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.75, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(ev_table)
    else:
        elements.append(Paragraph("No automated evidence records attached to this case.", body_muted))
    elements.append(Spacer(1, 14))

    # Section 2: Evidence-Linked Questions
    elements.append(Paragraph("2. Evidence-Linked Investigation Checklist", section_heading))
    elements.append(Paragraph("Structured questions derived from case evidence. Record findings and action taken.", body_muted))
    elements.append(Spacer(1, 6))

    # Group questions by category
    categories = {}
    for q in questions:
        categories.setdefault(q.get("category", "General"), []).append(q)

    for cat_name, cat_questions in categories.items():
        cat_p = Paragraph(f"<b>Category: {cat_name}</b>", ParagraphStyle("CatHeader", parent=section_heading, fontSize=10.5, textColor=accent_color))
        elements.append(cat_p)

        for q in cat_questions:
            priority_color = "#b91c1c" if q.get("priority") == "High" else "#d97706" if q.get("priority") == "Medium" else "#2563eb"
            status_text = q.get("status", "Pending")
            officer_notes = q.get("officer_notes", "") or "No notes recorded yet."

            q_box = [
                [
                    Paragraph(f"<b>[{q.get('question_id')}]</b> Priority: <font color='{priority_color}'><b>{q.get('priority')}</b></font> · Status: <b>{status_text}</b>", body_style),
                    Paragraph("<b>Refs:</b> " + (", ".join(q.get("evidence_refs", [])[:4]) or "Case data"), body_muted),
                ],
                [
                    Paragraph(f"<b>Question:</b> {q.get('question_text')}", q_text_style),
                    "",
                ],
                [
                    Paragraph(f"<b>Rationale:</b> {q.get('rationale')}", body_style),
                    "",
                ],
                [
                    Paragraph(f"<b>Recommended Action:</b> {q.get('verification_action')}", body_bold),
                    "",
                ],
                [
                    Paragraph(f"<b>Officer Findings & Notes:</b> {officer_notes}", body_style),
                    "",
                ],
                [
                    Paragraph("<b>Field Notes & Observations (for manual completion):</b><br/>__________________________________________________________________________________________<br/>__________________________________________________________________________________________", body_muted),
                    "",
                ],
            ]

            q_table = Table(q_box, colWidths=[380, 140])
            q_table.setStyle(TableStyle([
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 2), (1, 2)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("SPAN", (0, 5), (1, 5)),
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(KeepTogether([q_table, Spacer(1, 8)]))

    elements.append(Spacer(1, 10))

    # Section 3: General Case Observations & Notes
    elements.append(Paragraph("3. General Case Observations & Next Steps", section_heading))
    general_notes = investigation.get("notes") or "No general case observations entered."
    notes_box = [
        [Paragraph(f"<b>Recorded Case Observation:</b><br/>{general_notes}", body_style)],
        [Paragraph("<b>Next Steps / Action Directives:</b><br/>[ ] Contact institutional nodal officer &nbsp;&nbsp;&nbsp;&nbsp; [ ] Request bank KYC certified ledger &nbsp;&nbsp;&nbsp;&nbsp; [ ] Escalate to State Vigilance Committee", body_style)],
    ]
    notes_table = Table(notes_box, colWidths=[520])
    notes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(notes_table)
    elements.append(Spacer(1, 14))

    # Section 4: Sign-off block
    elements.append(Paragraph("4. Investigating Officer Review & Sign-Off", section_heading))
    sign_data = [
        [
            Paragraph("<b>Investigating Officer Name:</b><br/>___________________________", body_style),
            Paragraph("<b>Designation / Region:</b><br/>___________________________", body_style),
        ],
        [
            Paragraph("<b>Signature:</b><br/>___________________________", body_style),
            Paragraph("<b>Date of Review:</b><br/>____ / ____ / 202___", body_style),
        ],
    ]
    sign_table = Table(sign_data, colWidths=[260, 260])
    sign_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(KeepTogether([sign_table]))

    # Build PDF with two-pass numbering
    doc.build(elements, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
