import json
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_days_to_exam(exam_date_str):
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    days = (exam_date - today).days
    return max(0, days)

def get_category_color(days_remaining):
    if days_remaining <= 7:
        return "#FF6B6B"
    elif days_remaining <= 14:
        return "#FFD93D"
    else:
        return "#6BCB77"

def build_title_section(elements, timetable):
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1E3A5F"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    total_sessions = len(timetable)
    total_study_time = sum(day["total_study_minutes"] for day in timetable)
    hours = total_study_time // 60
    minutes = total_study_time % 60
    today = datetime.now().strftime("%d %B %Y")

    elements.append(Paragraph("📚 StudyPilot — Weekly Timetable", title_style))
    elements.append(Paragraph(
        f"Generated {today} · {total_sessions} days · {hours}h {minutes}m total study",
        subtitle_style
    ))

def build_legend_table(elements, exam_date):
    days_to_exam = calculate_days_to_exam(exam_date)

    legend_data = [
        ["🔴 0-7 days", "🟡 8-14 days", "🟢 15+ days"],
        ["Exam Week", "Revision", "New Chapters"],
        ["High Priority", "Medium Priority", "Low Priority"]
    ]

    legend_table = Table(legend_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch])
    legend_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FF6B6B")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFD93D")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#6BCB77")),

        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("PADDING", (0, 0), (-1, 0), 8),

        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#CCCCCC")),
    ]))

    elements.append(legend_table)
    elements.append(Spacer(1, 0.3*inch))

def build_timetable(elements, timetable, exam_date):
    days_to_exam = calculate_days_to_exam(exam_date)

    table_data = [["DATE", "SUBJECT", "CHAPTERS", "TIME"]]

    for day in timetable:
        date_str = day["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = date_obj.strftime("%a")
        formatted_date = f"{date_str}\n{day_name}"

        day_days_remaining = calculate_days_to_exam(date_str)

        for i, slot in enumerate(day["slots"]):
            subject = slot["subject"]
            chapters = slot.get("chapters_to_cover", [])
            chapters_text = "\n".join([f"• {ch}" for ch in chapters[:5]])
            if len(chapters) > 5:
                chapters_text += f"\n... +{len(chapters)-5} more"

            time_str = f"{slot['duration_minutes']}m"

            if i == 0:
                table_data.append([formatted_date, subject, chapters_text, time_str])
            else:
                table_data.append(["", subject, chapters_text, time_str])

    col_widths = [1.0*inch, 2.0*inch, 2.8*inch, 0.7*inch]
    table = Table(table_data, colWidths=col_widths)

    table_style_list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("PADDING", (0, 0), (-1, 0), 10),

        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9F9F9")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("PADDING", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9F9F9"), colors.HexColor("#FFFFFF")]),
    ]

    row_num = 1
    for day in timetable:
        day_days_remaining = calculate_days_to_exam(day["date"])
        row_color = get_category_color(day_days_remaining)

        num_slots = len(day["slots"])
        for _ in range(num_slots):
            table_style_list.append(
                ("BACKGROUND", (0, row_num), (0, row_num), colors.HexColor(row_color))
            )
            table_style_list.append(
                ("TEXTCOLOR", (0, row_num), (0, row_num), colors.white)
            )
            table_style_list.append(
                ("FONTNAME", (0, row_num), (0, row_num), "Helvetica-Bold")
            )
            row_num += 1

    table.setStyle(TableStyle(table_style_list))

    elements.append(table)

def build_summary_section(elements, timetable, exam_date):
    styles = getSampleStyleSheet()

    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=6,
        leftIndent=0,
    )

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("<b>Study Plan Summary</b>", ParagraphStyle(
        'SummaryTitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor("#1E3A5F"),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )))

    total_study_time = sum(day["total_study_minutes"] for day in timetable)
    avg_per_day = total_study_time // len(timetable) if timetable else 0
    days_to_exam = calculate_days_to_exam(exam_date)

    urgency_emoji = "🔴" if days_to_exam <= 7 else "🟡" if days_to_exam <= 14 else "🟢"
    urgency_label = "EXAM WEEK" if days_to_exam <= 7 else "REVISION PHASE" if days_to_exam <= 14 else "LEARNING PHASE"

    summary_text = f"""
    <b>Total Study Time:</b> {total_study_time // 60}h {total_study_time % 60}m across {len(timetable)} days<br/>
    <b>Average Per Day:</b> {avg_per_day // 60}h {avg_per_day % 60}m<br/>
    <b>Days Until Exam:</b> {days_to_exam} days ({urgency_emoji} {urgency_label})<br/>
    <b>Subjects Covered:</b> {', '.join(set(slot['subject'] for day in timetable for slot in day['slots']))}
    """

    elements.append(Paragraph(summary_text.strip(), summary_style))

def export_timetable_to_pdf(input_file="timetable.json", output_file="timetable.pdf"):
    try:
        with open(input_file, "r") as f:
            data = json.load(f)

        timetable = data.get("timetable", [])
        if not timetable:
            print(f"❌ No timetable data found in {input_file}")
            return

        exam_date = timetable[-1]["date"]

        doc = SimpleDocTemplate(
            output_file,
            pagesize=A4,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )

        elements = []

        build_title_section(elements, timetable)
        build_legend_table(elements, exam_date)
        elements.append(PageBreak())

        build_timetable(elements, timetable, exam_date)
        build_summary_section(elements, timetable, exam_date)

        doc.build(elements)
        print(f"✅ {output_file} generated successfully!")
        print(f"📊 Timetable spans {len(timetable)} days | Exam date: {exam_date}")

    except FileNotFoundError:
        print(f"❌ Error: {input_file} not found. Run planner.py first to generate timetable.json")
    except json.JSONDecodeError:
        print(f"❌ Error: {input_file} is not valid JSON")
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")

# if __name__ == "__main__":
#     export_timetable_to_pdf()
