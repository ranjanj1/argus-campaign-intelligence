from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from scripts.models.client_context import ClientProfile

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

BRAND_BLUE = colors.HexColor("#1F4E79")
BRAND_LIGHT = colors.HexColor("#2E75B6")


def _build_report_context(profile: ClientProfile) -> dict:
    camps = profile.campaigns
    total_spend = sum(c.spend for c in camps)
    total_revenue = sum(c.revenue for c in camps)
    total_impressions = sum(c.impressions for c in camps)
    total_clicks = sum(c.clicks for c in camps)
    total_conversions = sum(c.conversions for c in camps)
    blended_roas = total_revenue / total_spend if total_spend else 0.0
    blended_ctr = total_clicks / total_impressions if total_impressions else 0.0

    sorted_by_roas = sorted(camps, key=lambda c: c.revenue / max(c.spend, 0.01), reverse=True)
    top = sorted_by_roas[0]
    worst = sorted_by_roas[-1]

    best_seg = max(profile.segments, key=lambda s: s.avg_ctr)

    channel_data: dict[str, dict] = {}
    for c in camps:
        ch = c.channel
        if ch not in channel_data:
            channel_data[ch] = {"spend": 0.0, "revenue": 0.0, "impressions": 0, "clicks": 0}
        channel_data[ch]["spend"] += c.spend
        channel_data[ch]["revenue"] += c.revenue
        channel_data[ch]["impressions"] += c.impressions
        channel_data[ch]["clicks"] += c.clicks

    channel_summary = {}
    for ch, d in channel_data.items():
        channel_summary[ch] = {
            "spend": round(d["spend"], 2),
            "revenue": round(d["revenue"], 2),
            "roas": round(d["revenue"] / d["spend"], 2) if d["spend"] else 0,
            "impressions": d["impressions"],
            "ctr": round(d["clicks"] / d["impressions"], 4) if d["impressions"] else 0,
        }

    status_counts = {"active": 0, "paused": 0, "completed": 0}
    for c in camps:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1

    return {
        "client_id": profile.client_id,
        "company_name": profile.company_name,
        "industry": profile.industry,
        "report_month": profile.report_month,
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_revenue, 2),
        "blended_roas": round(blended_roas, 2),
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "blended_ctr": round(blended_ctr, 4),
        "top_campaign_name": top.name,
        "top_campaign_roas": round(top.revenue / max(top.spend, 0.01), 2),
        "top_campaign_spend": round(top.spend, 2),
        "worst_campaign_name": worst.name,
        "worst_campaign_roas": round(worst.revenue / max(worst.spend, 0.01), 2),
        "best_segment_name": best_seg.segment_name,
        "best_segment_ctr": round(best_seg.avg_ctr, 4),
        "best_segment_cvr": round(best_seg.avg_conversion_rate, 4),
        "active_count": status_counts["active"],
        "paused_count": status_counts["paused"],
        "completed_count": status_counts["completed"],
        "channel_summary": channel_summary,
        "channels": list(channel_summary.keys()),
        "tone_keywords": ", ".join(profile.vertical_config.tone_keywords),
        "business_objectives": profile.vertical_config.business_objectives,
        "recommendations": profile.vertical_config.business_objectives,  # reused as base
    }


def _render_pdf(sections: dict, context: dict, output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle("H1", parent=styles["Heading1"],
                               textColor=BRAND_BLUE, fontSize=18, spaceAfter=12)
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                               textColor=BRAND_LIGHT, fontSize=13, spaceAfter=8, spaceBefore=16)
    style_body = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=10.5, leading=15, spaceAfter=8, alignment=TA_JUSTIFY)
    style_bullet = ParagraphStyle("Bullet", parent=styles["Normal"],
                                  fontSize=10.5, leading=15, spaceAfter=4, leftIndent=20)
    style_meta = ParagraphStyle("Meta", parent=styles["Normal"],
                                fontSize=9, textColor=colors.gray, spaceAfter=6)

    story = []

    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Monthly Performance Report", style_h1))
    story.append(Paragraph(
        f"{context['company_name']} — {context['report_month']}",
        ParagraphStyle("Subtitle", parent=styles["Normal"],
                       fontSize=13, textColor=BRAND_LIGHT, spaceAfter=4),
    ))
    story.append(Paragraph("Prepared by 2060 Digital", style_meta))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=12))

    # KPI summary table
    kpi_data = [
        ["Total Spend", "Total Revenue", "Blended ROAS", "Total Conversions"],
        [
            f"${context['total_spend']:,.0f}",
            f"${context['total_revenue']:,.0f}",
            f"{context['blended_roas']:.2f}x",
            f"{context['total_conversions']:,}",
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[1.6 * inch] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#DEEAF1")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, BRAND_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.3 * inch))

    def add_section(title: str, content: str) -> None:
        story.append(Paragraph(title, style_h2))
        for para in content.strip().split("\n\n"):
            para = para.strip()
            if para.startswith("- ") or para.startswith("• "):
                for line in para.splitlines():
                    story.append(Paragraph(line.lstrip("- •"), style_bullet))
            elif para:
                story.append(Paragraph(para, style_body))

    add_section("Executive Summary", sections.get("executive_summary", ""))
    story.append(PageBreak())
    add_section("Channel Performance", sections.get("channel_performance", ""))
    story.append(PageBreak())
    add_section("Audience Insights", sections.get("audience_insights", ""))
    add_section("Budget Efficiency", sections.get("budget_efficiency", ""))
    story.append(PageBreak())

    story.append(Paragraph("Recommendations", style_h2))
    for rec in sections.get("recommendations", []):
        story.append(Paragraph(f"• {rec}", style_bullet))

    doc.build(story)


def generate_monthly_report_pdf(profile: ClientProfile, output_path: Path) -> None:
    """Render PDF using Jinja2 templates — no LLM required."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    # Add custom filter
    env.filters["currency"] = lambda v: f"${v:,.0f}"
    env.filters["pct"] = lambda v: f"{v:.1%}"

    context = _build_report_context(profile)
    template = env.get_template("monthly_report.j2")
    rendered = template.render(**context)

    # Parse rendered text into sections (delimited by ###SECTION:name###)
    sections: dict[str, str | list] = {}
    current_key = None
    buf: list[str] = []
    for line in rendered.splitlines():
        if line.startswith("###SECTION:"):
            if current_key:
                sections[current_key] = "\n".join(buf).strip()
                buf = []
            current_key = line.replace("###SECTION:", "").strip()
        elif line.startswith("###LIST:"):
            if current_key:
                sections[current_key] = "\n".join(buf).strip()
                buf = []
            current_key = line.replace("###LIST:", "").strip()
            sections[current_key] = []  # will be list
        elif current_key is not None:
            if isinstance(sections.get(current_key), list):
                if line.strip():
                    sections[current_key].append(line.strip().lstrip("- "))  # type: ignore
            else:
                buf.append(line)
    if current_key and buf:
        sections[current_key] = "\n".join(buf).strip()

    _render_pdf(sections, context, output_path)
